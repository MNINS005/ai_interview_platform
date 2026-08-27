from django.urls import path

from .views import dashboard, final_remarks, question, report, start_interview, transcribe_audio

app_name = "interviews"

urlpatterns = [
    path("", dashboard, name="dashboard"),
    path("start/", start_interview, name="start"),
    path("<int:session_id>/question/", question, name="question"),
    path("<int:session_id>/remarks/", final_remarks, name="final_remarks"),
    path("<int:session_id>/report/", report, name="report"),
    path("transcribe-audio/", transcribe_audio, name="transcribe_audio"),
]
