# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0015_affiliateinvite_active'),
        ('ccx', '0028_auto_20171213_0911'),
    ]

    operations = [
        migrations.AddField(
            model_name='customcourseforedx',
            name='affiliate',
            field=models.ForeignKey(related_name='ccx', blank=True, to='affiliates.AffiliateEntity', null=True),
        ),
    ]
