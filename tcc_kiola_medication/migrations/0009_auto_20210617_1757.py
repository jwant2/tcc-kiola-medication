# Generated by Django 2.2.12 on 2021-06-17 07:57

from django.db import migrations


def setup_medication_types(apps, schema_editor):
    from django.contrib.auth.models import Group
    from reversion import revisions as reversion
    from kiola.utils.commons import get_system_user
    from kiola.kiola_senses import const
    from .. import pyxtures


    with reversion.create_revision():
        reversion.set_user(get_system_user())
        pyxtures.Pyxture().generate_default_medication_types()

def undo_noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('tcc_kiola_medication', '0008_medicationtype_tccprescription'),
    ]

    operations = [
        migrations.RunPython(setup_medication_types, undo_noop),
    ]
