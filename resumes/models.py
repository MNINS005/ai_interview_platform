from django.conf import settings
from django.db import models


class Resume(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=120, default="My Resume")
    file = models.FileField(upload_to="uploads/resumes/", blank=True, null=True)
    raw_text = models.TextField(blank=True)
    parsed_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user}"
