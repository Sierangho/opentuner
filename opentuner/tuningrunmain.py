# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab autoindent smarttab
import argparse
import copy
import inspect
import json
import logging
import math
import os
import requests
import socket
import sys
import time
import uuid
from datetime import datetime, timedelta

from opentuner import resultsdb
from opentuner.search.driver import SearchDriver
from opentuner.measurement.driver import MeasurementDriver

log = logging.getLogger(__name__)

argparser = argparse.ArgumentParser(add_help=False)
argparser.add_argument('--label',
                       help="name for the TuningRun")
argparser.add_argument('--print-search-space-size', action='store_true',
                       help="Print out the estimated size of the search space and exit")
argparser.add_argument('--database',
                       help=("database to store tuning results in, see: "
                             "http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#database-urls"))
argparser.add_argument('--print-params','-pp',action='store_true',
                       help='show parameters of the configuration being tuned')

argparser.add_argument('--upload-results', type='int', default=0, help='upload tuning results from the past x days. -1 for all days')


class CleanStop(Exception):
  pass


class LogFormatter(logging.Formatter):
  def format(self, record):
    record.relativeCreated /= 1000.0
    try:
      # python 2.7
      return super(LogFormatter, self).format(record)
    except:
      # python 2.6
      return _OldFormatter.format(self, record)


_OldFormatter = logging.Formatter
logging.Formatter = LogFormatter

try:
  # python 2.7
  from logging.config import dictConfig
except:
  # python 2.6
  from .utils.dictconfig import dictConfig

the_logging_config = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {'console': {'format': '[%(relativeCreated)6.0fs] '
                                       '%(levelname)7s %(name)s: '
                                       '%(message)s'},
                 'file': {'format': '[%(asctime)-15s] '
                                    '%(levelname)7s %(name)s: '
                                    '%(message)s '
                                    '@%(filename)s:%(lineno)d'}},
  'handlers': {'console': {'class': 'logging.StreamHandler',
                           'formatter': 'console',
                           'level': 'INFO'},
               'file': {'class': 'logging.FileHandler',
                        'filename': 'opentuner.log',
                        'formatter': 'file',
                        'level': 'WARNING'}},
  'loggers': {'': {'handlers': ['console', 'file'],
                   'level': 'INFO',
                   'propagate': True}}}


def init_logging():
  dictConfig(the_logging_config)
  global init_logging
  init_logging = lambda: None


