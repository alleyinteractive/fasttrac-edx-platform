# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0006_auto_20170412_0554'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customcourseforedx',
            name='fee',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 5, 23, 4, 50, 24, 248780)),
        ),
    ]
