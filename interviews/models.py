from django.conf import settings
from django.db import models

from resumes.models import Resume


class InterviewSession(models.Model):
    ROLE_CHOICES = [
        ("swe", "Software Engineer"),
        ("aiml", "AI/ML Engineer"),
        ("ds", "Data Scientist"),
        ("app", "App Developer"),
        ("backend", "Backend Developer"),
        ("frontend", "Frontend Developer"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    target_role = models.CharField(max_length=40, choices=ROLE_CHOICES)
    custom_role = models.CharField(max_length=120, blank=True)
    plan = models.JSONField(default=dict, blank=True)
    resume_summary = models.JSONField(default=dict, blank=True)
    topic_index = models.PositiveIntegerField(default=0)
    followups_used = models.PositiveIntegerField(default=0)
    user_remarks = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_role_display()} interview for {self.user}"

    @property
    def role_label(self):
        return self.custom_role or self.get_target_role_display()


class Question(models.Model):
    session = models.ForeignKey(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    text = models.TextField()
    category = models.CharField(max_length=80, default="technical")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:80]


class Answer(models.Model):
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        related_name="answer",
    )
    text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:80]
