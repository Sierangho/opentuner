#!/usr/bin/env python
# coding: utf-8
#
# Example of tuning Halide filter schedules for a photoshop plugin
#
# Halide filter functions programs must be modified by:
#  1) Inserting AUTOTUNE_HOOK(Func) directly after the algorithm definition
#     in main() 
#  2) Creating a settings file that describes the functions and variables
#     (see apps/halide_blur.settings for an example)
#  3) Compile the function to a file with name 'halide_out'
#     eg: vector<Argument> args;
#         args.push_back(input_1);
#         output_2.compile_to_file("halide_out",args);
#
# Halide can be found here: https://github.com/halide/Halide
# 
# Configured to run on Windows, requires Microsoft Visual C++ 2012 and pywin32

import adddeps  # fix sys.path

import argparse
import collections
import hashlib
import json
import logging
import math
import os
import errno
import re
import subprocess
import tempfile
import textwrap
from cStringIO import StringIO
from fn import _
from pprint import pprint
import win32file
import win32event
import win32con
import win32api
import win32gui
import time

import opentuner
from opentuner.search.manipulator import ConfigurationManipulator
from opentuner.search.manipulator import PowerOfTwoParameter
from opentuner.search.manipulator import PermutationParameter
from opentuner.search.manipulator import BooleanParameter
from opentuner.search.manipulator import ScheduleParameter
from opentuner.search.manipulator import IntegerParameter

#TODO GENERATE halide_out.def. also change the name?
COMPILE_CMD = '"{args.vcvarsall}" &' # load microsoft visual c compiler
COMPILE_CMD += 'cl "{cpp}" -I "{args.halide_dir}" -Fe"{args.tmp_dir}/gen" -link "{args.halide_dir}/halide.lib" &' # compile halide
COMPILE_CMD += '"{args.tmp_dir}/gen.exe" &' #create halide files
COMPILE_CMD += 'link -out:{args.tmp_dir}/filter.dll -dll -def:"halide_out.def" "halide_out.o" msvcrt.lib' #create dll
# gpu cmds
# COMPILE_CMD += ' "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v6.5/lib/Win32/cuda.lib"' 
# COMPILE_CMD += ' "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v6.5/lib/Win32/OpenCL.lib"' 

log = logging.getLogger('halide')

parser = argparse.ArgumentParser(parents=opentuner.argparsers())
parser.add_argument('source', help='Halide source file annotated with '
                                   'AUTOTUNE_HOOK')
parser.add_argument('image', help='Test Image file to run filter on')
parser.add_argument('--halide-dir', default='C:/Halide',
                    help='Installation directory for Halide')
parser.add_argument('--trials', default=3, type=int,
                    help='Number of times to test each schedule')
parser.add_argument('--nesting', default=2, type=int,
                    help='Maximum depth for generated loops')
parser.add_argument('--max-split-factor', default=8, type=int,
                    help='The largest value a single split() can add')
parser.add_argument('--compile-command', default=COMPILE_CMD,
                    help='How to compile generated C++ code')
parser.add_argument('--tmp-dir', # shouldn't actually change this yet (hardcoded in the plugin)
                    default='C:/temp',
                    help='Where to store generated filter dll')
parser.add_argument('--plugin-dir', # shouldn't actually change this yet (hardcoded in the plugin)
                    default='C:/temp/plugin',
                    help='Directory being watched by the plugin')
parser.add_argument('--result-dir', # shouldn't actually change this yet (hardcoded in the plugin)
                    default='C:/temp/result',
                    help='Directory plugin will write results to. Must differ from plugin-dir')
parser.add_argument('--settings-file',
                    help='Override location of json encoded settings')
parser.add_argument('--debug-error',
                    help='Stop on errors matching a given string')
parser.add_argument('--limit', type=float, default=15,
                    help='Kill compile + runs taking too long (seconds)')
parser.add_argument('--memory-limit', type=int, default=1024 ** 3,
                    help='Set memory ulimit on unix based systems')
parser.add_argument('--enable-unroll', action='store_true',
                    help='Enable .unroll(...) generation')
parser.add_argument('--enable-store-at', action='store_true',
                    help='Never generate .store_at(...)')
