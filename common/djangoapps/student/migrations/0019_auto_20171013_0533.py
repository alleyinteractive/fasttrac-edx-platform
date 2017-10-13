# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0018_auto_20170914_0421'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='migrated_to_auth0',
            field=models.BooleanField(default=False),
        ),
    ]
