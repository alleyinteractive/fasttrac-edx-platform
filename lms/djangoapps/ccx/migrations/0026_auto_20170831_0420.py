# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0025_auto_20170814_0739'),
    ]

    operations = [
        migrations.AddField(
            model_name='customcourseforedx',
            name='location_latitude',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='location_longitude',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
