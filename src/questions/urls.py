from django.urls import path

from questions import views


app_name = "questions"

urlpatterns = [
    path("", views.question_list, name="list"),
    path("create/", views.question_create, name="create"),
    path("<int:question_id>/edit/", views.question_edit, name="edit"),
    path("<int:question_id>/revision/", views.question_revision, name="revision"),
    path("<int:question_id>/delete/", views.question_delete, name="delete"),
    path("<int:question_id>/archive/", views.question_archive, name="archive"),
    path("<int:question_id>/restore/", views.question_restore, name="restore"),
]
