# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0011_userprofile_affiliate_organization_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='secondary_address',
            field=models.TextField(null=True, blank=True),
        ),
    ]
