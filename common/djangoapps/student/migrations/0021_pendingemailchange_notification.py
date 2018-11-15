# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0020_auto_20180109_0348'),
    ]

    operations = [
        migrations.AddField(
            model_name='pendingemailchange',
            name='notification',
            field=models.BooleanField(default=True),
        ),
    ]
