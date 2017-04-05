# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0007_auto_20170403_0851'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='state',
            field=models.CharField(default=b'na', max_length=255, null=True, blank=True, choices=[(b'y', b'Yes'), (b'n', b'No')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='zipcode',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
    ]
