"""Test layout chung và phân quyền theo vai trò (S3-28; BR-02, NFR-SEC-02, NFR-SEC-09).

Chạy riêng: cd src && python manage.py test config.tests.test_layout
"""
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role, User, UserStatus
from config.tests.factories import make_question, make_user


@override_settings(ROOT_URLCONF="config.tests.urls_for_tests")
class RoleRequiredTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.exam = self.teacher.create_exam({"title": "Đề nháp"})
        self.url = reverse("test_publish", args=[self.exam.pk])

    def test_chua_dang_nhap_thi_chuyen_toi_trang_dang_nhap(self):
        response = self.client.post(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}", fetch_redirect_response=False)

    def test_sai_vai_tro_mo_thang_duong_dan_thi_bi_chan_403(self):
        for role in (Role.STUDENT, Role.ADMIN):
            with self.subTest(role=role):
                self.client.force_login(make_user(role))
                response = self.client.post(self.url)
                self.assertEqual(response.status_code, 403)
                self.assertContains(response, "Bạn không có quyền truy cập trang này.", status_code=403)

    def test_giang_vien_khac_khong_thao_tac_duoc_de_cua_nguoi_khac(self):
        # Đúng vai trò nhưng không sở hữu đề: Model báo PermissionDenied -> 403.
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.post(self.url).status_code, 403)

    def test_loi_nghiep_vu_hien_thong_bao_tieng_viet(self):
        # Đề rỗng không phát hành được: ValidationError của Model hiện thành thông báo đỏ.
        self.client.force_login(self.teacher)
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Đề cần ít nhất 1 câu hỏi.")
        self.assertContains(response, "alert-danger")

    def test_thao_tac_thanh_cong_hien_thong_bao_xanh(self):
        self.exam.add_question(make_question(self.teacher).pk, 2)
        self.client.force_login(self.teacher)
        response = self.client.post(self.url, follow=True)
        self.assertContains(response, "Đã phát hành đề thi.")
        self.assertContains(response, "alert-success")


class HomeTests(TestCase):
    """Trang chủ theo vai trò và menu bên trái (màn hình 03, 04 Figma)."""

    def test_chua_dang_nhap_thi_chuyen_toi_trang_dang_nhap(self):
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, "/accounts/login/?next=/", fetch_redirect_response=False)

    def test_moi_vai_tro_thay_menu_cua_minh(self):
        menus = {
            Role.ADMIN: ("Quản lý tài khoản", "Ngân hàng câu hỏi"),
            Role.TEACHER: ("Ngân hàng câu hỏi", "Quản lý tài khoản"),
            Role.STUDENT: ("Danh sách bài thi", "Ngân hàng câu hỏi"),
        }
        for role, (visible, hidden) in menus.items():
            with self.subTest(role=role):
                user = make_user(role, name=f"Người dùng {role}")
                self.client.force_login(user)
                response = self.client.get(reverse("home"))
                self.assertContains(response, f"Chào mừng, Người dùng {role}")
                self.assertContains(response, visible)
                self.assertNotContains(response, hidden)

    def test_menu_chua_lam_hien_sap_co(self):
        self.client.force_login(make_user(Role.TEACHER))
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'aria-disabled="true"', count=3)  # 3 mục Teacher chưa có trang
        self.assertContains(response, "Sắp có", count=3)
        self.assertContains(response, 'class="nav-link active"', count=1)  # Trang chủ đang chọn

    def test_so_lieu_trang_chu_giang_vien(self):
        teacher = make_user(Role.TEACHER)
        make_question(teacher)
        make_question(teacher)
        self.client.force_login(teacher)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["stats"][0], ("Ngân hàng câu hỏi", 2))

    def test_tai_khoan_bi_khoa_mat_phien_ngay(self):
        # BR-22: Admin khóa tài khoản thì phiên đang mở của người đó không dùng được nữa.
        student = make_user()
        self.client.force_login(student)
        User.objects.filter(pk=student.pk).update(status=UserStatus.LOCKED)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)


@override_settings(DEBUG=False)
class ErrorPageTests(TestCase):
    def test_trang_404_tieng_viet(self):
        self.client.force_login(make_user())
        response = self.client.get("/khong-co-trang-nay/")
        self.assertContains(response, "Không tìm thấy trang", status_code=404)
        self.assertContains(response, "Về Trang chủ", status_code=404)


class DevLoginTests(TestCase):
    """Lệnh dev_login dùng để chạy thử giao diện khi chưa có trang Đăng nhập."""

    def run_command(self, *args):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("dev_login", *args, stdout=out)
        return out.getvalue()

    @override_settings(DEBUG=True)
    def test_tao_phien_dung_tai_khoan(self):
        teacher = make_user(Role.TEACHER, name="Cô Lan")
        output = self.run_command(teacher.email)
        session_id = output.split("sessionid = ")[1].split()[0]
        self.client.cookies["sessionid"] = session_id
        self.assertContains(self.client.get(reverse("home")), "Chào mừng, Cô Lan")

    @override_settings(DEBUG=False)
    def test_khong_chay_khi_tat_debug(self):
        from django.core.management.base import CommandError

        with self.assertRaisesMessage(CommandError, "DEBUG=True"):
            self.run_command(make_user().email)

    @override_settings(DEBUG=True)
    def test_tai_khoan_bi_khoa_khong_dang_nhap_tam_duoc(self):
        from django.core.management.base import CommandError

        student = make_user()
        User.objects.filter(pk=student.pk).update(status=UserStatus.LOCKED)
        with self.assertRaisesMessage(CommandError, "bị khóa"):
            self.run_command(student.email)
