from django.urls import path  # noqa: F401


from questions import views

app_name = "questions"

urlpatterns = [
    path("", views.question_list, name="list"),
]
