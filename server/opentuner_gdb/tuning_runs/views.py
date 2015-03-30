from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import traceback
import datetime

from tuning_runs import models
# Create your views here.

def index(request):
  return HttpResponse("Hello, world. This is the index for tuning_runs")

def update_ranks(request, num):
  rep_id = int(num)
  try:
    representation = models.Representation.objects.get(id=rep_id)
  except ObjectDoesNotExist:
    return HttpResponse("representation does not exist")

  s = "updating technique rankings for " + representation.program.project + "-" + representation.program.name

  response = [s]
  response.append(representation.parameter_info)

  q = get_technique_performances(representation=representation)
  num_runs = len(q.distinct('tuning_run'))
  response.append("aggregated over " + str(num_runs) + " runs")

  technique_scores = {}
  for t in q:
    name = t.technique.name
    if not name in technique_scores:
      technique_scores[name] = {'num_cfgs': 0, 'num_bests': 0, 'num_runs': 0}
    technique_scores[name]['num_runs'] = technique_scores[name]['num_runs'] + 1
    technique_scores[name]['num_cfgs'] = technique_scores[name]['num_cfgs'] + t.num_cfgs
    technique_scores[name]['num_bests'] = technique_scores[name]['num_bests'] + t.num_bests

  for name in technique_scores:
    technique_scores[name]['score'] = technique_scores[name]['num_bests'] / (1.0*technique_scores[name]['num_cfgs'])

  sorted_x = sorted(technique_scores.items(), reverse=True, key=lambda x: x[1]['score'])
  for x in sorted_x:
    response.append(str(x))

  return HttpResponse("<html><body><p>%s</p></body></html>" % '</p><p>'.join(response))


def score_techniques(technique, representation, stage):
  """
  aggregate technique performances related to a bandit performance
  technique = which technique
  representation = which representation
  stage = which stage of tuning (#cfg cutoff)
  """
  pass

def get_bandit_performances(stage=None, representation=None):
  """
  Get query set of bandit performances associated with a representation at a specified stage of tuning

  :param stage: BanditPerformance will have at least this number of cfgs tested. a value of None gets performances from the end of tuning.
  :param representation: which representation to consider. A value of None considers all representations
  :returns: query set
  """
  pass

def get_technique_performances(stage=None, representation=None):
  """
  Get query set of technique performances associated with a representation at a specified stage of tuning

  :param stage: Associated BanditPerformance will have at least this number of cfgs tested. a value of None gets performances from the end of tuning.
  :param representation: which representation to consider. A value of None considers all representations
  :returns: query set
  """
  q = models.TechniquePerformance.objects.all()
  if representation is not None:
    q = q.filter(bandit_performance__tuning_run__representation=representation)
  if stage is None:
    q = q.filter(bandit_performance__seconds_elapsed=-1)
  else:
    #TODO deal with stage
    q = q.filter(bandit_performances__seconds_elapsed=-1)
  return q

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




