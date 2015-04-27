from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import traceback
import datetime
import numpy
import re
import math

from tuning_runs import models
# Create your views here.

def index(request):
  return HttpResponse("Hello, world. This is the index for tuning_runs")

def see_distances(request, rep_id):
  representation = get_representation(rep_id)

  s = "Distances to " + representation.program.project + "-" + representation.program.name

  response = [s]
  response.append(representation.parameter_info)
  param_info = parse_parameter_info(representation.parameter_info)

  for r in models.Representation.objects.all():
    if r.id != representation.id:
      d = get_distance(param_info, parse_parameter_info(r.parameter_info))
      response.append('Representation {}: {}-{} - distance = {}'.format(r.id, r.program.project, r.program.name, d))
      response.append(r.parameter_info)

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


def get_similar(request, rep_id):
  representation = get_representation(rep_id)

  s = "Similar representation to " + representation.program.project + "-" + representation.program.name

  response = [s]
  response.append(representation.parameter_info)

  r = get_closest_representation(representation.parameter_info, exclude_id=representation.id)

  response.append('Representation {}: {}-{} '.format(r.id, r.program.project, r.program.name))
  response.append(r.parameter_info)

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


def get_closest_representation(pinfo, exclude_id=None, representations=None):
  """
  Return the Representation with the most similar parameter_info to pinfo.

  Ignores the id passed in exclude_id
  """
  param_count = parse_parameter_info(pinfo)
  best_distance = 0
  best = None

  if representations is None:
    representations = models.Representation.objects.all()

  for r in representations:
    if r.id == exclude_id:
      continue
    param_count2 = parse_parameter_info(r.parameter_info)
    distance = get_distance(param_count, param_count2)
    if best is None or distance < best_distance:
      best_distance = distance
      best = r
  return best


def parse_parameter_info(pinfo):
  """
  de-jsonize parameter_info field of Representation -
  returns a simple count of # of each param type
  TODO return better counts
  TODO make a better pinfo....
  """
  counts = {}
  # fix pinfo so we can parse it as json
  # put quotes around parameter names
  pinfo = re.sub(r'\[(\w+),', '["\\1",', pinfo)
  # turn dicts of {pinfo:count, pinfo:count} into a list [pinfo, count, pinfo count]
  pinfo = re.sub('}',']', re.sub('{', '[', pinfo))
  pinfo = re.sub(':', ',', pinfo)

  param_info = json.loads(pinfo)

  # subroutine - called on sub_info, num is the number of copies
  # called on subparam_info = [paraminfo, count, param2info, count ... ]
  # where paraminfo has form [parameter, subparam_info]
  def add_subparam_info(sub_info, num):
    for i in range(len(sub_info)/2):
      subparam = sub_info[2*i]
      new_num = sub_info[2*i + 1] * num
      counts[subparam[0]] = counts.get(subparam[0], 0) + new_num
      add_subparam_info(subparam[1], new_num)

  add_subparam_info(param_info[1], 1)

  return counts


def get_distance(param_count1, param_count2):
  """
  calculate distance metric between two parameter counts (dictionary from parameter to # of that parameter used)
  """
  distance = 0
  # handle parameters in param_count2 not in param_count1
  for p in param_count2:
    if not p in param_count1:
      # param_count1[p] = 0.1
      distance += 1 # penalize by 1 order of magnitude

  for p in param_count1:
    if p not in param_count2:
      distance += (math.log10(param_count1[p]) - 0.001)**2
    else:
      distance += abs(math.log10(param_count1[p]) - math.log10(param_count2[p]))**2
  return distance

