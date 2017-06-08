# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0008_auto_20170523_0630'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customcourseforedx',
            name='delivery_mode',
            field=models.CharField(default=b'IN_PERSON', max_length=255, choices=[(b'IN_PERSON', b'In Person'), (b'ONLINE_ONLY', b'Online')]),
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 6, 8, 5, 24, 53, 908103)),
        ),
    ]
