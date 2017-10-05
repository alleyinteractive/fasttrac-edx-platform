# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import model_utils.fields
import xmodule_django.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courseware', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentTimeTracker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('course_id', xmodule_django.models.CourseKeyField(max_length=255, db_index=True)),
                ('unit_location', xmodule_django.models.LocationKeyField(max_length=255, db_index=True)),
                ('time_duration', models.IntegerField(null=True, blank=True)),
                ('student', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='studenttimetracker',
            unique_together=set([('course_id', 'unit_location', 'student')]),
        ),
    ]
