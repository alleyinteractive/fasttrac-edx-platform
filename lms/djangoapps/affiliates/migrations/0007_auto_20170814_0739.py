# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0006_auto_20170814_0527'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='affiliateentity',
            name='geoposition_x',
        ),
        migrations.RemoveField(
            model_name='affiliateentity',
            name='geoposition_y',
        ),
        migrations.AddField(
            model_name='affiliateentity',
            name='position_latitude',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='affiliateentity',
            name='position_longitude',
            field=models.FloatField(null=True, blank=True),
        ),
    ]
