# Generated by Django 5.2.1 on 2025-05-26 08:24

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_alter_domain_options_alter_domain_dkim_verified_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='domain',
            options={},
        ),
        migrations.AlterUniqueTogether(
            name='domain',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='domain',
            name='domain_name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='domain',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
