from django.http import HttpResponse
from django.urls import path

from . import views

app_name = "attempts"


def _take_exam_placeholder(request, submission_id):
    return HttpResponse(f"Đang vào phòng thi lượt #{submission_id} (Giao diện S3-17 sẽ gắn tại đây)")


urlpatterns = [
    path("", views.exam_list, name="exam_list"),
    path("<int:exam_id>/start/", views.start_exam, name="start_exam"),
    path("submission/<int:submission_id>/", _take_exam_placeholder, name="take_exam"),
]