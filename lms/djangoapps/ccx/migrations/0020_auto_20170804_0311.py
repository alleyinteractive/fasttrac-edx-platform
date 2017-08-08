# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import datetime


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ccx', '0019_auto_20170803_0717'),
    ]

    operations = [
        migrations.CreateModel(
            name='CourseUpdates',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('content', models.TextField()),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterField(
            model_name='customcourseforedx',
            name='time',
            field=models.DateTimeField(default=datetime.datetime(2017, 8, 4, 3, 11, 3, 604475)),
        ),
        migrations.AddField(
            model_name='courseupdates',
            name='ccx',
            field=models.ForeignKey(to='ccx.CustomCourseForEdX'),
        ),
    ]
