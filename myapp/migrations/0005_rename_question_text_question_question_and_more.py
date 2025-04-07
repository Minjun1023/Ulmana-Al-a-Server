# Generated by Django 5.1.7 on 2025-04-06 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_alter_genre_genre_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='question',
            old_name='question_text',
            new_name='question',
        ),
        migrations.RemoveField(
            model_name='question',
            name='genre',
        ),
        migrations.AddField(
            model_name='question',
            name='genre_id',
            field=models.IntegerField(default=5),
        ),
    ]
