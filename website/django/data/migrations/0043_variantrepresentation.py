# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2019-06-21 12:51
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0042_auto_20190610_1433'),
    ]

    operations = [
        migrations.CreateModel(
            name='VariantRepresentation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Genomic_Coordinate_hg38', models.TextField()),
                ('Description', django.contrib.postgres.fields.jsonb.JSONField(default={})),
            ],
        ),
        migrations.RunSQL("""
            create index variantrep_hg38_hash_idx on data_variantrepresentation using hash ("Genomic_Coordinate_hg38")
            """, reverse_sql="""
            drop index if exists variantrep_hg38_hash_idx
            """
        )
    ]
