# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ccx', '0027_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customcourseforedx',
            name='delivery_mode',
            field=models.CharField(default=b'IN_PERSON', max_length=255, choices=[(b'IN_PERSON', b'In-Person'), (b'ONLINE_ONLY', b'Online'), (b'BLENDED', b'Blended')]),
        ),
    ]
