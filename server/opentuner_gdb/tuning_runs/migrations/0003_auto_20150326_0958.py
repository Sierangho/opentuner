# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tuning_runs', '0002_representation_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='techniqueperformance',
            name='technique',
            field=models.ForeignKey(default=1, to='tuning_runs.Technique'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='tuningrun',
            name='user',
            field=models.ForeignKey(default=1, to='tuning_runs.User'),
            preserve_default=False,
        ),
    ]