class TuningRunMain(object):
  def __init__(self,
               measurement_interface,
               args,
               search_driver=SearchDriver,
               measurement_driver=MeasurementDriver):
    init_logging()

    manipulator = measurement_interface.manipulator()
    if args.print_search_space_size:
      print "10^{%.2f}" % math.log(manipulator.search_space_size(), 10)
      sys.exit(0)
    # show internal parameter representation
    if args.print_params:
      cfg = manipulator.seed_config()
      d = manipulator.parameters_dict(cfg)
      params_dict ={}
      for k in d:
        cls = d[k].__class__.__name__
        p = (k, d[k].search_space_size())
        if cls in params_dict:
          params_dict[cls].append(p)
        else:
          params_dict[cls] = [p]
      for k in params_dict:
        print k, params_dict[k]
        print
      sys.exit(0)

    input_manager = measurement_interface.input_manager()
    objective = measurement_interface.objective()

    if not args.database:
      #args.database = 'sqlite://' #in memory
      if not os.path.isdir('opentuner.db'):
        os.mkdir('opentuner.db')
      args.database = 'sqlite:///' + os.path.join('opentuner.db',
                                                  socket.gethostname() + '.db')

    if '://' not in args.database:
      args.database = 'sqlite:///' + args.database

    if not args.label:
      args.label = 'unnamed'

    #self.fake_commit = ('sqlite' in args.database)
    self.fake_commit = True

    self.args = args

    self.engine, self.Session = resultsdb.connect(args.database)
    self.session = self.Session()
    if args.upload_results != 0:
      print "uploading results"
      self.upload_results(args.upload_results)
      sys.exit(0)
    self.tuning_run = None
    self.search_driver_cls = search_driver
    self.measurement_driver_cls = measurement_driver
    self.measurement_interface = measurement_interface
    self.input_manager = input_manager
    self.manipulator = manipulator
    self.objective = objective
    self.objective_copy = copy.copy(objective)
    self.last_commit_time = time.time()

  def init(self):
    if self.tuning_run is None:
      program_version = (self.measurement_interface
                         .db_program_version(self.session))
      self.session.flush()
      self.measurement_interface.prefix_hook(self.session)
      self.tuning_run = (
        resultsdb.models.TuningRun(
          uuid=uuid.uuid4().hex,
          name=self.args.label,
          args=self.args,
          start_date=datetime.now(),
          program_version=program_version,
          objective=self.objective_copy,
        ))
      self.session.add(self.tuning_run)

      driver_kwargs = {
        'args': self.args,
        'input_manager': self.input_manager,
        'manipulator': self.manipulator,
        'measurement_interface': self.measurement_interface,
        'objective': self.objective,
        'session': self.session,
        'tuning_run_main': self,
        'tuning_run': self.tuning_run,
        'extra_seeds': self.measurement_interface.seed_configurations(),
      }

      self.search_driver = self.search_driver_cls(**driver_kwargs)

      self.measurement_driver = self.measurement_driver_cls(**driver_kwargs)
      self.measurement_interface.set_driver(self.measurement_driver)
      self.input_manager.set_driver(self.measurement_driver)

      self.tuning_run.machine_class = self.measurement_driver.get_machine_class()
      self.tuning_run.input_class = self.input_manager.get_input_class()

  def commit(self, force=False):
    if (force or not self.fake_commit or
            time.time() - self.last_commit_time > 30):
      self.session.commit()
      self.last_commit_time = time.time()
    else:
      self.session.flush()

  def main(self):
    self.init()
    try:
      self.tuning_run.state = 'RUNNING'
      self.commit(force=True)
      self.search_driver.main()
      if self.search_driver.best_result:
        self.measurement_interface.save_final_config(
            self.search_driver.best_result.configuration)
      self.tuning_run.final_config = self.search_driver.best_result.configuration
      self.tuning_run.state = 'COMPLETE'
    except:
      self.tuning_run.state = 'ABORTED'
      raise
    finally:
      self.tuning_run.end_date = datetime.now()
      self.commit(force=True)
      self.session.close()

  def results_wait(self, generation):
    """called by search_driver to wait for results"""
    #single process version:
    self.measurement_driver.process_all()

  def upload_results(self, num_days):
    def submit_batch(b):
      r = requests.post(url, data=json.dumps(b))
      if r.status_code is not 200:
        print "Error uploading results. Status code {}: {}".format(r.status_code, r.text)

    url = 'http://localhost:8000/tuning_runs/upload/'
    # url = 'http://128.52.171.76/tuning_runs/upload/'
    # url = 'http://www.opentuner.org/tuning_runs/upload/'
    # gather tuning runs into payload

    q = (self.session.query(resultsdb.models.TuningRun)
          .filter_by(state='COMPLETE')
          .order_by('start_date'))
    if num_days > 0:
      q = q.filter(resultsdb.models.TuningRun.start_date > datetime.utcnow() - timedelta(days=num_days))
    # TODO add a limit on which results to submit if in args
    print "submitting {} results".format(q.count())
    counter = 0
    batch = []
    for tr in q:
      counter += 1
      try:
        # collect tuning run data
        data = self.get_tuning_run_data(tr)
        data.update(self.get_technique_info(tr))
        data.update(self.get_performance_info(tr))
        batch.append(data)
      except:
        print "error submitting tuning run {}".format(tr.id)
        continue

      if counter % 100 == 0:
        submit_batch(batch)
        batch = []
        print "submitted {} results".format(counter)

    #submit remaining
    if not counter % 100 == 0:
      submit_batch(batch)

    print "Finished uploading results"


  def get_tuning_run_data(self, tr):
    pv = tr.program_version
    p = pv.program
    out = {
        'uuid': tr.uuid,
        'start_date': tr.start_date.strftime("%Y-%m-%d %H:%M:%S.%f"),
        'program': {
          'project': p.project,
          'name': p.name,
          'version': pv.version,
          'objective': tr.objective.__class__.__name__,
        },
        'representation': {
          'parameter_info': pv.parameter_info,
          'name': '', # human readable name for the representation. Currently unused.
        },

      }
    return out

  def get_technique_info(self, tr):
    # extend data with 'bandit_technique' if bandit used
    q = (self.session.query(resultsdb.models.BanditInfo).filter_by(tuning_run_id=tr.id))
    bi = q.first()
    if bi is None:
      # TODO get metatechnique name if there was one used and handle submitting non-bandit
      print "SKIPPING BECAUSE NO BANDIT IN TUNING RUN {}".format(tr.id)
      # print tr.args
      raise Exception("unhandled")
    else:
      q = (self.session.query(resultsdb.models.BanditSubTechnique).filter_by(bandit_info_id=bi.id))
      bandit_sub_techniques = [t.name for t in q]

      out = {
        'bandit_technique': {
            'name': 'AUCBanditMetaTechnique', #TODO change this once field gets added to model
            'c': bi.c,
            'window': bi.window,
            'subtechnique_count': len(bandit_sub_techniques),
          },
        'bandit_sub_techniques': bandit_sub_techniques,
        }
      return out

  def get_performance_info(self, tr):
    start = tr.start_date
    q = (self.session.query(resultsdb.models.DesiredResult)
          .filter_by(tuning_run_id=tr.id)
          .filter_by(state='COMPLETE')
          .order_by('request_date'))
    bandit_performances = []
    technique_performance = {}
    total_num_bests = 0
    total_num_cfgs = 0
    # iterate through adding info
    drs = q.all()
    for dr in drs:
      total_num_cfgs += 1
      if dr.requestor not in technique_performance:
        technique_performance[dr.requestor] = {'num_cfgs':0, 'num_bests':0}
      technique_performance[dr.requestor]['num_cfgs'] += 1
      if dr.result.was_new_best:
        technique_performance[dr.requestor]['num_bests'] += 1
        total_num_bests +=1
      # output performance data at regular intervals
      if total_num_cfgs % 50 == 0:
        bandit_performance = {
            'total_num_cfgs': total_num_cfgs,
            'total_num_bests': total_num_bests,
            'seconds_elapsed': int((dr.request_date - start).total_seconds()),
            'technique_performances': copy.deepcopy(technique_performance),
          }
        bandit_performances.append(bandit_performance)
    # add an entry with values at the end of the tuning run.
    bandit_performances.append({
        'total_num_cfgs': total_num_cfgs,
        'total_num_bests': total_num_bests,
        'seconds_elapsed': -1, # mark that this is performance at the end of the tuning
        'technique_performances': copy.deepcopy(technique_performance),
      })


    return {'bandit_performances':bandit_performances}




def main(interface, args, *pargs, **kwargs):
  if inspect.isclass(interface):
    interface = interface(args=args, *pargs, **kwargs)
  return TuningRunMain(interface, args).main()

