# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('affiliates', '0011_auto_20171117_0544'),
    ]

    operations = [
        migrations.CreateModel(
            name='AffiliateInvite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.CharField(max_length=255)),
                ('role', models.CharField(max_length=255, choices=[(b'ccx_coach', b'Facilitator'), (b'instructor', b'Course Manager'), (b'staff', b'Program Director')])),
                ('invited_at', models.DateTimeField(auto_now=True)),
                ('affiliate', models.ForeignKey(to='affiliates.AffiliateEntity')),
                ('invited_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
