# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0008_auto_20170814_0901'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateentity',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