def view_pearson(request, rep_id, lookup=True, spearman=False):
  representation = get_representation(rep_id)
  technique_ranking = json.loads(get_technique_ranking(representation).technique_ranking)
  technique_scores = normalize_grouped_scores(technique_ranking, lookup=lookup)

  # STUFF FOR VIEWING OUTPUT
  s = "Pearson rank score + distance scores for representation " + representation.program.project + "-" + representation.program.name
  response = [s]

  #USED TO CALC DISTANCE
  param_info = parse_parameter_info(representation.parameter_info)


  for tr in models.TechniqueRanking.objects.all():
    r = tr.representation
    if tr.representation.id != representation.id:
      response.append('==============================================')
      response.append('Representation {}: {}-{} '.format(r.id, r.program.project, r.program.name))

      other_scores = normalize_grouped_scores(json.loads(tr.technique_ranking), lookup=lookup)
      xvals = []
      yvals = []
      for technique in technique_scores:
        if technique in other_scores:
          xvals.append(technique_scores[technique]['score'])
          yvals.append(other_scores[technique]['score'])

      if spearman:
        correlation_score = calc_spearman(xvals, yvals)
        response.append('spearman score : {}'.format(correlation_score))
      else:
        correlation_score = calc_pearson(xvals, yvals)
        response.append('pearson score : {}'.format(correlation_score))

      d = get_distance(param_info, parse_parameter_info(r.parameter_info))
      response.append('parameter distance score : {}'.format(d))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))

def view_all(request, rep_id):
  # output all pearson/spearman scores, both collapsing similar named techniques and leaving them expanded
  representation = get_representation(rep_id)
  technique_ranking = json.loads(get_technique_ranking(representation).technique_ranking)
  technique_scores = normalize_grouped_scores(technique_ranking, lookup=True)
  technique_scores_expanded = normalize_grouped_scores(technique_ranking, lookup=False)

  # STUFF FOR VIEWING OUTPUT
  s = "Rank score + distance scores for representation " + representation.program.project + "-" + representation.program.name
  response = [s]

  #USED TO CALC DISTANCE
  param_info = parse_parameter_info(representation.parameter_info)


  for tr in models.TechniqueRanking.objects.all():
    r = tr.representation
    if tr.representation.id != representation.id:
      response.append('==============================================')
      response.append('Representation {}: {}-{} '.format(r.id, r.program.project, r.program.name))

      d = get_distance(param_info, parse_parameter_info(r.parameter_info))
      response.append('parameter distance score : {}'.format(d))

      other_scores = normalize_grouped_scores(json.loads(tr.technique_ranking), lookup=True)
      other_scores_expanded = normalize_grouped_scores(json.loads(tr.technique_ranking), lookup=False)
      xvals = []
      yvals = []
      for technique in technique_scores:
        if technique in other_scores:
          xvals.append(technique_scores[technique]['score'])
          yvals.append(other_scores[technique]['score'])
      correlation_score1 = calc_spearman(xvals, yvals)
      response.append('spearman score : {}'.format(correlation_score1))
      correlation_score2 = calc_pearson(xvals, yvals)
      response.append('pearson score : {}'.format(correlation_score2))

      xvals_expanded = []
      yvals_expanded = []
      for technique in technique_scores_expanded:
        if technique in other_scores_expanded:
          xvals_expanded.append(technique_scores_expanded[technique]['score'])
          yvals_expanded.append(other_scores_expanded[technique]['score'])
      correlation_score3 = calc_spearman(xvals_expanded, yvals_expanded)
      response.append('spearman score (expanded): {}'.format(correlation_score3))
      correlation_score4 = calc_pearson(xvals_expanded, yvals_expanded)
      response.append('pearson score (expanded): {}'.format(correlation_score4))

      response.append('<table><tbody><tr><td>' + '</td><td>'.join([str(d), str(correlation_score1), str(correlation_score2), str(correlation_score3), str(correlation_score4)]) + '</td></tr></tbody></table>')

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))

def view_ranks(request, rep_id):
  representation = get_representation(rep_id)
  s = "technique rankings for " + representation.program.project + "-" + representation.program.name
  response = [s]
  response.append(representation.parameter_info)
  tr = get_technique_ranking(representation)

  technique_scores = json.loads(tr.technique_ranking)

  sorted_x = sorted(technique_scores.items(), reverse=True, key=lambda x: x[1]['score'])
  for x in sorted_x:
  #  if x[1]['num_runs'] > 3:
      response.append(str(x))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))

