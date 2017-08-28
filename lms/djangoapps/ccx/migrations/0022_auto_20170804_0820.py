# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0021_auto_20170731_0519'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customcourseforedx',
            name='original_ccx_id',
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 8, 4, 8, 19, 58, 794334)),
        ),
    ]
