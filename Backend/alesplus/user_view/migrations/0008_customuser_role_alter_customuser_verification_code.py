# Generated by Django 5.2.1 on 2025-06-15 08:04

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_view', '0007_partnershiprequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('user', 'User'), ('admin', 'Admin'), ('moderator', 'Moderator')], default='user', max_length=20),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='verification_code',
            field=models.CharField(blank=True, max_length=6, null=True, validators=[django.core.validators.RegexValidator(message='Verification code must be exactly 6 digits', regex='^\\d{6}$')]),
        ),
    ]