def view_grouped(request, rep_id, lookup=True):
  representation = get_representation(rep_id)
  s = "grouped technique scores for " + representation.program.project + "-" + representation.program.name
  response = [s]
  response.append(representation.parameter_info)
  tr = get_technique_ranking(representation)

  technique_scores = group_performance_by_base_technique(json.loads(tr.technique_ranking), lookup=lookup)

  sorted_x = sorted(technique_scores.items(), reverse=True, key=lambda x: x[1]['score'])
  for x in sorted_x:
  #  if x[1]['num_runs'] > 3:
      response.append(str(x))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


def view_normalized(request, rep_id, lookup=True):
  representation = get_representation(rep_id)
  s = "normalized technique scores for " + representation.program.project + "-" + representation.program.name
  response = [s]
  response.append(representation.parameter_info)
  tr = get_technique_ranking(representation)

  technique_scores = normalize_grouped_scores(json.loads(tr.technique_ranking), lookup=lookup)

  sorted_x = sorted(technique_scores.items(), reverse=True, key=lambda x: x[1]['score'])
  for x in sorted_x:
  #  if x[1]['num_runs'] > 3:
      response.append(str(x))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


# TODO have deferred tasks to update all ranks (overnight or something)
# def update_all_ranks(request):
#   for rep in models.Representation.objects.all():



def update_ranks(request, rep_id):
  representation = get_representation(rep_id)

  s = "updating technique rankings for " + representation.program.project + "-" + representation.program.name

  response = [s]
  response.append(representation.parameter_info)

  q = get_technique_performances(representation=representation) # TODO non-fixed stage


  num_runs = len(q.distinct('tuning_run'))
  response.append("aggregated over " + str(num_runs) + " runs")

  technique_scores = aggregate_technique_performances(q)

  # cache the technique ranking
  try:
    tr = models.TechniqueRanking.objects.get(representation=representation)
  except ObjectDoesNotExist:
    tr = models.TechniqueRanking(representation=representation, technique_ranking='')

  tr.technique_ranking = json.dumps(technique_scores)
  tr.save()


  sorted_x = sorted(technique_scores.items(), reverse=True, key=lambda x: x[1]['score'])
  for x in sorted_x:
    if x[1]['num_runs'] > 3:
      response.append(str(x))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))

def aggregate_technique_performances(qset):
  """
  #TODO IMPROVE NAME

  given a query set of TechniquePerformance return a mapping from technique names
  to a dict of {num_runs, num_cfgs, num_bests, score, avg_score, std_score}
  """
  # track list of scores per run
  avg_score = {}

  #aggregate run information
  technique_scores = {}
  for t in qset:
    name = t.technique.name
    if not name in technique_scores:
      technique_scores[name] = {'num_cfgs': 0, 'num_bests': 0, 'num_runs': 0}
      avg_score[name] = []
    technique_scores[name]['num_runs'] = technique_scores[name]['num_runs'] + 1
    technique_scores[name]['num_cfgs'] = technique_scores[name]['num_cfgs'] + t.num_cfgs
    technique_scores[name]['num_bests'] = technique_scores[name]['num_bests'] + t.num_bests
    avg_score[name].append(technique_scores[name]['num_bests'] / (1.0*technique_scores[name]['num_cfgs']))


  for name in technique_scores:
    # calc aggregate score
    technique_scores[name]['score'] = technique_scores[name]['num_bests'] / (1.0*technique_scores[name]['num_cfgs'])

    # calc avg and std dev for scores per run
    array = numpy.array(avg_score[name])
    technique_scores[name]['avg_score'] = numpy.mean(array)
    technique_scores[name]['std_score'] = numpy.std(array)
  return technique_scores

