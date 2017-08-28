# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0004_auto_20170726_0733'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateentity',
            name='slug',
            field=models.SlugField(default=b'', unique=True, max_length=255),
        ),
        migrations.AddField(
            model_name='affiliateentity',
            name='website',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
    ]
