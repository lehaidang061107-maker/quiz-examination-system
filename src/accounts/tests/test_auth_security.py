from datetime import timedelta
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.forms import StudentRegisterForm
from accounts.models import Role, User, UserStatus
from config.tests.factories import PASSWORD, make_user


def _register_confirm_field() -> str:
    form = StudentRegisterForm()
    for candidate in ("password_confirm", "confirm_password", "password2", "re_password"):
        if candidate in form.fields:
            return candidate
    for name in form.fields:
        if "password" in name and name != "password":
            return name
    return "password_confirm"


class AuthAndSecurityTests(TestCase):
    def setUp(self):
        self.student = make_user(role=Role.STUDENT, email="sv1@test.example", name="Sinh Viên Một")
        self.other_student = make_user(role=Role.STUDENT, email="sv2@test.example", name="Sinh Viên Hai")
        self.teacher = make_user(role=Role.TEACHER, email="gv1@test.example", name="Giảng Viên Một")
        self.admin = make_user(role=Role.ADMIN, email="admin1@test.example", name="Quản Trị Viên")
        self.confirm_field = _register_confirm_field()

    # --- 1. Auth lifecycle: đăng ký, đăng nhập, đăng xuất, khóa sau 5 lần sai, hết phiên ---

    def test_register_valid_and_reject_duplicate_email_or_weak_password(self):
        reg_url = reverse("accounts:register")

        resp_ok = self.client.post(
            reg_url,
            {
                "full_name": "Sinh Viên Mới",
                "email": "sv.moi@test.example",
                "password": PASSWORD,
                self.confirm_field: PASSWORD,
            },
        )
        self.assertEqual(
            resp_ok.status_code,
            302,
            msg=f"Expected 302 on valid register, got {resp_ok.status_code}. Context form errors: {resp_ok.context.get('form').errors if resp_ok.context and resp_ok.context.get('form') else ''}",
        )
        self.assertRedirects(resp_ok, reverse("accounts:login"))
        created = User.objects.filter(email="sv.moi@test.example").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.role, Role.STUDENT)
        self.assertNotEqual(created.password, PASSWORD)

        # Trùng email
        resp_dup = self.client.post(
            reg_url,
            {
                "full_name": "Trùng Email",
                "email": "sv.moi@test.example",
                "password": PASSWORD,
                self.confirm_field: PASSWORD,
            },
        )
        self.assertEqual(resp_dup.status_code, 200)
        self.assertEqual(User.objects.filter(email="sv.moi@test.example").count(), 1)

        # Mật khẩu yếu (thiếu chữ/số hoặc quá ngắn)
        resp_weak = self.client.post(
            reg_url,
            {
                "full_name": "Mật Khẩu Yếu",
                "email": "weak@test.example",
                "password": "123",
                self.confirm_field: "123",
            },
        )
        self.assertEqual(resp_weak.status_code, 200)
        self.assertFalse(User.objects.filter(email="weak@test.example").exists())

    def test_login_logout_destroys_session_and_cookie_security_flags(self):
        login_url = reverse("accounts:login")
        logout_url = reverse("accounts:logout")
        cookie_name = settings.SESSION_COOKIE_NAME

        resp = self.client.post(login_url, {"email": self.student.email, "password": PASSWORD})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

        session_key = self.client.session.session_key
        self.assertTrue(Session.objects.filter(session_key=session_key).exists())
        self.assertIn(cookie_name, resp.cookies)
        cookie = resp.cookies[cookie_name]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

        logout_resp = self.client.post(logout_url)
        self.assertRedirects(logout_resp, login_url)
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

    def test_lock_temporary_after_five_failed_login_attempts(self):
        login_url = reverse("accounts:login")
        target_email = self.student.email

        for _ in range(5):
            resp = self.client.post(login_url, {"email": target_email, "password": "sai_mat_khau_1"})
            self.assertEqual(resp.status_code, 200)

        self.student.refresh_from_db()
        is_locked = (
            getattr(self.student, "status", None) == UserStatus.LOCKED
            or getattr(self.student, "locked_until", None) is not None
        )
        self.assertTrue(is_locked)

        resp_after_lock = self.client.post(login_url, {"email": target_email, "password": PASSWORD})
        self.assertEqual(resp_after_lock.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_expired_session_is_rejected_and_redirects_to_login(self):
        cookie_name = settings.SESSION_COOKIE_NAME
        self.client.post(reverse("accounts:login"), {"email": self.student.email, "password": PASSWORD})
        session_key = self.client.session.session_key
        db_session = Session.objects.get(session_key=session_key)
        db_session.expire_date = timezone.now() - timedelta(minutes=1)
        db_session.save()

        expired_client = Client()
        expired_client.cookies[cookie_name] = session_key
        resp = expired_client.get(reverse("accounts:admin_user_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp["Location"])

    # --- 2. Role & ownership (IDOR) ---

    def test_wrong_role_cannot_access_admin_urls_and_cannot_idor_other_user(self):
        for non_admin in (self.student, self.teacher):
            c = Client()
            c.post(reverse("accounts:login"), {"email": non_admin.email, "password": PASSWORD})

            for url in (
                reverse("accounts:admin_user_list"),
                reverse("accounts:admin_user_create"),
                reverse("accounts:admin_user_update", args=[self.other_student.pk]),
                reverse("accounts:admin_user_lock", args=[self.other_student.pk]),
                reverse("accounts:admin_user_delete", args=[self.other_student.pk]),
            ):
                resp = c.get(url)
                self.assertIn(resp.status_code, (302, 403))
                if resp.status_code == 302:
                    self.assertNotIn("admin/users", resp["Location"])

        c_student = Client()
        c_student.post(reverse("accounts:login"), {"email": self.student.email, "password": PASSWORD})
        post_idor = c_student.post(
            reverse("accounts:admin_user_update", args=[self.other_student.pk]),
            {
                "full_name": "Bị Sửa Trái Phép",
                "email": self.other_student.email,
                "role": Role.ADMIN,
            },
        )
        self.assertIn(post_idor.status_code, (302, 403))
        self.other_student.refresh_from_db()
        self.assertEqual(self.other_student.full_name, "Sinh Viên Hai")
        self.assertEqual(self.other_student.role, Role.STUDENT)

    # --- 3. CSRF, XSS, SQL injection & sensitive info disclosure ---

    def test_csrf_token_present_and_missing_csrf_is_rejected_403(self):
        login_url = reverse("accounts:login")
        reg_url = reverse("accounts:register")

        for url in (login_url, reg_url):
            get_resp = self.client.get(url)
            self.assertContains(get_resp, "csrfmiddlewaretoken")

        csrf_enforced_client = Client(enforce_csrf_checks=True)
        resp = csrf_enforced_client.post(
            login_url,
            {"email": self.student.email, "password": PASSWORD},
        )
        self.assertEqual(resp.status_code, 403)

    def test_xss_and_sql_injection_payloads_are_neutralized_without_500(self):
        xss_name = '<script>alert("xss")</script>'
        sqli_email = "' OR '1'='1' --"

        resp_login = self.client.post(
            reverse("accounts:login"),
            {"email": sqli_email, "password": PASSWORD},
        )
        self.assertNotEqual(resp_login.status_code, 500)
        self.assertNotIn("_auth_user_id", self.client.session)

        admin_client = Client()
        admin_client.post(reverse("accounts:login"), {"email": self.admin.email, "password": PASSWORD})
        resp_create = admin_client.post(
            reverse("accounts:admin_user_create"),
            {
                "full_name": xss_name,
                "email": "xss.user@test.example",
                "password": PASSWORD,
                self.confirm_field: PASSWORD,
                "role": Role.STUDENT,
            },
        )
        self.assertNotEqual(resp_create.status_code, 500)

        list_resp = admin_client.get(reverse("accounts:admin_user_list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertNotIn(xss_name, list_resp.content.decode("utf-8"))

    @override_settings(DEBUG=False)
    def test_no_password_or_secret_leaked_in_auth_responses(self):
        resp = self.client.post(
            reverse("accounts:login"),
            {"email": self.student.email, "password": "wrong_secret_123"},
        )
        body = resp.content.decode("utf-8")
        self.assertNotIn("wrong_secret_123", body)
        self.assertNotIn(self.student.password, body)
