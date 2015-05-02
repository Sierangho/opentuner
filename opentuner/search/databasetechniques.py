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

  def update_techniques(self):
    """
    update the bandit queue
    """
    # url = 'http://localhost:8000/tuning_runs/recommend/'
    url = 'http://128.52.171.76/tuning_runs/recommend/'
    # ping server
    # TODO also send representation
    r = requests.post(url, data=json.dumps(self.performances))
    if r.status_code is not 200:
      log.warning("failed to update techniques")
      return
    # print r.text
    # myfile = open('myfile.html', 'w+')
    # myfile.write(r.text)

    # response contains list of techniques (ordered best to worst)
    techniques = json.loads(r.text)
    # select a technique to add
    for t_name in techniques:
      if t_name not in self.bandit.keys:
        new_technique = t_name
        t = get_technique_from_name(new_technique)
        if t is None:
          log.warning("could not initialize technique with name {}".format(new_technique))
          continue
        break
    # initialize the technique
    if t is None:
      log.warning("could not update techniques")
      return

    t.set_driver(self.driver)

    # find the worst performing technique to swap out
    keys = list(self.bandit.keys)
    random.shuffle(keys)
    keys.sort(key=self.bandit.exploitation_term)
    worst = keys[0]

    # update state
    self.bandit.keys.remove(worst)
    self.bandit.keys.append(new_technique)
    if not new_technique in self.bandit.use_counts:
      self.bandit.auc_sum[new_technique] = 0
      self.bandit.auc_decay[new_technique] = 0
      self.bandit.use_counts[new_technique] = 0
    if not new_technique in self.performances:
      self.performances[new_technique] = {'num_cfgs':0, 'num_bests':0}
    self.name_to_technique[new_technique] = t
    print "==============================="
    print "OUT: " + worst
    print "IN: " + new_technique
    print ""
    print self.bandit.keys
    print "==============================="


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


