# Generated by Django 4.2.3 on 2025-03-19 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0025_cacheresponse'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default='2025-03-19'),
            preserve_default=False,
        ),
    ]
