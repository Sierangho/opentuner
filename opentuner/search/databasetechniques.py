import abc
import copy
import json
import logging
import random
import requests

from .metatechniques import MetaSearchTechnique
from .bandittechniques import AUCBanditMetaTechnique
from .technique import register, get_technique_from_name

log = logging.getLogger(__name__)
logging.getLogger("requests").setLevel(logging.WARNING)



class DatabaseAUCBanditMetaTechnique(AUCBanditMetaTechnique):
  """
  A bandit that replaces techniques at regular intervals
  """
  def __init__(self, techniques, bandit_kwargs=dict(), interval=50, **kwargs):
    super(DatabaseAUCBanditMetaTechnique, self).__init__(techniques, bandit_kwargs=bandit_kwargs, **kwargs)

    self.interval = interval
    self.performances = dict(((t.name, {'num_cfgs':0, 'num_bests':0}) for t in self.techniques))
    self.count = 0
    self.program_version = None

  # when setting the driver, also figure out the program name, version, representation etc.
  def set_driver(self, driver):
    super(DatabaseAUCBanditMetaTechnique, self).set_driver(driver)
    self.program_version = self.driver.tuning_run.program_version
    self.program = self.program_version.program

  def select_technique_order(self):
    """select the next technique to use"""
    self.count = (self.count + 1) % self.interval
    if self.count == 0:
      self.update_techniques()
    return (self.name_to_technique[k] for k in self.bandit.ordered_keys())

  def on_technique_result(self, technique, result):
    self.bandit.on_result(technique.name, result.was_new_best)
    self.performances[technique.name]['num_cfgs'] += 1
    if result.was_new_best:
      self.performances[technique.name]['num_bests'] += 1

  def on_technique_no_desired_result(self, technique):
    """treat not providing a configuration as not a best"""
    self.bandit.on_result(technique.name, 0)
    # TODO when no desired result , this should be counted against the technique
    # when uploading results (can make a "fake" desired result that isn't a best)
    # self.performances[technique.name]['num_cfgs'] += 1

  def get_problem_info(self):
    # check if properly initialized
    if self.program_version is None:
      return {}
    pv = self.program_version
    p = self.program

    info = {
      'program': {
          'project': p.project,
          'name': p.name,
          'version': pv.version,
          'objective': self.driver.objective.__class__.__name__,
        },
      'representation': {
          'parameter_info': pv.parameter_info,
          'name': '' # human readable name for the representation, Currently unused
        },
      }
    return info


  def get_recommended_techniques(self, use_performance=True):
    """
    return a list of technique names to use
    use_perforamnce - a boolean on whether we should send performance data on techniques
    """
    # url = 'http://localhost:8000/tuning_runs/recommend/'
    url = 'http://128.52.171.76/tuning_runs/recommend/'
    data = {}
    if use_performance:
      data['performance'] = self.performances
    else:
      data['performance'] = {}
    data['problem'] = self.get_problem_info()
    r = requests.post(url, data=json.dumps(data))
    if r.status_code is not 200:
      #DEBUG
      # print r.text
      # myfile = open('myfile.html', 'w+')
      # myfile.write(r.text)
      log.warning("failed to get recommended techniques")
      return []

    # response contains list of techniques (ordered best to worst)
    return json.loads(r.text)

  def remove_worst_technique(self):
    """
    remove the worst performing technique (by exploitation value) from the bandit
    as selectable technique
    performance data is left in the history
    """
    # find the worst performing technique to swap out
    keys = list(self.bandit.keys)
    random.shuffle(keys)
    keys.sort(key=self.bandit.exploitation_term)
    worst = keys[0]
    # remove from the bandit
    self.bandit.keys.remove(worst)
    log.debug("removing technique %s", worst)

  def add_technique(self, technique):
    """
    takes in an initialized Technique instance and add it to...
      the bandit
      performances
      name -> technique mapping
    """

    log.debug("adding technique %s", technique.name)
    new_technique = technique.name
    self.bandit.keys.append(new_technique)
    if not new_technique in self.bandit.use_counts:
      self.bandit.auc_sum[new_technique] = 0
      self.bandit.auc_decay[new_technique] = 0
      self.bandit.use_counts[new_technique] = 0
    if not new_technique in self.performances:
      self.performances[new_technique] = {'num_cfgs':0, 'num_bests':0}
    self.name_to_technique[new_technique] = technique

  def initialize_technique(self, technique_name):
    """
    given a technique_name, initialize the technique with the driver
    returns None if the technique cannot be initialized
    """
    t = get_technique_from_name(technique_name)
    if t is None:
      log.warning("could not initialize technique with name{}".format(technique_name))
      return None

    # technique name may differ if unable to initialize some operators
    t.name = technique_name
    # set the driver for the technique
    t.set_driver(self.driver)
    return t

  def update_techniques(self):
    """
    update the bandit queue by swapping in a new technique
    """
    techniques = self.get_recommended_techniques()
    # select a technique to add and initialize the technique
    t = None
    for t_name in techniques:
      if t_name not in self.bandit.keys:
        # initialize
        t = self.initialize_technique(t_name)
        if t is None:
          continue
        break
    if t is None:
      log.warning("could not update techniques")
      return
    self.remove_worst_technique()
    self.add_technique(t)