def get_bandit_performances(stage=None, representation=None):
  """
  Get query set of bandit performances associated with a representation at a specified stage of tuning

  :param stage: BanditPerformance will have stage < #cfgs_tested <= stage rounded up to nearest 50.
  a value of None gets performances from the end of tuning.
  :param representation: which representation to consider. A value of None considers all representations
  :returns: query set
  """
  q = models.BanditPerformance.objects.all()
  if representation is not None:
    q = q.filter(tuning_run__representation=representation)
  if stage is None:
    q = q.filter(seconds_elapsed=-1)
  else:
    upper_limit = ((stage / 50) + 1)*50
    #TODO deal with stage - distinct on tuning run id + technique
    q = q.filter(total_num_cfgs__gt=stage)
    q = q.filter(total_num_cfgs__lte=upper_limit)
  return q

def get_technique_performances(stage=None, representation=None):
  """
  Get query set of technique performances associated with a representation at a specified stage of tuning

  :param stage: Associated BanditPerformance will have stage < #cfgs_tested <= stage rounded up to nearest 50.
  a value of None gets performances from the end of tuning.
  :param representation: which representation to consider. A value of None considers all representations
  :returns: query set
  """
  q = models.TechniquePerformance.objects.all()
  if representation is not None:
    q = q.filter(bandit_performance__tuning_run__representation=representation)
  if stage is None:
    q = q.filter(bandit_performance__seconds_elapsed=-1)
  else:
    upper_limit = ((stage / 50) + 1)*50
    #TODO deal with stage - distinct on tuning run id + technique
    q = q.filter(bandit_performance__total_num_cfgs__gt=stage)
    q = q.filter(bandit_performance__total_num_cfgs__lte=upper_limit)
  return q

"""
HELPER METHODS/THINGS
"""

def calc_pearson(xvals, yvals):
  """
  calculate the Pearson product-moment correlation coefficient

  takes in a list of x values and a list of y values
  """
  assert(len(xvals) == len(yvals))
  n = len(xvals)
  if n < 2:
    return 0

  xmean = calc_average(xvals)
  ymean = calc_average(yvals)

  covariance = math.fsum([(xvals[i] - xmean)*(yvals[i] - ymean) for i in range(n)])
  return covariance/(calc_dev(xvals)*calc_dev(yvals)*n)

def calc_spearman(xvals, yvals):
  """
  calculate the Spearman rank correlation coefficient

  takes in a list of x values and a list of y values
  """

  assert(len(xvals) == len(yvals))
  n = len(xvals)
  if n < 2:
    return 0

  # helper function for going from [val, idx] pairs into [rank, idx] pairs
  def make_ranks(sorted_vals):
    n = len(sorted_vals)
    start_idx = 0
    for i in range(1,n):
      # if tie, keep going before assigning rank. otherwise...
      if sorted_vals[i-1][0] != sorted_vals[i][0]:
        # assign rank to tied (or single) values
        tie_rank = (start_idx + i-1)/2.0
        for j in range(start_idx,i):
          sorted_vals[j][0] = tie_rank
        start_idx = i
    # clean up remaining
    tie_rank = (start_idx + n-1)/2.0
    for j in range(start_idx,n):
      sorted_vals[j][0] = tie_rank

  # convert x and y to ranks
  ranked_x = [[xvals[i],i] for i in range(n)]
  ranked_y = [[yvals[i],i] for i in range(n)]
  # order by value
  ranked_x = sorted(ranked_x, key=lambda x: x[0])
  ranked_y = sorted(ranked_y, key=lambda x: x[0])
  # change values to rankings, dealing with ties
  make_ranks(ranked_x)
  make_ranks(ranked_y)
  xranks = [rank for rank,idx in sorted(ranked_x, key=lambda x: x[1])]
  yranks = [rank for rank,idx in sorted(ranked_y, key=lambda x: x[1])]

  rank_diffs = math.fsum([(xranks[i] - yranks[i])**2 for i in range(n)])
  return 1 - ((6*rank_diffs)/(n*n*n - n))



def calc_average(vals):
  """
  get the mean of a list of values
  """
  return math.fsum(vals)/len(vals)