parser.add_argument('--gated-store-reorder', action='store_true',
                    help='Only reorder storage if a special parameter is given')

parser.add_argument('--ps-api-dir', default = 'PhotoshopAPI', # not used yet - tobe used to build plugin
                    help='Location of PhotoshopAPI from the photoshop cs6 sdk')
parser.add_argument('--photoshop-dir', default = r'C:\Program Files (x86)\Adobe\Adobe Photoshop CS6')
parser.add_argument('--vcvarsall', default='C:/Program Files (x86)/Microsoft Visual Studio 12.0/VC/vcvarsall.bat',
                    help='Directory where Microsoft VS vcvarsall.bat is located')

group = parser.add_mutually_exclusive_group()
group.add_argument('--random-test', action='store_true',
                   help='Generate a random configuration and run it')
group.add_argument('--random-source', action='store_true',
                   help='Generate a random configuration and print source ')


# class HalideRandomConfig(opentuner.search.technique.SearchTechnique):
#   def desired_configuration(self):
#     '''
#     inject random configs with no compute_at() calls to kickstart the search process
#     '''
#     cfg = self.manipulator.random()
#     for k in cfg.keys():
#       if re.match('.*_compute_level', k):
#         cfg[k] = LoopLevel.INLINE
#     return cfg
#
# technique.register(bandittechniques.AUCBanditMetaTechnique([
#         HalideRandomConfig(),
#         differentialevolution.DifferentialEvolutionAlt(),
#         evolutionarytechniques.UniformGreedyMutation(),
#         evolutionarytechniques.NormalGreedyMutation(mutation_rate=0.3),
#       ], name = "HalideMetaTechnique"))


