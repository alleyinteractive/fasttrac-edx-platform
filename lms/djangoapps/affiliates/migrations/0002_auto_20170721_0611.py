# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import affiliates.models


class Migration(migrations.Migration):

    dependencies = [
        ('affiliates', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='affiliateentity',
            name='image',
            field=models.ImageField(null=True, upload_to=affiliates.models.user_directory_path, blank=True),
        ),
        migrations.AlterField(
            model_name='affiliateentity',
            name='members',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL, through='affiliates.AffiliateMembership'),
        ),
    ]