def calc_dev(vals, sample=False):
  """
  get the sample std deviation of a list of values

  sample is whether this is for a sample, or a population
  """
  n = len(vals)
  if sample:
    n = n-1
  if n < 1:
    return 0

  mean = calc_average(vals)
  return math.sqrt(math.fsum([(x - mean)**2 for x in vals]) / n)


def get_base_technique_name(technique_name, lookup = True):
  """
  given a technique name, return the root technique name (class)
  Does a lookup for known technique names first
  """
  if lookup:
    known = {
      'DifferentialEvolution': 'DifferentialEvolution',
      'DifferentialEvolutionAlt': 'DifferentialEvolution',
      'DifferentialEvolution_20_100': 'DifferentialEvolution',
      'ComposableDiffEvolution': 'RandomThreeParentsComposableTechnique',
      'ComposableDiffEvolutionCX': 'RandomThreeParentsComposableTechnique',
      # these are basically the same as UniformGreedyMutation (except they allow a crossover)
      'ga-OX3': 'GA',
      'ga-OX1': 'GA',
      'ga-PX': 'GA',
      'ga-CX': 'GA',
      'ga-PMX': 'GA',
      'ga-base': 'UniformGreedyMutation',
      'UniformGreedyMutation05': 'UniformGreedyMutation',
      'UniformGreedyMutation10': 'UniformGreedyMutation',
      'UniformGreedyMutation20': 'UniformGreedyMutation',
      'NormalGreedyMutation05': 'NormalGreedyMutation',
      'NormalGreedyMutation10': 'NormalGreedyMutation',
      'NormalGreedyMutation20': 'NormalGreedyMutation',
      'pso-OX3': 'PSO',
      'pso-OX1': 'PSO',
      'pso-PX': 'PSO',
      'pso-CX': 'PSO',
      'pso-PMX': 'PSO',
      'RandomNelderMead': 'NelderMead',
      'RightNelderMead': 'NelderMead',
      'RegularNelderMead': 'NelderMead',
      'RandomTorczon': 'Torczon',
      'RightTorczon': 'Torczon',
      'RegularTorczon': 'Torczon',
    }
    if technique_name in known:
      return known[technique_name]
  # deal with right simplex weirdness in halide
  known = {
    'RightNelderMead': 'NelderMead',
    'RegularNelderMead': 'NelderMead',
    'RightTorczon': 'Torczon',
    'RegularTorczon': 'Torczon',
  }
  if technique_name in known:
    return known[technique_name]

  #remove operator info
  parts = technique_name.split(' ')
  #remove hyperparam info
  return parts[0].split(';')[0]

def normalize_grouped_scores(performance_info, lookup=True):
  return normalize_performance_scores(group_performance_by_base_technique(performance_info,lookup=lookup))

def group_performance_by_base_technique(performance_info, lookup=True):
  """
  Given dict mapping from technique names to dicts containing {num_runs, num_cfgs, num_bests}
  aggregates technique names by base technique by summing
  Returns dict mapping from base technique names to dict of {num_runs, num_cfgs, num_bests, score}
  where score is num_bests/num_cfgs
  """
  grouped = {}
  for technique_name in performance_info:
    orig_perf = performance_info[technique_name]

    base_name = get_base_technique_name(technique_name, lookup=lookup)
    if not base_name in grouped:
      grouped[base_name] = {'num_cfgs': 0, 'num_bests': 0, 'num_runs': 0}
    grouped_perf = grouped[base_name]

    grouped_perf['num_runs'] += orig_perf['num_runs']
    grouped_perf['num_cfgs'] += orig_perf['num_cfgs']
    grouped_perf['num_bests'] += orig_perf['num_bests']

  for base_name in grouped:
    grouped_perf = grouped[base_name]
    grouped_perf['score'] = grouped_perf['num_bests'] / (1.0*grouped_perf['num_cfgs'])

  return grouped

