from django.contrib import admin
from django.urls import include, path

from .views import health, home

urlpatterns = [
    path("", home, name="home"),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("questions/", include("questions.urls")),
    path("exams/", include("exams.urls")),
    path("attempts/", include("attempts.urls")),
    path("results/", include("results.urls")),
]
