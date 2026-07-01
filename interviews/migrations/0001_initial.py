# Generated for the AI Interview Prep MVP.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("resumes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "target_role",
                    models.CharField(
                        choices=[
                            ("swe", "Software Engineer"),
                            ("aiml", "AI/ML Engineer"),
                            ("ds", "Data Scientist"),
                            ("app", "App Developer"),
                            ("backend", "Backend Developer"),
                            ("frontend", "Frontend Developer"),
                            ("other", "Other"),
                        ],
                        max_length=40,
                    ),
                ),
                ("custom_role", models.CharField(blank=True, max_length=120)),
                ("plan", models.JSONField(blank=True, default=dict)),
                ("user_remarks", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("completed", "Completed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "resume",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="resumes.resume"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("category", models.CharField(default="technical", max_length=80)),
                ("order", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="interviews.interviewsession",
                    ),
                ),
            ],
            options={"ordering": ["order"]},
        ),
        migrations.CreateModel(
            name="Answer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "question",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answer",
                        to="interviews.question",
                    ),
                ),
            ],
        ),
    ]
