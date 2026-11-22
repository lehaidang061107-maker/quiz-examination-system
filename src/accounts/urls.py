from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("password/", views.change_password_view, name="change_password"),
    # S3-04: Admin account management & session revocation
    path("admin/users/", views.admin_user_list_view, name="admin_user_list"),
    path("admin/users/create/", views.admin_user_create_view, name="admin_user_create"),
    path("admin/users/<int:user_id>/edit/", views.admin_user_update_view, name="admin_user_update"),
    path("admin/users/<int:user_id>/lock/", views.admin_user_lock_view, name="admin_user_lock"),
    path("admin/users/<int:user_id>/unlock/", views.admin_user_unlock_view, name="admin_user_unlock"),
    path("admin/users/<int:user_id>/delete/", views.admin_user_delete_view, name="admin_user_delete"),
]
