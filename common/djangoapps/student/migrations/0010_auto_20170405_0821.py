# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0009_auto_20170405_0806'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='newsletter',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True, choices=[(b'y', b'Yes'), (b'n', b'No')]),
        ),
    ]
