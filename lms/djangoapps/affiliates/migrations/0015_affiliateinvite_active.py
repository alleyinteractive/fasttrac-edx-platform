# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0014_affiliateentity_parent'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateinvite',
            name='active',
            field=models.BooleanField(default=True),
        ),
    ]