class HalideTuner(opentuner.measurement.MeasurementInterface):
  def __init__(self, args):
    # args.technique = ['HalideMetaTechnique']
    super(HalideTuner, self).__init__(args, program_name=args.source)
    self.template = open(args.source).read()
    
    self.min_collection_cost = float('inf')
    if not args.settings_file:
      args.settings_file = os.path.splitext(args.source)[0] + '.settings'
   
    with open(args.settings_file) as fd:
      self.settings = json.load(fd)
    self.post_dominators = post_dominators(self.settings)
    # set "program_version" based on hash of halidetuner.py, program source
    h = hashlib.md5()
    #with open(__file__) as src:
    #  h.update(src.read())
    with open(args.source) as src:
      h.update(src.read())
    self._version = h.hexdigest()

    self.build_plugin();

    #make sure tmp directories and files created
    try:
      os.makedirs(args.tmp_dir)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise        
    try:
      os.makedirs(args.plugin_dir)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise
    try:
      os.makedirs(args.result_dir)
    except OSError as exception:
      if exception.errno != errno.EEXIST:
        raise

    f = open(args.plugin_dir + '/tilesize.txt','w')
    f.write("")
    f.close()

    #generate script to init photoshop plugin
    f = open('start_plugin.jsx', 'w')
    f.write(
      '''
      #target photoshop

      var idOpn = charIDToTypeID( "Opn " );
      var desc1 = new ActionDescriptor();
      var idnull = charIDToTypeID( "null" );
      desc1.putPath( idnull, new File( "%(imgPath)s" ) );
      executeAction( idOpn, desc1, DialogModes.NO );

      var id = stringIDToTypeID( "d9543b0c-3c91-11d4-97bc-00b0d0204936" );
      executeAction( id, undefined, DialogModes.NO );

      ''' % {"imgPath": args.image}

      )
    f.close()
    # return #TODO remove testing
    self.kill_photoshop()
    self.start_photoshop()



  def start_photoshop(self):
    subprocess.Popen(self.args.photoshop_dir+'/photoshop.exe')
    time.sleep(15) #wait for photoshop to start up and trial notification to go away

    os.startfile('start_plugin.jsx')
    time.sleep(1)
    
    # set focus to alert and 
    toplist = []
    winlist = []
    def enum_callback(hwnd, results):
      winlist.append((hwnd, win32gui.GetWindowText(hwnd)))

    win32gui.EnumWindows(enum_callback, toplist)
    alert = [(hwnd, title) for hwnd, title in winlist if 'script alert' in title.lower()]
    for al in alert:
      try:
        win32gui.SetForegroundWindow(al[0])
        win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0) #press enter
        win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0) #press enter
      except: 
        print "Error confirming script start"
    
    # wait for notification that plugin has started
    change_handle = win32file.FindFirstChangeNotification (
                  self.args.result_dir,
                  0,
                  win32con.FILE_NOTIFY_CHANGE_LAST_WRITE)
    try:
      i = 0
      # wait up to a minute for photoshop to start
      while i < 120:
        result = win32event.WaitForSingleObject(change_handle, 500)
        if result == win32con.WAIT_OBJECT_0:
          break
        i += 1
          
    finally:
      win32file.FindCloseChangeNotification(change_handle)
    return


  def kill_photoshop(self):
    return os.system("taskkill /im photoshop.exe /f")

  def build_plugin(self):
    return
    #TODO build the plugin after inserting temp folder locations
    # for now, must build plugin through visual studio externally and copy the resulting .8bf plugin file
    # into photoshop's plugin directory. The files modified photoshop's tutorial dissolve plugin to do this are under 
    # /common

    # cmd = '"{args.vcvarsall}" &' 
    # cmd += r'cl /c /I"{args.ps_api_dir}" /I"{args.ps_api_dir}/Photoshop" /I"{args.halide_dir}" /I"{args.ps_api_dir}\PICA_SP" /I".\common" /I".\common\includes" /ZI /W4 /WX- /Od /Oy- /D ISOLATION_AWARE_ENABLED=1 /D WIN32=1 /D _DEBUG /D _CRT_SECURE_NO_DEPRECATE /D _SCL_SECURE_NO_DEPRECATE /D _WINDOWS /D _USRDLL /D DISSOLVE_EXPORTS /D _VC80_UPGRADE=0x0710 /D _USING_V110_SDK71_ /D _WINDLL /D _MBCS /Gm- /EHsc /RTC1 /MDd /GS /fp:precise /Zc:wchar_t /Zc:forScope /Fo".\output/" /Fd".\.output\vc120.pdb" /FR".\Debug\\" /Gd /TP /analyze- /errorReport:prompt /MP /GS /F30000000 .\common\sources\Logger.cpp .\common\sources\PIUFile.cpp .\common\sources\Timer.cpp .\common\halide_funcs.cpp'
    # cmd = cmd.format(args=self.args)

    # compile_result = self.call_program(cmd, limit=self.args.limit,
    #                                    memory_limit=self.args.memory_limit)
    # if compile_result['returncode'] != 0:

    #   log.error('compile failed: %s', compile_result)
    
  def compute_order_parameter(self, func):
    name = func['name']
    schedule_vars = []
    schedule_deps = dict()
    for var in func['vars']:
      schedule_vars.append((var, 0))
      for i in xrange(1, self.args.nesting):
        schedule_vars.append((var, i))
        schedule_deps[(var, i - 1)] = [(var, i)]
    return ScheduleParameter('{0}_compute_order'.format(name), schedule_vars,
                             schedule_deps)

  def manipulator(self):
    """
    The definition of the manipulator is meant to mimic the Halide::Schedule
    data structure and defines the configuration space to search
    """
    manipulator = HalideConfigurationManipulator(self)
    manipulator.add_parameter(HalideComputeAtScheduleParameter(
      'schedule', self.args, self.settings['functions'],
      self.post_dominators))
    for func in self.settings['functions']:
      name = func['name']
      manipulator.add_parameter(PermutationParameter(
        '{0}_store_order'.format(name), func['vars']))
      manipulator.add_parameter(
        BooleanParameter('{0}_store_order_enabled'.format(name)))
      manipulator.add_parameter(self.compute_order_parameter(func))
      for var in func['vars']:
        manipulator.add_parameter(PowerOfTwoParameter(
          '{0}_vectorize'.format(name), 1, self.args.max_split_factor))
        manipulator.add_parameter(PowerOfTwoParameter(
          '{0}_unroll'.format(name), 1, self.args.max_split_factor))
        manipulator.add_parameter(BooleanParameter(
          '{0}_parallel'.format(name)))
        for nesting in xrange(1, self.args.nesting):
          manipulator.add_parameter(PowerOfTwoParameter(
            '{0}_splitfactor_{1}_{2}'.format(name, nesting, var),
            1, self.args.max_split_factor))
    #Add tile size parameters (will be )
    manipulator.add_parameter(IntegerParameter('horizontal_tile_size', 1, 256))
    manipulator.add_parameter(IntegerParameter('vertical_tile_size', 1, 256))

    return manipulator

  def cfg_to_schedule(self, cfg):
    """
    Produce a Halide schedule from a configuration dictionary
    """
    o = StringIO()
    cnt = 0
    temp_vars = list()
    schedule = ComputeAtStoreAtParser(cfg['schedule'], self.post_dominators)
    compute_at = schedule.compute_at
    store_at = schedule.store_at

    # build list of all used variable names
    var_names = dict()
    var_name_order = dict()
    for func in self.settings['functions']:
      name = func['name']
      compute_order = cfg['{0}_compute_order'.format(name)]
      for var in func['vars']:
        var_names[(name, var, 0)] = var
        for nesting in xrange(1, self.args.nesting):
          split_factor = cfg.get('{0}_splitfactor_{1}_{2}'.format(
            name, nesting, var), 0)
          if split_factor > 1 and (name, var, nesting - 1) in var_names:
            var_names[(name, var, nesting)] = '_{var}{cnt}'.format(
              func=name, var=var, nesting=nesting, cnt=cnt)
            temp_vars.append(var_names[(name, var, nesting)])
          cnt += 1
      var_name_order[name] = [var_names[(name, v, n)] for v, n in compute_order
                              if (name, v, n) in var_names]

    # set a schedule for each function
    for func in self.settings['functions']:
      name = func['name']
      inner_var_name = var_name_order[name][-1] # innermost variable in the reordered list for this func
      vectorize = cfg['{0}_vectorize'.format(name)]
      if self.args.enable_unroll:
        unroll = cfg['{0}_unroll'.format(name)]
      else:
        unroll = 1

      # print >> o, 'Halide::Func(funcs["%s"])' % name

      print >> o, '%s' % name

      for var in func['vars']:
        # handle all splits
        for nesting in xrange(1, self.args.nesting):
          split_factor = cfg.get('{0}_splitfactor_{1}_{2}'.format(
            name, nesting, var), 0)
          if split_factor <= 1:
            break

          for nesting2 in xrange(nesting + 1, self.args.nesting):
            split_factor2 = cfg.get('{0}_splitfactor_{1}_{2}'.format(
              name, nesting2, var), 0)
            if split_factor2 <= 1:
              break
            split_factor *= split_factor2
          var_name = var_names[(name, var, nesting)]
          last_var_name = var_names[(name, var, nesting - 1)]
          
          # apply unroll, vectorize factors to all surrounding splits iff we're the innermost var
          if var_name == inner_var_name:
            split_factor *= unroll
            split_factor *= vectorize

          print >> o, '.split({0}, {0}, {1}, {2})'.format(
            last_var_name, var_name, split_factor)

      # drop unused variables and truncate (Halide supports only 10 reorders)
      if len(var_name_order[name]) > 1:
        print >> o, '.reorder({0})'.format(
            ', '.join(reversed(var_name_order[name][:10])))

      # reorder_storage
      store_order_enabled = cfg['{0}_store_order_enabled'.format(name)]
      if store_order_enabled or not self.args.gated_store_reorder:
        store_order = cfg['{0}_store_order'.format(name)]
        if len(store_order) > 1:
          print >> o, '.reorder_storage({0})'.format(', '.join(store_order))

      if unroll > 1:
        # apply unrolling to innermost var
        print >> o, '.unroll({0}, {1})'.format(
          var_name_order[name][-1], unroll * vectorize)

      if vectorize > 1:
        # apply vectorization to innermost var
        print >> o, '.vectorize({0}, {1})'.format(
          var_name_order[name][-1], vectorize)
      
      # compute_at(not root)
      if (compute_at[name] is not None and
              len(var_name_order[compute_at[name][0]]) >= compute_at[name][1]):
        at_func, at_idx = compute_at[name]
        try:
          at_var = var_name_order[at_func][-at_idx]
          print >> o, '.compute_at({0}, {1})'.format(at_func, at_var)
          if not self.args.enable_store_at:
            pass  # disabled
          elif store_at[name] is None:
            print >> o, '.store_root()'
          elif store_at[name] != compute_at[name]:
            at_func, at_idx = store_at[name]
            at_var = var_name_order[at_func][-at_idx]
            print >> o, '.store_at({0}, {1})'.format(at_func, at_var)
        except IndexError:
          # this is expected when at_idx is too large
          # TODO: implement a cleaner fix
          pass
      # compute_root
      else:
        parallel = cfg['{0}_parallel'.format(name)]
        if parallel:
          # only apply parallelism to outermost var of root funcs
          print >> o, '.parallel({0})'.format(var_name_order[name][0])
        print >> o, '.compute_root()'

      print >> o, ';'

    if temp_vars:
      return 'Halide::Var {0};\n{1}'.format(
        ', '.join(temp_vars), o.getvalue())
    else:
      return o.getvalue()

  def schedule_to_source(self, schedule):
    """
    Generate a temporary Halide cpp file with schedule inserted
    """
    # TESTING - no schedule
    # return self.template
    def repl_autotune_hook(match):
      # std::map<std::string, Halide::Internal::Function> funcs = Halide::Internal::find_transitive_calls((%(func)s).function());
        
      tmpl = '''
        
        %(sched)s

    '''
      return tmpl % {"sched": schedule.replace('\n', '\n        ')}

    source = re.sub(r'\n\s*AUTOTUNE_HOOK\(\s*([a-zA-Z0-9_]+)\s*\)',
                    repl_autotune_hook, self.template)
    return source


  def run_schedule(self, schedule, cfg):
    """
    Generate a temporary Halide cpp file with schedule inserted and compile.
    Run output exe to generate .o and .h file
    Build dll
    notify Photoshop and pass tile size to test
    Wait for response.
    """
    print "new schedule"
    #print schedule
    #print "=========================="
    if self.build_dll(self.schedule_to_source(schedule)): 
      # return # TODO testing build_dll only
      return self.notify_photoshop(cfg)
    #failed to build
    return None

  def notify_photoshop(self, cfg):
    change_handle = win32file.FindFirstChangeNotification (
                      self.args.result_dir,
                      0,
                      win32con.FILE_NOTIFY_CHANGE_LAST_WRITE)
    #write to a directory that the photoshop plugin is listening to
    f = open(self.args.plugin_dir + '/tilesize.txt','w')
    # TESTING - fix tile size
    # f.write(str('80 3232'))
    f.write(str(cfg['horizontal_tile_size'] * 16) + ' ' + str(cfg['vertical_tile_size'] * 16))
    f.close()
    #wait for a response
    try:
      while 1:
        result = win32event.WaitForSingleObject(change_handle, int(self.args.limit * 1000)) # TIMEOUT HERE
        if result == win32con.WAIT_OBJECT_0:
          f = open(self.args.result_dir + '/result.txt','r')
          line =  f.readline()
          f.close()
          if line:
            result = float(line)
            print "Took:" 
            print result
            break
          else:
            win32file.FindNextChangeNotification(change_handle)
        else:
          # it didn't work. Kill restart photoshop, return None.
          self.kill_photoshop()
          self.start_photoshop()
          return None
    finally:
      win32file.FindCloseChangeNotification(change_handle)

    return result

  def build_dll(self, source):
    #remove existing files
    try:
      os.remove(self.args.tmp_dir+"/filter.dll")
      os.remove("halide_out.o")
      os.remove(self.args.tmp_dir+"/gen.exe")
    except:
      pass
    # print "HALIDE SOURCE:"
    # print source
    cmd = ''
    cppfile = tempfile.NamedTemporaryFile(suffix='.cpp', prefix='halide',
                                     dir=self.args.tmp_dir, delete=False)
    cppfile.write(source)
    cppfile.flush()
    cppfile.close()
    cmd = self.args.compile_command.format(cpp=cppfile.name, args=self.args)

    # print "COMPILE COMMAND:"
    # print cmd

    compile_result = self.call_program(cmd, limit=self.args.limit,
                                       memory_limit=self.args.memory_limit)
    if compile_result['returncode'] != 0:

      log.error('compile failed: %s', compile_result)
      try:
        os.remove(os.path.splitext(os.path.basename(cppfile.name))[0]+".obj")
        os.remove(cppfile.name)
      except:
        pass
      return False

    try:
      os.remove(os.path.splitext(os.path.basename(cppfile.name))[0]+".obj")
      os.remove(cppfile.name)
    except:
      pass
    return True

  def run_cfg(self, cfg, limit=0):
    try:
      schedule = self.cfg_to_schedule(cfg)
    except:
      log.exception('error generating schedule')
      return None
    return self.run_schedule(schedule, cfg)

  def run(self, desired_result, input, limit):
    time = self.run_cfg(desired_result.configuration.data, limit)
    if time is not None:
      return opentuner.resultsdb.models.Result(time=time)
    else:
      return opentuner.resultsdb.models.Result(state='ERROR',
                                               time=float('inf'))

  def save_final_config(self, configuration):
    """called at the end of tuning"""
    print 'Final Configuration:'
    print self.cfg_to_schedule(configuration.data)
    print 'Tilesize: ' + str(configuration.data['horizontal_tile_size'] * 16) + ' px , ' + str(configuration.data['vertical_tile_size'] * 16) + ' px'
    self.kill_photoshop()
    
    f = open(self.args.plugin_dir + '/finalSchedule.txt','w')
    f.write("Final Configuration:\n" + self.cfg_to_schedule(configuration.data) + "\n Tilesize: " + str(configuration.data['horizontal_tile_size'] * 16) + ' px , ' + str(configuration.data['vertical_tile_size'] * 16) + ' px')
    f.close()

  def debug_log_schedule(self, filename, source):
    open(filename, 'w').write(source)
    print 'offending schedule written to {0}'.format(filename)

  def debug_schedule(self, filename, source):
    self.debug_log_schedule(filename, source)
    raw_input('press ENTER to continue')


