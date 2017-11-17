# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0010_auto_20171113_0320'),
    ]

    operations = [
        migrations.AddField(
            model_name='affiliateentity',
            name='address_2',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='affiliateentity',
            name='phone_number_private',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
    ]
