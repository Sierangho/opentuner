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
import random

from tuning_runs import models
# Create your views here.

def index(request):
  return HttpResponse("Hello, world. This is the index for tuning_runs")

@csrf_exempt
def recommend_technique(request):
  """
  recommend a technique to use
  """
  if request.method == 'POST':
    try:
      # expect request body to have data with performance and problem
      # performance should be dict from technique names to {num_cfgs, num_bests}
      # problem should let us match to an existing representation
      data = json.loads(request.body)
      #TODO put checks for performance, then representation using fallthroughs
      performance = data['performance']
      representation = get_or_create_representation(data['problem'])
      print representation.id

      tr = None
      if len(performance) > 2:
        total_cfgs = 0
        for t_name in performance:
          performance[t_name]['score'] = calc_technique_score(performance[t_name]['num_bests'], performance[t_name]['num_cfgs'])
          total_cfgs += performance[t_name]['num_cfgs']
        tr = recommend_technique_ranking_by_performance(performance,
                                                        stage=total_cfgs,
                                                        spearman=False,
                                                        exclude_id=representation.id)
    except Exception as e:
      response = HttpResponse(traceback.format_exc())
      response.status_code = 500
      return response

  # not enough techniques in performance to rank, suggest by representation
  if tr is None:
    print "Using representation"
    r = get_closest_representation(representation.parameter_info, technique_rankings=True, exclude_id=representation.id)
    tr = get_technique_ranking(r)
    if tr is None:
      # just guess at random
      print "GUESSING A RANDOM TECHNIQUE RANKING"
      rindex = random.randint(0, models.TechniqueRanking.objects.count() - 1)
      tr = models.TechniqueRanking.objects.all()[rindex]

  performance = json.loads(tr.technique_ranking)
  # filter out things that haven't been used much
  performance = {k:v for (k,v) in performance.iteritems() if v['num_runs'] > 0 and (k != 'RightNelderMead' and k != 'RightTorczon')}

  #return a list of sorted techniques by performance
  return HttpResponse(json.dumps(sorted(performance, key=lambda x: performance[x]['score'], reverse=True )))



def test_recommend(request):
  #TESTING
  # generate some performance
  techniques = []

  random_idx = random.randint(0, models.TuningRun.objects.count() - 1)
  print random_idx
  random_obj = models.TuningRun.objects.all()[random_idx]
  representation = random_obj.representation
  s = str(representation.id) + '-' + representation.program.project + '-' + representation.program.name
  response = ["random representation: " + s]
  q = models.TechniquePerformance.objects.all().filter(tuning_run=random_obj).filter(bandit_performance__total_num_cfgs=50)
  performance = aggregate_technique_performances(q)
  for tp in q:
    techniques.append(tp.technique.name)
  response.append(str(techniques))
  tr = recommend_technique_ranking_by_performance(performance, spearman=False)
  if tr is None:
    response.append("not enough overlap")
    r = get_closest_representation(representation.parameter_info, exclude_id=representation.id)
    tr = get_technique_ranking(r)
  response.append("recommending representation {}-{}".format(tr.representation.program.project, tr.representation.program.name))
  response.append(recommend_technique_from_technique_ranking(tr, techniques))
  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


def recommend_technique_from_technique_ranking(technique_ranking, techniques):
  """
  Given a TechniqueRanking object, get a technique name from it.
  """
  performance = json.loads(technique_ranking.technique_ranking)
  sorted_techniques = sorted(performance, key=lambda x: performance[x]['score'], reverse=True )
  for technique_name in sorted_techniques:
    #TODOS deal with techniques with operators that aren't relevant here?
    #      weight the techniques and randomly return one?

    # return first technique not in given techniques
    if technique_name not in techniques:
      return technique_name
    print 'skipping technique ' + technique_name

