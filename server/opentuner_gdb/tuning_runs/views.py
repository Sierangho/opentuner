from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import MultipleObjectsReturned
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import traceback
import datetime

from tuning_runs import models
# Create your views here.

def index(request):
  return HttpResponse("Hello, world. This is the index for tuning_runs")

# get info about tuning_runs

def add_runs(request, name):
  response = "Here's the url to hit to add runs with name %s"
  return HttpResponse(response % name)

# take post data and add to db. expects info to be stored under 'data'
@csrf_exempt
def upload(request):
  print "hit upload_runs"
  if request.method == 'POST':
    try:
      data = json.loads(request.body)
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




