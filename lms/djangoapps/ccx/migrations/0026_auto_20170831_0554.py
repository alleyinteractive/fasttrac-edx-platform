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
            name='end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='enrollment_end_date',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime.now),
        ),
    ]
