from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from interviews.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("interviews/", include("interviews.urls")),
    path("resumes/", include("resumes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
