# Generated by Django 4.2.3 on 2025-03-08 16:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0024_contact_full_name_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='CacheResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('type', models.CharField(max_length=255)),
            ],
        ),
    ]
