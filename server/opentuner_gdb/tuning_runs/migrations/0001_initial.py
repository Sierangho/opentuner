# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BanditPerformance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('seconds_elapsed', models.IntegerField()),
                ('total_num_cfgs', models.IntegerField()),
                ('total_num_bests', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BanditSubTechnique',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BanditTechnique',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('c', models.FloatField()),
                ('window', models.PositiveIntegerField()),
                ('subtechnique_count', models.PositiveSmallIntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('project', models.CharField(max_length=128)),
                ('name', models.CharField(max_length=128)),
                ('version', models.CharField(max_length=128)),
                ('objective', models.CharField(max_length=128)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Representation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('parameter_info', models.TextField()),
                ('program', models.ForeignKey(to='tuning_runs.Program')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Technique',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.TextField()),
                ('base_name', models.CharField(max_length=128)),
                ('operator_info', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TechniquePerformance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('num_cfgs', models.IntegerField()),
                ('num_bests', models.IntegerField()),
                ('bandit_performance', models.ForeignKey(to='tuning_runs.BanditPerformance')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TechniqueRanking',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('technique_ranking', models.TextField()),
                ('representation', models.ForeignKey(to='tuning_runs.Representation')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TuningRun',
            fields=[
                ('uuid', models.CharField(max_length=32, unique=True, serialize=False, primary_key=True)),
                ('start_date', models.DateTimeField()),
                ('bandit_technique', models.ForeignKey(to='tuning_runs.BanditTechnique')),
                ('representation', models.ForeignKey(to='tuning_runs.Representation')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('affiliation', models.CharField(max_length=128)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='techniqueperformance',
            name='tuning_run',
            field=models.ForeignKey(to='tuning_runs.TuningRun'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='banditsubtechnique',
            name='technique',
            field=models.ForeignKey(to='tuning_runs.Technique'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='banditsubtechnique',
            name='tuning_run',
            field=models.ForeignKey(to='tuning_runs.TuningRun'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='banditperformance',
            name='bandit_technique',
            field=models.ForeignKey(to='tuning_runs.BanditTechnique'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='banditperformance',
            name='tuning_run',
            field=models.ForeignKey(to='tuning_runs.TuningRun'),
            preserve_default=True,
        ),
    ]
