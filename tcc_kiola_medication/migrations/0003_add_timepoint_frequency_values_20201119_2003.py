# Generated by Django 2.2.12 on 2020-11-19 09:03

from django.db import migrations


def addTimepointValues(apps, schema_editor):
    from tcc_kiola_medication import const, models

    from kiola.kiola_med import models as med_models

    med_models.TakingTimepoint.objects.get_or_create(
        name=const.TAKING_TIMEPOINT__CUSTOM
    )
    med_models.TakingTimepoint.objects.get_or_create(
        name=const.TAKING_TIMEPOINT__AFTERNOON
    )


def addTakingFrequencyValues(apps, schema_editor):
    from tcc_kiola_medication import const, models

    models.TakingFrequency.objects.get_or_create(
        name=const.TAKING_FREQUENCY_VALUE__ONCE
    )
    models.TakingFrequency.objects.get_or_create(
        name=const.TAKING_FREQUENCY_VALUE__DAILY
    )
    models.TakingFrequency.objects.get_or_create(
        name=const.TAKING_FREQUENCY_VALUE__WEEKLY
    )
    models.TakingFrequency.objects.get_or_create(
        name=const.TAKING_FREQUENCY_VALUE__FORTNIGHTLY
    )
    models.TakingFrequency.objects.get_or_create(
        name=const.TAKING_FREQUENCY_VALUE__MONTHLY
    )


def undo_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tcc_kiola_medication", "0002_add_reaction_types_20201113_1757"),
    ]

    operations = [
        migrations.RunPython(addTimepointValues, undo_noop),
        migrations.RunPython(addTakingFrequencyValues, undo_noop),
    ]
