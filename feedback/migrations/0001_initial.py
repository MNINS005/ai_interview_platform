# Generated for the AI Interview Prep MVP.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("interviews", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Evaluation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveIntegerField(default=0)),
                ("feedback", models.TextField()),
                ("missing_points", models.JSONField(blank=True, default=list)),
                ("improved_answer", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "answer",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluation",
                        to="interviews.answer",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="FinalReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("strengths", models.JSONField(blank=True, default=list)),
                ("weak_areas", models.JSONField(blank=True, default=list)),
                ("recommendations", models.JSONField(blank=True, default=list)),
                ("summary", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="final_report",
                        to="interviews.interviewsession",
                    ),
                ),
            ],
        ),
    ]
