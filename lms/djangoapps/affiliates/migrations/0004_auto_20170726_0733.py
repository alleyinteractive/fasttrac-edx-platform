# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0003_auto_20170721_0636'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='affiliateentity',
            unique_together=set([('email', 'name')]),
        ),
    ]
