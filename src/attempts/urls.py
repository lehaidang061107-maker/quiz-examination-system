from django.urls import path

from . import views

app_name = "attempts"

urlpatterns = [
    path("", views.exam_list, name="exam_list"),
    path("<int:exam_id>/start/", views.start_exam, name="start_exam"),
    path("submission/<int:submission_id>/", views.take_exam, name="take_exam"),
    path("submission/<int:submission_id>/save-answer/", views.save_answer_api, name="save_answer_api"),
    path("submission/<int:submission_id>/submit/", views.submit_exam, name="submit_exam"),
]