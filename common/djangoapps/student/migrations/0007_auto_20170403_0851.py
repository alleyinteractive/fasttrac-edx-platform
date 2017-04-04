# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0006_logoutviewconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='company',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='newsletter',
            field=models.CharField(default=b'n', max_length=255, choices=[(b'y', b'Yes'), (b'n', b'No')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='title',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='bio',
            field=models.CharField(blank=True, max_length=3000, null=True, choices=[(b'start', b'I want to start a business'), (b'support', b'I support those who are starting businesses'), (b'have', b'I have a business'), (b'other', b'Other')]),
        ),
    ]
