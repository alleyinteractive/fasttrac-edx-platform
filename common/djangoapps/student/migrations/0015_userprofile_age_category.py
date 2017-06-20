# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0014_auto_20170620_0143'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='age_category',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'under25', b'Under 25'), (b'25', b'25-34'), (b'35', b'35-44'), (b'45', b'45-54'), (b'55', b'55-64'), (b'65', b'65 or over')]),
        ),
    ]
