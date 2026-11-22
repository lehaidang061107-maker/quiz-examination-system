"""Bổ sung S3-04 (và đăng nhập S3-03): nhật ký đăng nhập và thay đổi tài khoản (NFR-MAI-03, NFR-SEC-10).

Chạy riêng: cd src && python manage.py test accounts.tests.test_audit_log
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import LOGIN_MAX_FAILS, Role, UserStatus
from config.tests.factories import PASSWORD, make_user

NEW_PASSWORD = "MatKhauMoi@2026"


class LoginAuditTests(TestCase):
    def setUp(self):
        self.user = make_user(Role.TEACHER, email="gv.log@test.example")

    def login(self, email, password):
        return self.client.post(reverse("accounts:login"), {"email": email, "password": password})

    def test_dang_nhap_dung_ghi_nhat_ky_khong_ghi_mat_khau(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.login("gv.log@test.example", PASSWORD)
        line = logs.output[0]
        self.assertIn("đăng nhập |", line)
        self.assertIn(f"user_id={self.user.pk}", line)
        self.assertIn("ip=127.0.0.1", line)
        self.assertNotIn(PASSWORD, line)

    def test_sai_mat_khau_ghi_lan_sai_va_khoa_tam(self):
        with self.assertLogs("accounts.audit", level="WARNING") as logs:
            for _ in range(LOGIN_MAX_FAILS):
                self.login("gv.log@test.example", "SaiMatKhau1!")
        self.assertIn("sai mật khẩu lần 1", logs.output[0])
        self.assertIn("khóa tạm 15 phút", logs.output[-1])
        self.assertTrue(all("SaiMatKhau1!" not in line for line in logs.output))

    def test_email_khong_ton_tai_va_khong_gia_duoc_dong_log(self):
        with self.assertLogs("accounts.audit", level="WARNING") as logs:
            self.login("ai.do@test.example\n[AUDIT] đăng nhập | user_id=1", "x")
        self.assertEqual(len(logs.output), 1)
        self.assertNotIn("\n", logs.output[0])
        self.assertIn("email không tồn tại", logs.output[0])

    def test_tai_khoan_bi_khoa_ghi_ly_do(self):
        type(self.user).objects.filter(pk=self.user.pk).update(status=UserStatus.LOCKED)
        with self.assertLogs("accounts.audit", level="WARNING") as logs:
            self.login("gv.log@test.example", PASSWORD)
        self.assertIn("tài khoản LOCKED", logs.output[0])

    def test_dang_xuat_ghi_nhat_ky(self):
        self.client.force_login(self.user)
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.client.post(reverse("accounts:logout"))
        self.assertIn(f"đăng xuất | user_id={self.user.pk}", logs.output[0])

    def test_dang_ky_ghi_nhat_ky(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.client.post(reverse("accounts:register"), {
                "full_name": "Sinh viên mới", "email": "sv.moi@test.example",
                "password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD,
            })
        self.assertIn("đăng ký tài khoản Student", logs.output[0])
        self.assertNotIn(NEW_PASSWORD, logs.output[0])


class AdminAuditTests(TestCase):
    def setUp(self):
        self.admin = make_user(Role.ADMIN)
        self.target = make_user(Role.STUDENT, email="sv.target@test.example")

    def test_tao_tai_khoan(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            user = self.admin.create_user({"full_name": "GV mới", "email": "gv.moi@test.example",
                                           "password": NEW_PASSWORD, "role": Role.TEACHER})
        self.assertIn(f"tạo tài khoản | admin_id={self.admin.pk} | user_id={user.pk}", logs.output[0])
        self.assertNotIn(NEW_PASSWORD, logs.output[0])

    def test_sua_tai_khoan_ghi_truong_doi(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.admin.update_user(self.target.pk, {"full_name": "Tên mới", "role": Role.TEACHER})
        self.assertIn("đổi full_name, role (STUDENT -> TEACHER)", logs.output[0])

    def test_sua_khong_doi_gi_thi_khong_ghi(self):
        with self.assertNoLogs("accounts.audit", level="INFO"):
            self.admin.update_user(self.target.pk, {"full_name": self.target.full_name})

    def test_khoa_mo_khoa_xoa(self):
        with self.assertLogs("accounts.audit", level="INFO") as logs:
            self.admin.lock_user(self.target.pk)
            self.admin.unlock_user(self.target.pk)
            self.admin.delete_user(self.target.pk)
        self.assertIn("khóa tài khoản |", logs.output[0])
        self.assertIn("tự nộp 0 bài đang làm", logs.output[0])
        self.assertIn("mở khóa tài khoản |", logs.output[1])
        self.assertIn("xóa tài khoản (ngừng sử dụng)", logs.output[2])

    def test_thao_tac_bi_tu_choi_khong_ghi(self):
        with self.assertNoLogs("accounts.audit", level="INFO"):
            with self.assertRaises(Exception):
                self.admin.unlock_user(self.target.pk)  # đang ACTIVE, không mở khóa được
