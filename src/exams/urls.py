from django.urls import path

from . import views

app_name = "exams"

urlpatterns = [
    path("", views.exam_list, name="list"),
    path("create/", views.exam_create, name="create"),
    path("<int:exam_id>/", views.exam_detail, name="detail"),
    path("<int:exam_id>/edit/", views.exam_edit, name="edit"),
    path("<int:exam_id>/questions/", views.exam_questions, name="questions"),
    path("<int:exam_id>/publish/", views.exam_publish, name="publish"),
]