def normalize_performance_scores(performance_info):
  """
  Given dict mapping from technique_names to dicts containing {num_runs, num_cfgs, num_bests}
  Returns dict mapping to dicts of {num_runs, num_cfgs, num_bests, score}
  where score is num_bests/num_cfgs, normalized to the top score
  """
  normalized = {}
  best_score = 0
  for technique_name in performance_info:
    orig_perf = performance_info[technique_name]
    normalized[technique_name] = {
        'num_cfgs': orig_perf['num_cfgs'],
        'num_bests': orig_perf['num_bests'],
        'num_runs': orig_perf['num_runs'],
        'score': orig_perf['num_bests'] / (1.0*orig_perf['num_cfgs']),
      }
    best_score = max(normalized[technique_name]['score'],best_score)
  for technique_name in normalized:
    normalized[technique_name]['score'] = normalized[technique_name]['score'] / best_score
  return normalized

# returns the representation with id = num, or raises an Http404
def get_representation(rep_id):
  rep_id = int(rep_id)
  try:
    representation = models.Representation.objects.get(id=rep_id)
  except ObjectDoesNotExist:
    raise Http404("representation does not exist")
  return representation

# return the cached technique ranking with representation rep_id, or raises an Http404
def get_technique_ranking(representation):
  q = models.TechniqueRanking.objects.all().filter(representation=representation)
  try:
    return q.get()
  except ObjectDoesNotExist:
    raise Http404("ranking does not exist yet. update ranks first")
  raise Http404("error getting technique_ranking")



"""
UPLOADING RUNS
"""

# take post data and add to db. expects info to be stored under 'data'
@csrf_exempt
def upload(request):
  print "hit upload_runs"
  if request.method == 'POST':
    try:
      batch_data = json.loads(request.body)
      for data in batch_data:
        # create database entries.
        with transaction.atomic():
          if not has_tuning_run(data['uuid']):
            add_run(data)
          else:
            print '-----------------------------------'
            print " already did this tuning_run "
            print '-----------------------------------'

    except Exception as e:
      print "invalid format"
      print traceback.format_exc()
      return HttpResponse('invalid format for post data')

  return HttpResponse('upload successful?')

def add_run(data):
  if 'user' in data:
    user = models.User.get(data['user']['name'],data['user']['affiliation'])
  else:
    user = models.User.get('anonymous', '')
  # get program from program info
  prog_info = data['program']
  program = models.Program.get(prog_info['project'], prog_info['name'], prog_info['version'], prog_info['objective'])
  rep_info = data['representation']
  representation = models.Representation.get(program, rep_info['parameter_info'], rep_info['name'])
  bandit_info = data['bandit_technique']
  bandit = models.BanditTechnique.get(bandit_info['name'], bandit_info['c'], bandit_info['window'], bandit_info['subtechnique_count'])
  techniques = {}
  for sub_technique in data['bandit_sub_techniques']:
    techniques[sub_technique] = models.Technique.get(sub_technique)
  start_date = datetime.datetime.strptime(data['start_date'],"%Y-%m-%d %H:%M:%S.%f")
  # create tuning run
  tr = models.TuningRun(uuid=data['uuid'], representation=representation, bandit_technique=bandit, start_date=start_date, user=user)
  tr.save()
  #associate with techniques
  for t_name, technique in techniques.iteritems():
    models.BanditSubTechnique.objects.create(tuning_run=tr, technique=technique)

  # create bandit performance and technique performance
  performance = data['bandit_performances']
  for p in performance:
    bp = models.BanditPerformance(tuning_run=tr,
                                  bandit_technique=bandit,
                                  seconds_elapsed=p['seconds_elapsed'],
                                  total_num_cfgs=p['total_num_cfgs'],
                                  total_num_bests=p['total_num_bests'],
                                  )
    bp.save()
    for t_name, pinfo in p['technique_performances'].iteritems():
      models.TechniquePerformance.objects.create(tuning_run=tr,
                                                 technique=techniques[t_name],
                                                 num_cfgs=pinfo['num_cfgs'],
                                                 num_bests=pinfo['num_bests'],
                                                 bandit_performance=bp,
                                                )

def has_tuning_run(uuid):
  return models.TuningRun.objects.filter(uuid=uuid).exists()




