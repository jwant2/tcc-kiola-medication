# Generated by Django 2.2.12 on 2021-01-12 06:46

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('tcc_kiola_medication', '0004_add_med_obs_profile_20201207_1607'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledtaking',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='scheduledtaking',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='scheduledtaking',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
