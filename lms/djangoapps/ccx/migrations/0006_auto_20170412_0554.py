# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0005_auto_20170317_0634'),
    ]

    operations = [
        migrations.AddField(
            model_name='customcourseforedx',
            name='course_description',
            field=models.TextField(default=b'Course description...'),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='delivery_mode',
            field=models.CharField(default=b'IN_PERSON_REQUIRED', max_length=255, choices=[(b'IN_PERSON_REQUIRED', b'In Person - Required'), (b'IN_PERSON_OPTIONAL', b'In Person - Optional'), (b'ONLINE_ONLY', b'Online Only')]),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='fee',
            field=models.DecimalField(default=0, max_digits=5, decimal_places=2),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='location_city',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='location_postal_code',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='location_state',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 4, 12, 5, 54, 25, 260947)),
        ),
    ]
