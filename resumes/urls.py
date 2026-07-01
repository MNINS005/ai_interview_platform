from django.urls import path

from .views import resume_upload_placeholder

app_name = "resumes"

urlpatterns = [
    path("upload/", resume_upload_placeholder, name="upload"),
]
