from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def resume_upload_placeholder(request):
    return render(request, "resumes/upload.html")
