# Generated by Django 4.2.3 on 2025-03-28 12:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0028_toolcall_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='SkipMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='conversation',
            name='conversation_type',
            field=models.CharField(choices=[('Human', 'Human'), ('AI', 'AI'), ('ToolCall', 'ToolCall'), ('Agent', 'Agent'), ('AUDIO_MSG_ERROR', 'AUDIO_MSG_ERROR'), ('Skip_Message', 'Skip_Message'), ('APC_FACE_CARD', 'APC_FACE_CARD')], max_length=20, null=True),
        ),
    ]
