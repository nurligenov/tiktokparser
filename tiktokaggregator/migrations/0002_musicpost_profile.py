# Generated by Django 3.2.8 on 2024-01-26 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tiktokaggregator', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='musicpost',
            name='profile',
            field=models.CharField(max_length=255, null=True),
        ),
    ]