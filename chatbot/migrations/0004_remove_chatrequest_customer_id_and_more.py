# Generated by Django 4.2.3 on 2024-12-27 14:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0003_alter_thread_contact'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='chatrequest',
            name='customer_id',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='customer_id',
        ),
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