class ComputeAtStoreAtParser(object):
  """
  A recursive descent parser to force proper loop nesting, and enforce post
  dominator scheduling constraints

  For each function input will have tokens like:
  ('foo', 's') = store_at location for foo
  ('foo', '2'), ('foo', '1') = opening the loop nests for foo,
                               the inner 2 variables
  ('foo', 'c') = the computation of foo, and closing all loop nests

  The order of these tokens define a loop nest tree which we reconstruct
  """

  def __init__(self, tokens, post_dominators):
    self.tokens = list(tokens)  # input, processed back to front
    self.post_dominators = post_dominators
    self.compute_at = dict()
    self.store_at = dict()
    self.process_root()

  def process_root(self):
    old_len = len(self.tokens)
    out = []
    while self.tokens:
      if self.tokens[-1][1] == 's':
        # store at root
        self.store_at[self.tokens[-1][0]] = None
        out.append(self.tokens.pop())
      else:
        self.process_loopnest(out, [])
    self.tokens = list(reversed(out))
    assert old_len == len(self.tokens)

  def process_loopnest(self, out, stack):
    func, idx = self.tokens[-1]
    out.append(self.tokens.pop())
    if idx != 'c':
      raise Exception('Invalid schedule')

    self.compute_at[func] = None
    for targ_func, targ_idx in reversed(stack):
      if targ_func in self.post_dominators[func]:
        self.compute_at[func] = (targ_func, targ_idx)
        break

    close_tokens = [(f, i) for f, i in self.tokens if f == func and i != 's']
    while close_tokens:
      if self.tokens[-1] == close_tokens[-1]:
        # proper nesting
        close_tokens.pop()
        out.append(self.tokens.pop())
      elif self.tokens[-1][1] == 'c':
        self.process_loopnest(out, stack + close_tokens[-1:])
      elif self.tokens[-1][1] == 's':
        # self.tokens[-1] is computed at this level
        if func in self.post_dominators[self.tokens[-1][0]]:
          self.store_at[self.tokens[-1][0]] = close_tokens[-1]
        else:
          self.store_at[self.tokens[-1][0]] = None
        out.append(self.tokens.pop())
      else:
        # improper nesting, just close the loop and search/delete close_tokens
        out.extend(reversed(close_tokens))
        self.tokens = [x for x in self.tokens if x not in close_tokens]
        break


