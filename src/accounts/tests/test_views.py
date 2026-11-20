"""Kiểm thử view đăng ký (S3-02), đăng nhập / đăng xuất (S3-03)."""
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role, User

PASSWORD = "Kiemthu2026"


class LoginViewTests(TestCase):
    def setUp(self):
        self.url = reverse("accounts:login")
        for email, role in (
            ("admin@x.example", Role.ADMIN),
            ("teacher@x.example", Role.TEACHER),
            ("student@x.example", Role.STUDENT),
        ):
            User.objects.create_user(email, PASSWORD, full_name=email, role=role)

    def test_every_role_goes_home_after_login(self):
        for email in ("admin@x.example", "teacher@x.example", "student@x.example"):
            with self.subTest(email=email):
                self.client.logout()
                response = self.client.post(self.url, {"email": email, "password": PASSWORD})
                self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
                self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    def test_email_is_normalized(self):
        response = self.client.post(self.url, {"email": "  STUDENT@X.Example ", "password": PASSWORD})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_wrong_password_shows_error(self):
        response = self.client.post(self.url, {"email": "student@x.example", "password": "SaiMatKhau1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email hoặc mật khẩu không đúng.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_safe_next_is_followed(self):
        response = self.client.post(
            f"{self.url}?next=/results/", {"email": "student@x.example", "password": PASSWORD, "next": "/results/"}
        )
        self.assertRedirects(response, "/results/", fetch_redirect_response=False)

    def test_external_next_is_ignored(self):
        for next_url in ("https://evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)"):
            with self.subTest(next_url=next_url):
                self.client.logout()
                response = self.client.post(
                    self.url, {"email": "student@x.example", "password": PASSWORD, "next": next_url}
                )
                self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_logged_in_user_is_sent_home(self):
        self.client.post(self.url, {"email": "student@x.example", "password": PASSWORD})
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)


class LogoutViewTests(TestCase):
    def setUp(self):
        User.objects.create_user("student@x.example", PASSWORD, full_name="S")
        self.client.post(reverse("accounts:login"), {"email": "student@x.example", "password": PASSWORD})

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)

    def test_post_ends_session(self):
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)


class RegisterViewTests(TestCase):
    url = "/accounts/register/"

    def post(self, **overrides):
        data = {
            "full_name": "Nguyễn Văn A",
            "email": "sv.moi@x.example",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_register_creates_student_and_redirects_to_login(self):
        response = self.post(email="  SV.Moi@X.example ")
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        user = User.objects.get(email="sv.moi@x.example")
        self.assertEqual(user.role, Role.STUDENT)
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_email(self):
        User.objects.create_user("sv.moi@x.example", PASSWORD, full_name="Cũ")
        response = self.post()
        self.assertContains(response, "Email này đã được sử dụng.")
        self.assertEqual(User.objects.filter(email="sv.moi@x.example").count(), 1)

    def test_password_rules(self):
        cases = {
            "abc123": "tối thiểu từ 8 ký tự",
            "abcdefgh": "gồm cả chữ và số",
            "password1": "quá phổ biến",  # CommonPasswordValidator
        }
        for password, message in cases.items():
            with self.subTest(password=password):
                response = self.post(password=password, confirm_password=password)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, message)
                self.assertFalse(User.objects.filter(email="sv.moi@x.example").exists())

    def test_confirm_password_mismatch(self):
        response = self.post(confirm_password="Khac12345")
        self.assertContains(response, "Mật khẩu xác nhận không khớp.")
        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_sent_home(self):
        User.objects.create_user("student@x.example", PASSWORD, full_name="S")
        self.client.post(reverse("accounts:login"), {"email": "student@x.example", "password": PASSWORD})
        self.assertRedirects(self.client.get(self.url), reverse("home"), fetch_redirect_response=False)
