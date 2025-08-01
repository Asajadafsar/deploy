# Generated by Django 5.2.1 on 2025-07-18 17:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presale', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='presaletransaction',
            old_name='wallet_address',
            new_name='user_wallet_address',
        ),
        migrations.AddField(
            model_name='presaletransaction',
            name='user_wallet_network',
            field=models.CharField(choices=[('TRC20', 'TRC20'), ('BEP20', 'BEP20')], default='0000', max_length=10),
            preserve_default=False,
        ),
    ]