class HalideConfigurationManipulator(ConfigurationManipulator):
  def __init__(self, halide_tuner):
    super(HalideConfigurationManipulator, self).__init__()
    self.halide_tuner = halide_tuner

  def hash_config(self, config):
    """
    Multiple configs can lead to the same schedule, so we provide a custom
    hash function that hashes the resulting schedule instead of the raw config.
    This will lead to fewer duplicate tests.
    """
    self.normalize(config)
    try:
      schedule = self.halide_tuner.cfg_to_schedule(config)
      return hashlib.sha256(schedule).hexdigest()
    except:
      log.warning('error hashing config', exc_info=True)
      return super(HalideConfigurationManipulator, self).hash_config(config)


class HalideComputeAtScheduleParameter(ScheduleParameter):
  def __init__(self, name, args, functions, post_dominators):
    """
    Custom ScheduleParameter that normalizes using ComputeAtStoreAtParser
    """
    super(HalideComputeAtScheduleParameter, self).__init__(
      name, *self.gen_nodes_deps(args, functions))
    self.post_dominators = post_dominators

  def gen_nodes_deps(self, args, functions):
    """
    Compute the list of nodes and point-to-point deps to provide to base class
    """
    nodes = list()
    deps = collections.defaultdict(list)
    for func in functions:
      last = None
      for idx in reversed(['c'] + # 'c' = compute location (and close loops)
          range(1, len(func['vars']) * args.nesting + 1) +
          ['s']):  # 's' = storage location
        name = (func['name'], idx)
        if last is not None:
          # variables must go in order
          deps[last].append(name)
        last = name
        nodes.append(name)
        if idx == 'c':
          # computes must follow call graph order
          for callee in func['calls']:
            deps[(callee, 'c')].append(name)
    return nodes, deps

  def normalize(self, cfg):
    """
    First enforce basic point-to-point deps (in base class), then call
    ComputeAtStoreAtParser to normalize schedule.
    """
    super(HalideComputeAtScheduleParameter, self).normalize(cfg)
    cfg[self.name] = ComputeAtStoreAtParser(cfg[self.name],
                                            self.post_dominators).tokens


