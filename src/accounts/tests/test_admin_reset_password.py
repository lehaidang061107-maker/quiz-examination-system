"""S3-36: Admin đặt lại mật khẩu cho tài khoản khác."""
from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User, UserStatus
from config.tests.factories import PASSWORD, make_user

NEW_PASSWORD = "matkhaumoi456"


class AdminResetPasswordModelTests(TestCase):
    def setUp(self):
        self.admin = make_user(Role.ADMIN)
        self.student = make_user()

    def test_dat_lai_mat_khau_luu_dang_bam_va_xoa_khoa_tam(self):
        User.objects.filter(pk=self.student.pk).update(
            failed_login_count=5, locked_until=timezone.now() + timedelta(minutes=10))
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.admin.reset_password(self.student.pk, NEW_PASSWORD)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password(NEW_PASSWORD))
        self.assertFalse(self.student.check_password(PASSWORD))
        self.assertNotIn(NEW_PASSWORD, self.student.password)
        self.assertEqual(self.student.failed_login_count, 0)
        self.assertIsNone(self.student.locked_until)
        output = "\n".join(logs.output)
        self.assertIn("đặt lại mật khẩu", output)
        self.assertNotIn(NEW_PASSWORD, output)

    def test_mat_khau_yeu_bi_tu_choi(self):
        for weak in ("abc12", "chiconchu", "12345678"):
            with self.assertRaises(ValidationError) as ctx:
                self.admin.reset_password(self.student.pk, weak)
            self.assertIn("new_password", ctx.exception.message_dict)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password(PASSWORD))

    def test_khong_dat_lai_cho_tai_khoan_ngung_su_dung_hoac_chinh_minh(self):
        self.admin.delete_user(self.student.pk)
        with self.assertRaisesMessage(ValidationError, "đã ngừng sử dụng"):
            self.admin.reset_password(self.student.pk, NEW_PASSWORD)
        with self.assertRaisesMessage(ValidationError, "trang Đổi mật khẩu"):
            self.admin.reset_password(self.admin.pk, NEW_PASSWORD)

    def test_tai_khoan_bi_khoa_van_bi_khoa_sau_khi_dat_lai(self):
        self.admin.lock_user(self.student.pk)
        self.admin.reset_password(self.student.pk, NEW_PASSWORD)
        self.student.refresh_from_db()
        self.assertEqual(self.student.status, UserStatus.LOCKED)  # chỉ Mở khóa mới đổi trạng thái


class AdminResetPasswordViewTests(TestCase):
    def setUp(self):
        self.admin = make_user(Role.ADMIN)
        self.teacher = make_user(Role.TEACHER)
        self.url = reverse("accounts:admin_user_reset_password", args=[self.teacher.pk])

    def test_admin_dat_lai_mat_khau_va_huy_phien_cu(self):
        teacher_client = Client()
        teacher_client.force_login(self.teacher)
        self.assertEqual(Session.objects.count(), 1)

        client = Client()
        client.force_login(self.admin)
        detail = client.get(reverse("accounts:admin_user_detail", args=[self.teacher.pk]))
        self.assertContains(detail, self.url)
        self.assertEqual(client.get(self.url).status_code, 200)
        resp = client.post(self.url, {"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD}, follow=True)
        self.assertRedirects(resp, reverse("accounts:admin_user_detail", args=[self.teacher.pk]))
        self.assertContains(resp, "Đã đặt lại mật khẩu")

        # Phiên cũ của giảng viên bị hủy, phiên của Admin vẫn còn.
        self.assertEqual(teacher_client.get(reverse("home")).status_code, 302)
        self.assertEqual(client.get(reverse("home")).status_code, 200)

        old = Client().post(reverse("accounts:login"), {"email": self.teacher.email, "password": PASSWORD})
        self.assertEqual(old.status_code, 200)  # mật khẩu cũ không đăng nhập được
        new = Client().post(reverse("accounts:login"), {"email": self.teacher.email, "password": NEW_PASSWORD})
        self.assertRedirects(new, reverse("home"))

    def test_xac_nhan_khong_khop_hoac_mat_khau_yeu(self):
        self.client.force_login(self.admin)
        resp = self.client.post(self.url, {"new_password": NEW_PASSWORD, "confirm_password": "khac12345"})
        self.assertContains(resp, "Mật khẩu xác nhận không khớp.")
        resp = self.client.post(self.url, {"new_password": "abc", "confirm_password": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors.get("new_password"))
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password(PASSWORD))

    def test_vai_tro_khac_bi_403(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        resp = self.client.post(self.url, {"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD})
        self.assertEqual(resp.status_code, 403)

    def test_tai_khoan_ngung_su_dung_va_chinh_minh(self):
        self.client.force_login(self.admin)
        self.admin.delete_user(self.teacher.pk)
        resp = self.client.get(self.url, follow=True)
        self.assertContains(resp, "không thể đặt lại mật khẩu")
        detail = self.client.get(reverse("accounts:admin_user_detail", args=[self.teacher.pk]))
        self.assertNotContains(detail, self.url)

        own = self.client.get(reverse("accounts:admin_user_reset_password", args=[self.admin.pk]))
        self.assertRedirects(own, reverse("accounts:change_password"))
