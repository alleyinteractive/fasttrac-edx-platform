# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0017_userprofile_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='filled_presurvey_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, max_length=6, null=True, db_index=True, choices=[(b'm', b'Male'), (b'f', b'Female'), (b'o', b'Other/Prefer Not To Say')]),
        ),
    ]
