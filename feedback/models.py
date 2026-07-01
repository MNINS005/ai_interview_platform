from django.db import models

from interviews.models import Answer, InterviewSession


class Evaluation(models.Model):
    answer = models.OneToOneField(
        Answer,
        on_delete=models.CASCADE,
        related_name="evaluation",
    )
    score = models.PositiveIntegerField(default=0)
    feedback = models.TextField()
    missing_points = models.JSONField(default=list, blank=True)
    improved_answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class FinalReport(models.Model):
    session = models.OneToOneField(
        InterviewSession,
        on_delete=models.CASCADE,
        related_name="final_report",
    )
    strengths = models.JSONField(default=list, blank=True)
    weak_areas = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
