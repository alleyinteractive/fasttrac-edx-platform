# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0009_affiliateentity_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='affiliateentity',
            name='description',
            field=models.TextField(default=b'', null=True, blank=True),
        ),
    ]
