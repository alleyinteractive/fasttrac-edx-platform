# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0015_affiliateinvite_active'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='affiliatemembership',
            unique_together=set([('member', 'affiliate', 'role')]),
        ),
    ]
