# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0013_auto_20170619_1203'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='facebook_link',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='linkedin_link',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='twitter_link',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
