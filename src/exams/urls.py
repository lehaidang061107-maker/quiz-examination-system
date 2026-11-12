from django.urls import path
from . import views

urlpatterns = [
    path('', views.exam_list, name='exam_list'),
    path('create/', views.exam_create_draft, name='exam_create_draft'),
    path('<int:exam_id>/edit/', views.exam_edit_draft, name='exam_edit_draft'),
    path('<int:exam_id>/participants/', views.exam_manage_participants, name='exam_manage_participants'),
]