# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0007_auto_20170523_0450'),
    ]

    operations = [
        migrations.AddField(
            model_name='customcourseforedx',
            name='enrollment_type',
            field=models.CharField(default=b'PUBLIC', max_length=255, choices=[(b'PRIVATE', b'Private'), (b'PUBLIC', b'Public')]),
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 5, 23, 6, 30, 4, 71252)),
        ),
    ]
