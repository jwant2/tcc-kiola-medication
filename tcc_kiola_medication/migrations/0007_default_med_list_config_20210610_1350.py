# Generated by Django 2.2.12 on 2021-06-10 03:50

from django.db import migrations

def setup_default_med_list_config(apps, schema_editor):
    from django.contrib.auth.models import Group
    from reversion import revisions as reversion
    from kiola.utils.commons import get_system_user
    from kiola.kiola_senses import const
    from .. import pyxtures


    with reversion.create_revision():
        reversion.set_user(get_system_user())
        pyxtures.Pyxture().create_default_medication_list()
        pyxtures.Pyxture().set_up_extra_meds()

def undo_noop(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('tcc_kiola_medication', '0006_auto_20210423_1434'),
    ]

    operations = [
        migrations.RunPython(setup_default_med_list_config, undo_noop),
    ]