def post_dominators(settings):
  """
  Compute post dominator tree using textbook iterative algorithm for the
  call graph defined in settings
  """
  functions = [f['name'] for f in settings['functions']]
  calls = dict([(f['name'], set(f['calls'])) for f in settings['functions']])
  inverse_calls = collections.defaultdict(set)
  for k, callees in calls.items():
    for v in callees:
      inverse_calls[v].add(k)
  dom = {functions[-1]: set([functions[-1]])}
  for f in functions[:-1]:
    dom[f] = set(functions)
  change = True
  while change:
    change = False
    for f in functions[:-1]:
      old = dom[f]
      dom[f] = set([f]) | reduce(
        _ & _, [dom[c] for c in inverse_calls[f]], set(functions))
      if old != dom[f]:
        change = True
  return dom


def random_test(args):
  """
  Generate and run a random schedule
  """

  opentuner.tuningrunmain.init_logging()
  m = HalideTuner(args)
  cfg = m.manipulator().random()
  print 'Configuration:'
  pprint(cfg)
  print
  # return #TODO remove, testing
  schedule = m.cfg_to_schedule(cfg)
  print 'Schedule', m.run_schedule(schedule, cfg)
  print 'Halide Schedule:'
  print  schedule
  print 'Tilesize: ' + str(cfg['horizontal_tile_size'] * 16) + ' px , ' + str(cfg['vertical_tile_size'] * 16) + ' px'

  m.kill_photoshop()


def random_source(args):
  """
  Dump the source code of a random schedule
  """
  opentuner.tuningrunmain.init_logging()
  m = HalideTuner(args)
  cfg = m.manipulator().random()
  schedule = m.cfg_to_schedule(cfg)
  source = m.schedule_to_source(schedule)
  print source


def main(args):
  if args.random_test:
    random_test(args)
  elif args.random_source:
    random_source(args)
  else:
    HalideTuner.main(args)


if __name__ == '__main__':
  main(parser.parse_args())
