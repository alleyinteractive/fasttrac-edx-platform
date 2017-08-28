# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0007_auto_20170814_0739'),
    ]

    operations = [
        migrations.RenameField(
            model_name='affiliateentity',
            old_name='position_latitude',
            new_name='location_latitude',
        ),
        migrations.RenameField(
            model_name='affiliateentity',
            old_name='position_longitude',
            new_name='location_longitude',
        ),
    ]
