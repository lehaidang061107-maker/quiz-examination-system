from django.urls import path

from . import views

app_name = "results"

urlpatterns = [
    path("teacher/", views.teacher_list, name="teacher_list"),
    path("teacher/exam/<int:exam_id>/", views.teacher_exam, name="teacher_exam"),
    path("teacher/exam/<int:exam_id>/csv/", views.teacher_exam_csv, name="teacher_exam_csv"),
    path("me/", views.student_list, name="student_list"),
    path("me/exam/<int:exam_id>/", views.student_detail, name="student_detail"),
]
