# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0002_auto_20170721_0611'),
    ]

    operations = [
        migrations.AlterField(
            model_name='affiliateentity',
            name='address',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='city',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='description',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='facebook',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='linkedin',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='phone_number',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='twitter',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='zipcode',
            field=models.CharField(default=b'', max_length=255, null=True, blank=True),
        ),
    ]
