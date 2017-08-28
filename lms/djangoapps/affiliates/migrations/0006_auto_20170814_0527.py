# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0005_auto_20170731_0519'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateentity',
            name='geoposition_x',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='affiliateentity',
            name='geoposition_y',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
