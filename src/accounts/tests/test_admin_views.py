from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role, User, UserStatus


class AdminAccountManagementViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "StrongPass123!"
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self.password,
            full_name="Admin User",
            role=Role.ADMIN,
        )
        self.student = User.objects.create_user(
            email="student1@example.com",
            password=self.password,
            full_name="Student One",
            role=Role.STUDENT,
        )
        self.teacher = User.objects.create_user(
            email="teacher1@example.com",
            password=self.password,
            full_name="Teacher One",
            role=Role.TEACHER,
        )

    def test_non_admin_cannot_access_user_list(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:admin_user_list"))
        self.assertEqual(response.status_code, 403)  # giống mọi trang khác: sai vai trò -> 403

    def test_admin_can_list_search_filter_and_paginate_users(self):
        for i in range(12):
            User.objects.create_user(
                email=f"extra{i}@example.com",
                password=self.password,
                full_name=f"Extra User {i}",
                role=Role.STUDENT,
            )
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts:admin_user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 10)

        filtered = self.client.get(reverse("accounts:admin_user_list"), {"q": "student1", "role": Role.STUDENT})
        self.assertEqual(filtered.status_code, 200)
        self.assertContains(filtered, "student1@example.com")

    def test_admin_create_user_via_post(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:admin_user_create"),
            {
                "full_name": "New Student",
                "email": "new.student@example.com",
                "password": self.password,
                "role": Role.STUDENT,
            },
        )
        self.assertRedirects(response, reverse("accounts:admin_user_list"))
        self.assertTrue(User.objects.filter(email="new.student@example.com").exists())

    def test_role_change_revokes_target_user_sessions(self):
        student_client = Client()
        student_client.force_login(self.student)
        session_key = student_client.session.session_key
        self.assertTrue(Session.objects.filter(session_key=session_key).exists())

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:admin_user_update", args=[self.student.pk]),
            {
                "full_name": self.student.full_name,
                "email": self.student.email,
                "role": Role.TEACHER,
            },
        )
        self.assertRedirects(response, reverse("accounts:admin_user_list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, Role.TEACHER)
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

    def test_lock_user_confirmation_and_session_revocation(self):
        student_client = Client()
        student_client.force_login(self.student)
        session_key = student_client.session.session_key

        self.client.force_login(self.admin)
        get_resp = self.client.get(reverse("accounts:admin_user_lock", args=[self.student.pk]))
        self.assertEqual(get_resp.status_code, 200)

        post_resp = self.client.post(reverse("accounts:admin_user_lock", args=[self.student.pk]))
        self.assertRedirects(post_resp, reverse("accounts:admin_user_list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, UserStatus.LOCKED)
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

    def test_delete_user_confirmation_flow(self):
        self.client.force_login(self.admin)
        get_resp = self.client.get(reverse("accounts:admin_user_delete", args=[self.teacher.pk]))
        self.assertEqual(get_resp.status_code, 200)

        post_resp = self.client.post(reverse("accounts:admin_user_delete", args=[self.teacher.pk]))
        self.assertRedirects(post_resp, reverse("accounts:admin_user_list"))
        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.status, UserStatus.DELETED)

    def test_admin_menu_links_to_user_list(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("accounts:admin_user_list")}"')

    def test_long_full_name_shows_form_error_instead_of_500(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:admin_user_create"),
            {"full_name": "A" * 101, "email": "long@example.com", "password": self.password, "role": Role.STUDENT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="long@example.com").exists())
        self.assertIn("full_name", response.context["form"].errors)

        response = self.client.post(
            reverse("accounts:admin_user_update", args=[self.student.pk]),
            {"full_name": "B" * 101, "email": self.student.email, "role": Role.STUDENT},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("full_name", response.context["form"].errors)

    def test_unlock_locked_user(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:admin_user_lock", args=[self.student.pk]))
        list_resp = self.client.get(reverse("accounts:admin_user_list"))
        self.assertContains(list_resp, reverse("accounts:admin_user_unlock", args=[self.student.pk]))

        get_resp = self.client.get(reverse("accounts:admin_user_unlock", args=[self.student.pk]))
        self.assertContains(get_resp, "Mở khóa tài khoản")
        post_resp = self.client.post(reverse("accounts:admin_user_unlock", args=[self.student.pk]), follow=True)
        self.assertRedirects(post_resp, reverse("accounts:admin_user_list"))
        self.assertContains(post_resp, f"Đã mở khóa tài khoản {self.student.email}.")
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, UserStatus.ACTIVE)

        login = Client().post(reverse("accounts:login"), {"email": self.student.email, "password": self.password})
        self.assertRedirects(login, reverse("home"))

    def test_cannot_lock_deleted_user_by_direct_post(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:admin_user_delete", args=[self.student.pk]))
        resp = self.client.post(reverse("accounts:admin_user_lock", args=[self.student.pk]), follow=True)
        self.assertContains(resp, "Chỉ khóa được tài khoản đang hoạt động.")
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, UserStatus.DELETED)

    def test_admin_cannot_lock_or_delete_self(self):
        User.objects.create_user(email="admin2@example.com", password=self.password, full_name="Admin Hai",
                                 role=Role.ADMIN)
        self.client.force_login(self.admin)
        list_resp = self.client.get(reverse("accounts:admin_user_list"))
        self.assertNotContains(list_resp, reverse("accounts:admin_user_lock", args=[self.admin.pk]))
        self.assertNotContains(list_resp, reverse("accounts:admin_user_delete", args=[self.admin.pk]))
        resp = self.client.post(reverse("accounts:admin_user_lock", args=[self.admin.pk]), follow=True)
        self.assertContains(resp, "Không thể khóa hoặc xóa chính tài khoản bạn đang dùng.")
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.status, UserStatus.ACTIVE)