class DatabaseInitAUCBanditMetaTechnique(DatabaseAUCBanditMetaTechnique):
  """
  A bandit that starts with an initial recommended technique set and
  replaces techniques at regular intervals
  """
  def __init__(self, bandit_kwargs=dict(), interval=50, num_techniques=5, **kwargs):
    super(DatabaseInitAUCBanditMetaTechnique, self).__init__([], bandit_kwargs=bandit_kwargs, interval=interval,**kwargs)
    self.num_techniques = num_techniques

  def select_technique_order(self):
    """select the next technique to use"""
    if len(self.techniques) == 0:
      self.init_techniques()
    self.count = (self.count + 1) % self.interval
    if self.count == 0:
      self.update_techniques()
    return (self.name_to_technique[k] for k in self.bandit.ordered_keys())

  def init_techniques(self):
    log.debug("initializing techniques")
    techniques = []
    recommended = self.get_recommended_techniques(use_performance=False)
    for t_name in recommended:
      if len(techniques) >= self.num_techniques:
        break
      t = self.initialize_technique(t_name)
      if t is None:
        continue
      techniques.append(t)
    if len(techniques) != self.num_techniques:
      log.warning("Could only initialize %d out of %d initial techniques", len(techniques), self.num_techniques)

    self.techniques = techniques
    for t in techniques:
      self.add_technique(t)



import evolutionarytechniques
import differentialevolution
import simplextechniques
import patternsearch
import simulatedannealing
from pso import PSO, HybridParticle
import globalGA

register(DatabaseAUCBanditMetaTechnique([
        differentialevolution.DifferentialEvolutionAlt(),
        evolutionarytechniques.UniformGreedyMutation(name='UniformGreedyMutation10'),
        evolutionarytechniques.NormalGreedyMutation(name='NormalGreedyMutation20', mutation_rate=0.2),
        simplextechniques.RandomNelderMead(),
      ], name = "DBBanditMetaTechniqueA"))

register(DatabaseAUCBanditMetaTechnique([
      PSO(crossover='op3_cross_OX1'),
      PSO(crossover='op3_cross_PMX'),
      PSO(crossover='op3_cross_PX'),
      evolutionarytechniques.GA(crossover='op3_cross_OX1', crossover_rate=0.8),
      evolutionarytechniques.GA(crossover='op3_cross_PMX', crossover_rate=0.8),
      evolutionarytechniques.GA(crossover='op3_cross_PX', crossover_rate=0.8),
      differentialevolution.DifferentialEvolutionAlt(),
            globalGA.NormalGreedyMutation( crossover_rate=0.5, crossover_strength=0.2, name='GGA')
      ], name='DB_PSO_GA_DE'))


register(DatabaseAUCBanditMetaTechnique([
        differentialevolution.DifferentialEvolutionAlt(),
        patternsearch.PatternSearch(),
        simplextechniques.RandomNelderMead(),
        PSO(crossover = 'op3_cross_OX3'),
      ], name = "DBBanditMetaTechniqueD"))

# sticks with the initial recommendation
register(DatabaseInitAUCBanditMetaTechnique(name="BanditMetaTechnique_DBInit", interval=999999))
register(DatabaseInitAUCBanditMetaTechnique(name="DBBanditMetaTechnique_DBInit"))


# REMOVE BANDIT (by weighting Exploration a lot)
register(DatabaseAUCBanditMetaTechnique([
        differentialevolution.DifferentialEvolutionAlt(),
        evolutionarytechniques.UniformGreedyMutation(name='UniformGreedyMutation10'),
        evolutionarytechniques.NormalGreedyMutation(name='NormalGreedyMutation20', mutation_rate=0.2),
        simplextechniques.RandomNelderMead(),
      ], name = "DBMetaTechniqueA"
      , bandit_kwargs={'C':100000}))

register(DatabaseAUCBanditMetaTechnique([
      PSO(crossover='op3_cross_OX1'),
      PSO(crossover='op3_cross_PMX'),
      PSO(crossover='op3_cross_PX'),
      evolutionarytechniques.GA(crossover='op3_cross_OX1', crossover_rate=0.8),
      evolutionarytechniques.GA(crossover='op3_cross_PMX', crossover_rate=0.8),
      evolutionarytechniques.GA(crossover='op3_cross_PX', crossover_rate=0.8),
      differentialevolution.DifferentialEvolutionAlt(),
            globalGA.NormalGreedyMutation( crossover_rate=0.5, crossover_strength=0.2, name='GGA')
      ], name='DB_PSO'
      , bandit_kwargs={'C':100000}))

register(DatabaseAUCBanditMetaTechnique([
        differentialevolution.DifferentialEvolutionAlt(),
        patternsearch.PatternSearch(),
        simplextechniques.RandomNelderMead(),
        PSO(crossover = 'op3_cross_OX3'),
      ], name = "DBMetaTechniqueD"
      , bandit_kwargs={'C':100000}))

register(DatabaseInitAUCBanditMetaTechnique(name="DBMetaTechnique_DBInit",  bandit_kwargs={'C':100000}))