def recommend_technique_ranking_by_performance(performance, stage=None, spearman=False, exclude_id=None):
  """
  given technique performance (and what stage of tuning)
      dictionary from technique name -> {num_cfgs, num_bests}
  return a TechniqueRanking its most similar to
  """
  #TODO filter by stage
  q = qget_technique_rankings(stage=stage)
  if q.count() == 0:
    q = qget_technique_rankings()

  best = -2 # correlation scores from -1 to 1
  recommended = None
  for tr in q:
    if not exclude_id is None and tr.representation.id == exclude_id:
      continue
    other_performance = json.loads(tr.technique_ranking)
    xvals = []
    yvals = []
    count = 0
    for technique in performance:
      if technique in other_performance:
        xvals.append(performance[technique]['score'])
        yvals.append(other_performance[technique]['score'])
        count += 1
    if count < 3:
      continue
    if spearman:
      correlation_score = calc_spearman(xvals, yvals)
    else:
      correlation_score = calc_pearson(xvals, yvals)
    if correlation_score > best:
      best = correlation_score
      recommended = tr
  print recommended.representation.program.project + '-' + recommended.representation.program.name
  print best
  return recommended




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


def get_closest_representation(pinfo, exclude_id=None, representations=None, technique_rankings=False):
  """
  Return the Representation with the most similar parameter_info to pinfo.
  Only looks at those in TechniqueRanking if technique_rankings is True

  Ignores the id passed in exclude_id
  """
  param_count = parse_parameter_info(pinfo)
  best_distance = 0
  best = None

  if representations is None:
    if technique_rankings:
      trs = qget_technique_rankings()
      representations = []
      for tr in trs:
        representations.append(tr.representation)
    else:
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

  This is asymmetric, penalizing the other set not containing a parameter of this set
  more than this set not containing an element of the other set.

  In other words, a subset is closer to a superset than the superset is to the subset.
  """
  distance = 0
  # handle parameters in param_count2 not in param_count1
  for p in param_count2:
    if not p in param_count1:

      distance += 1 # penalize by 1 order of magnitude

  for p in param_count1:
    if p not in param_count2:
      #
      distance += (math.log10(param_count1[p]) + 1)**2
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

def view_technique_overlap(request, rep_id):
  representation = get_representation(rep_id)
  technique_ranking = json.loads(get_technique_ranking(representation).technique_ranking)
  response = []
  response.append('num techniques : ' + str(len(technique_ranking)))
  response.append('================================================')

  rep_ids = []
  overlap = []
  for tr in models.TechniqueRanking.objects.all().order_by('representation__program__project','representation__id'):
    other_ranks = json.loads(tr.technique_ranking)
    rep_ids.append(str(tr.representation.id))
    count = 0
    for t in technique_ranking:
      if t in other_ranks:
        count += 1
    overlap.append(str(count))
  response.append(', '.join(rep_ids))
  response.append('<table><tbody><tr><td>' + '</td><td>'.join(overlap) + '</td></tr></tbody></table>')

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


def update_rank(representation):
  #TODO update for non-fixed stage of tuning
  q = qget_technique_performances(representation=representation)
  technique_scores = aggregate_technique_performances(q)
  # cache the ranking
  try:
    tr = models.TechniqueRanking.objects.get(representation=representation)
    tr.technique_ranking = json.dumps(technique_scores)
    tr.save()
  except ObjectDoesNotExist:
    tr = models.TechniqueRanking(representation=representation,
                                 technique_ranking=json.dumps(technique_scores))
    tr.save()


def update_tsp(request):
  for i in range(68,82):
    update_rank(get_representation(i))
  return HttpResponse("done")

def update_old(request):
  for i in [58,59,60,61,62,63,48,50,51,53,57,64,65,67]:
    update_rank(get_representation(i))
  for i in [45,46,47,56,55,52]:
    update_rank(get_representation(i))
  return HttpResponse("done")

def update_ranks(request, rep_id):
  representation = get_representation(rep_id)
  #peta bricks / halide
  #[58,59,60,61,62,63,48,50,51,53,57,64,65,67]
  # mario - 45 46
  # rosenbrock - 47 56
  # gcc - 55
  # tsp - 52 (old)
  # tsp - range(68,76)
  # atsp - range(76,82)

  s = "updating technique rankings for " + representation.program.project + "-" + representation.program.name

  response = [s]
  response.append(representation.parameter_info)

  q = qget_technique_performances(representation=representation) # TODO non-fixed stage


  num_runs = len(q.distinct('tuning_run'))
  response.append("aggregated over " + str(num_runs) + " runs")

  technique_scores = aggregate_technique_performances(q)

  update_rank(representation)


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

  xdev = calc_dev(xvals)
  ydev = calc_dev(yvals)
  if xdev == 0 or ydev == 0:
    if xdev == 0 and ydev == 0:
      return 1
    return 0


  covariance = math.fsum([(xvals[i] - xmean)*(yvals[i] - ymean) for i in range(n)])
  return covariance/(xdev*ydev*n)

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

def calc_technique_score(num_bests, num_cfgs):
  if num_cfgs == 0:
    return 0
  return num_bests / (1.0*num_cfgs)

def is_composable_technique_name(technique_name):
  """
  check if its a composable technique name by seeing if there's operator info
  """
  return parts

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
  # # deal with right simplex weirdness in halide
  # known = {
  #   'RightNelderMead': 'NelderMead',
  #   'RegularNelderMead': 'NelderMead',
  #   'RightTorczon': 'Torczon',
  #   'RegularTorczon': 'Torczon',
  # }
  # if technique_name in known:
  #   return known[technique_name]

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
    grouped_perf['score'] = calc_technique_score(grouped_perf['num_bests'], grouped_perf['num_cfgs'])

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
        'score': calc_technique_score(orig_perf['num_bests'],orig_perf['num_cfgs']),
      }
    best_score = max(normalized[technique_name]['score'],best_score)
  for technique_name in normalized:
    normalized[technique_name]['score'] = normalized[technique_name]['score'] / best_score
  return normalized

# returns the representation with id = num, or raises an Http404
def get_representation(rep_id):
  """ returns the representation with given id, or raises an Http404 """
  rep_id = int(rep_id)
  try:
    representation = models.Representation.objects.get(id=rep_id)
  except ObjectDoesNotExist:
    raise Http404("representation does not exist")
  return representation

# return the cached technique ranking with representation rep_id, or raises an Http404
def get_technique_ranking(representation, stage=None):
  """ returns the technique ranking with given representation/stage, or raises an Http404 """
  q = qget_technique_rankings(representation=representation, stage=stage)
  try:
    return q.get()
  except ObjectDoesNotExist:
    raise Http404("ranking does not exist yet. update ranks first")
  raise Http404("error getting technique_ranking")

def get_or_create_program(prog_info):
  """get or create a Program. prog_info should be a dict with field values"""
  return models.Program.get(prog_info['project'], prog_info['name'], prog_info['version'], prog_info['objective'])


def get_or_create_representation(info):
  """
  get or create a Representation.
  input info should be a dict with field values. The 'program' field should
  go to a dict that can be passed into get_or_create_program
  """
  program = get_or_create_program(info['program'])
  rep_info = info['representation']
  return models.Representation.get(program, rep_info['parameter_info'], rep_info['name'])


def qget_bandit_performances(representation=None, stage=None):
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

def qget_technique_performances(representation=None, stage=None):
  """
  Get query set of technique performances associated with a representation at a specified stage of tuning

  :param stage: Associated TechniquePerformance will have stage < #cfgs_tested <= stage rounded up to nearest 50.
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

def qget_technique_rankings(representation=None, stage=None):
  """
  Get a query set of technique rankings associated with a representation at a specified stage

  :param stage: Associated TechniqueRanking will have stage < #cfgs_tested <= stage rounded up to nearest 50.
  a value of None gets performances from the end of tuning.
  :param representation: which representation to consider. A value of None considers all representations
  :returns: query set
  """
  q = models.TechniqueRanking.objects.all()
  if representation is not None:
    q = q.filter(representation=representation)

  #TODO add stage filter when models is updated

  # if stage is None:
  #   q = q.filter(stage=-1)
  # else:
  #   # round up
  #   upper_limit = ((stage / 50) + 1)*50
  #   q = q.filter(stage__gt=stage)
  #   q = q.filter(stage__lte=upper_limit)
  return q



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

  representation = get_or_create_representation(data)

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




