# Generated by Django 4.2.3 on 2025-02-16 17:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0011_pricingcall'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClubClass',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('class_name', models.CharField(max_length=30)),
                ('class_type', models.CharField(choices=[('adult', 'Adult'), ('junior', 'Junior')], default='adult', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='ClubProgram',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('program_name', models.CharField(max_length=30)),
                ('class_name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chatbot.clubclass')),
            ],
        ),
        migrations.CreateModel(
            name='ProgramSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chatbot.clubprogram')),
            ],
        ),
        migrations.AddConstraint(
            model_name='programschedule',
            constraint=models.UniqueConstraint(fields=('program', 'start_time', 'end_time'), name='unique_program_schedule'),
        ),
    ]
