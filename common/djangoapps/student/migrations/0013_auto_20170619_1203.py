# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0012_userprofile_secondary_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='education',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'less_than_high_school', b'Less than high school graduate'), (b'high_school', b'High school graduate - Diploma or GED'), (b'technical_school', b'Technical, trade, or vocational school'), (b'college_without_degree', b'Some college, but no degree'), (b'associate_degree', b'Associate Degree'), (b'bachelors_degree', b"Bachelor's Degree"), (b'more_than_masters_degree', b"Master's, Doctorate, or Professional Degree")]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ethnicity',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'american', b'American Indian/Alaska Native'), (b'asian', b'Asian'), (b'pacific', b'Pacific Islander'), (b'african_american', b'Black/African American'), (b'hispanic', b'Latino/Hispanic'), (b'middle_eastern', b'Middle Eastern'), (b'white', b'White - non Hispanic'), (b'multiracial', b'Multiracial'), (b'na', b'Prefer not to answer'), (b'other', b'Other')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='immigrant_status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'y', b'Yes'), (b'n', b'No')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='veteran_status',
            field=models.CharField(blank=True, max_length=255, null=True, choices=[(b'y', b'Yes'), (b'n', b'No')]),
        ),
    ]
