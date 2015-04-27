from django.db import models

# Create your models here.

class Program(models.Model):
  # A set of related programs
  project = models.CharField(max_length=128)
  # a specific program name within the project
  name = models.CharField(max_length=128)
  # version of the program
  version = models.CharField(max_length=128)

  # the classname of the objective function used
  objective = models.CharField(max_length=128)
  # TODO base-parameter-info <- not implemented in opentuner yet

  def __unicode__(self):
    return '-'.join([self.project, self.name, self.version, self.objective])

  @classmethod
  def get(cls, project, name, version, objective):
    try:
      obj, created = cls.objects.get_or_create(
              project = project,
              name = name,
              version = version,
              objective = objective,
            )
      return obj
    except MultipleObjectsReturned:
      return cls.objects.filter(
            project = project,
            name = name,
            version = version,
            objective = objective,
          ).first()


# the representation we use for a Program
class Representation(models.Model):
  # F.K. program
  program = models.ForeignKey(Program)
  # parameter_info
  parameter_info = models.TextField()
  # a human readable name
  name = models.CharField(max_length=128, default='')

  def __unicode__(self):
    return self.name

  @classmethod
  def get(cls, program, parameter_info, name=''):
    try:
      obj, created = cls.objects.get_or_create(
              program = program,
              name = name,
              parameter_info = parameter_info,
            )
      return obj
    except MultipleObjectsReturned:
      return cls.objects.filter(
              program = program,
              name = name,
              parameter_info = parameter_info,
            ).first()


class Technique(models.Model):
  # NAME of the technique
  name = models.TextField()

  # root name of the technique (stripped of hyperparameter or operator info)
  base_name = models.CharField(max_length=128)

  # operator information for the technique (only attached to composable techniques)
  operator_info = models.TextField(blank=True, null=True)

  def __unicode__(self):
    return self.name

  @classmethod
  def get(cls, name):
    # try getting base name/operator info
    parts = name.split(' ')
    base_name = parts[0].split(';')[0]
    try:
      operator_info = ' '.join(parts[1:])
    except:
      operator_info = None
    try:
      obj, created = cls.objects.get_or_create(name=name, base_name=base_name, operator_info=operator_info)
      return obj
    except MultipleObjectsReturned:
      return cls.objects.filter(name=name).first()


class BanditTechnique(models.Model):
  # technique name (only relevant if not bandit)
  name = models.CharField(max_length=128)

  # bandit hyperparameters - set to default if not a bandit
  c = models.FloatField()
  window = models.PositiveIntegerField()

  # number of subtechniques.
  subtechnique_count = models.PositiveSmallIntegerField()

  def __unicode__(self):
    return self.name

  @classmethod
  def get(cls, name, c, window, subtechnique_count):
    try:
      obj, created = cls.objects.get_or_create(name=name, c=c, window=window, subtechnique_count=subtechnique_count)
      return obj
    except MultipleObjectsReturned:
      return cls.objects.filter(name=name, c=c, window=window, subtechnique_count=subtechnique_count).first()


class User(models.Model):
  # a user id - defaults to anonymous
  name = models.CharField(max_length=128)
  # affiliation (university, etc)
  affiliation = models.CharField(max_length=128)

  def __unicode__(self):
    return self.name

  @classmethod
  def get(cls, name, affiliation):
    try:
      obj, created = cls.objects.get_or_create(name=name, affiliation=affiliation)
      return obj
    except MultipleObjectsReturned:
      return cls.objects.filter(name=name, affiliation=affiliation).first()


class TuningRun(models.Model):
  # representation/programf
  representation = models.ForeignKey(Representation)
  # uuid
  uuid = models.CharField(max_length=32, unique=True, primary_key=True)

  user = models.ForeignKey(User)

  # start datetime
  start_date = models.DateTimeField()

  # Bandit used (if none, use a bandit with 1 subtechnique)
  bandit_technique = models.ForeignKey(BanditTechnique)


class BanditPerformance(models.Model):
  # tuning run
  tuning_run = models.ForeignKey(TuningRun)
  # bandit technique
  bandit_technique = models.ForeignKey(BanditTechnique)
  # time elapsed
  seconds_elapsed = models.IntegerField()
  # total configs tested
  total_num_cfgs = models.IntegerField()
  # # bests found total
  total_num_bests = models.IntegerField()


class TechniquePerformance(models.Model):
  # tuning run
  tuning_run = models.ForeignKey(TuningRun) # TODO redundant?
  # technique
  technique = models.ForeignKey(Technique)
  # cfgs tested by this technique
  num_cfgs = models.IntegerField()
  # bests found by this technique
  num_bests = models.IntegerField()

  # BanditPerformance? (corresponding aggregate info)
  bandit_performance = models.ForeignKey(BanditPerformance)





# assocciative table between a tuning run and techniques used
class BanditSubTechnique(models.Model):
  tuning_run = models.ForeignKey(TuningRun)
  technique = models.ForeignKey(Technique)



# store sorted technique ranking for a given representation
class TechniqueRanking(models.Model):
  representation = models.ForeignKey(Representation) #Primary key?
  # Field to store cached information for ranking techniques. Currently a dict of
  # technique name -> {num_runs, num_cfgs, num_bests, score, avg_score, std_score}
  technique_ranking = models.TextField()
  # number of cfgs in?


