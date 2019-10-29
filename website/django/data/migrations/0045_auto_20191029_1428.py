# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2019-10-29 14:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data', '0044_add_gnomad_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='variant',
            name='Genomic_Coordinate_hg36',
        ),
        migrations.RemoveField(
            model_name='variant',
            name='Hg36_End',
        ),
        migrations.RemoveField(
            model_name='variant',
            name='Hg36_Start',
        ),
        migrations.RunSQL("""
            DROP TABLE IF EXISTS words;
            CREATE TABLE words AS SELECT DISTINCT left(word, 300) as word, release_id FROM (
            SELECT regexp_split_to_table(lower("Genomic_Coordinate_hg38"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("Genomic_Coordinate_hg37"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("Clinical_significance_ENIGMA"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("Gene_Symbol"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("Reference_Sequence"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("HGVS_cDNA"), '[\s|:''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("BIC_Nomenclature"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant UNION
            SELECT regexp_split_to_table(lower("HGVS_Protein"), '[\s|''"]') as word, "Data_Release_id" as release_id from variant
            )
            AS combined_words;

            CREATE INDEX words_idx ON words(word text_pattern_ops);
        """),
        migrations.RunSQL(
            """
            DROP MATERIALIZED VIEW IF EXISTS currentvariant;
            CREATE MATERIALIZED VIEW currentvariant AS (
                SELECT * FROM "variant" WHERE (
                    "id" IN ( SELECT DISTINCT ON ("Genomic_Coordinate_hg38") "id" FROM "variant" ORDER BY "Genomic_Coordinate_hg38" ASC, "Data_Release_id" DESC )
                )
            );
            """
        )
    ]
