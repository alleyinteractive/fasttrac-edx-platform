# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0015_userprofile_age_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='public_email',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
