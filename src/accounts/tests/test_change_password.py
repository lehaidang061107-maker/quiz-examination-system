"""S3-35: đổi mật khẩu cho mọi vai trò (NFR-SEC-03, NFR-SEC-08, NFR-MAI-03).

Chạy riêng: cd src && python manage.py test accounts.tests.test_change_password
"""
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import Role, User
from config.tests.factories import PASSWORD, make_user

NEW = "MatKhauMoi2026"


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = make_user(Role.TEACHER)
        self.url = reverse("accounts:change_password")
        self.client.force_login(self.user)

    def post(self, current=PASSWORD, new=NEW, confirm=None):
        return self.client.post(self.url, {
            "current_password": current, "new_password": new, "confirm_password": confirm or new,
        }, follow=True)

    def test_doi_dung_thi_dang_nhap_bang_mat_khau_moi(self):
        response = self.post()
        self.assertRedirects(response, reverse("home"))
        self.assertContains(response, "Đã đổi mật khẩu.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW))
        self.assertFalse(self.user.check_password(PASSWORD))
        self.assertNotIn(NEW, self.user.password)  # lưu dạng băm
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)  # phiên hiện tại vẫn dùng được

    def test_huy_phien_o_trinh_duyet_khac(self):
        other = Client()
        other.force_login(self.user)
        self.assertEqual(other.get(reverse("home")).status_code, 200)
        response = self.post()
        self.assertContains(response, "Đã đăng xuất 1 phiên ở thiết bị khác.")
        self.assertEqual(other.get(reverse("home")).status_code, 302)  # phải đăng nhập lại
        self.assertEqual(Session.objects.count(), 1)

    def test_sai_mat_khau_hien_tai(self):
        response = self.post(current="SaiMatKhau1")
        self.assertContains(response, "Mật khẩu hiện tại không đúng.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_mat_khau_moi_khong_hop_le(self):
        cases = {"abc12": "ít nhất 8", "chiconchu": "cả chữ và số", PASSWORD: "phải khác mật khẩu hiện tại"}
        for new, message in cases.items():
            with self.subTest(new=new):
                response = self.post(new=new)
                self.assertContains(response, message)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_xac_nhan_khong_khop(self):
        response = self.post(confirm="KhacHan2026")
        self.assertContains(response, "Mật khẩu xác nhận không khớp.")

    def test_ghi_nhat_ky_khong_ghi_mat_khau(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.post()
        text = "\n".join(logs.output)
        self.assertIn("đổi mật khẩu", text)
        self.assertNotIn(NEW, text)
        self.assertNotIn(PASSWORD, text)

    def test_moi_vai_tro_deu_doi_duoc_va_co_link(self):
        for role in (Role.ADMIN, Role.STUDENT):
            with self.subTest(role=role):
                user = make_user(role)
                self.client.force_login(user)
                self.assertContains(self.client.get(reverse("home")), self.url)
                self.post()
                user.refresh_from_db()
                self.assertTrue(user.check_password(NEW))

    def test_chua_dang_nhap_chuyen_toi_dang_nhap(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)
