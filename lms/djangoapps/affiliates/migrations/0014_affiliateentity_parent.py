# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0013_auto_20180109_0348'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateentity',
            name='parent',
            field=models.ForeignKey(related_name='children', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='affiliates.AffiliateEntity', null=True),
        ),
    ]
