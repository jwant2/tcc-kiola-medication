# Generated by Django 2.2.12 on 2022-06-10 04:51

import django.db.models.deletion
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tcc_kiola_medication", "0010_auto_20210707_1417"),
    ]

    operations = [
        migrations.AddField(
            model_name="tccprescription",
            name="editor",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to=settings.AUTH_USER_MODEL,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tccprescription",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
