"""Trang chủ có bảng bên dưới các ô số như Figma (màn hình 03, 04) và hộp xác nhận chung.

Chạy riêng: cd src && python manage.py test config.tests.test_home
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from exams.models import Exam, ExamStatus
from config.tests.factories import make_open_exam, make_question, make_user


class TeacherHomeTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.client.force_login(self.teacher)

    def test_bang_ky_thi_gan_day_chi_co_de_cua_minh(self):
        make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])
        other = make_user(Role.TEACHER)
        other.create_exam({"title": "Đề của người khác"})
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Kỳ thi gần đây")
        self.assertContains(response, "Đề kiểm tra")
        self.assertNotContains(response, "Đề của người khác")
        self.assertContains(response, "0/1")  # 0 bài nộp / 1 sinh viên được giao

    def test_toi_da_5_de_moi_nhat(self):
        for i in range(7):
            self.teacher.create_exam({"title": f"Đề số {i}"})
        response = self.client.get(reverse("home"))
        self.assertEqual(len(response.context["recent_exams"]), 5)
        self.assertContains(response, "Đề số 6")
        self.assertNotContains(response, "Đề số 0")

    def test_o_so_de_cho_cong_bo_diem(self):
        exam = self.teacher.create_exam({"title": "Đề đã đóng"})
        Exam.objects.filter(pk=exam.pk).update(status=ExamStatus.CLOSED)
        response = self.client.get(reverse("home"))
        self.assertIn(("Đề chờ công bố điểm", 1), response.context["stats"])

    def test_chua_co_de(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Chưa có kỳ thi nào")


class AdminHomeTests(TestCase):
    def test_bang_tai_khoan_moi(self):
        admin = make_user(Role.ADMIN)
        make_user(name="Sinh viên mới nhất")
        self.client.force_login(admin)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Danh sách tài khoản mới")
        self.assertContains(response, "Sinh viên mới nhất")
        self.assertContains(response, reverse("accounts:admin_user_create"))


class StudentHomeTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.client.force_login(self.student)

    def test_bai_thi_can_lam_co_nut_bat_dau_va_hop_xac_nhan(self):
        make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Bài thi cần làm")
        self.assertContains(response, "Bắt đầu làm bài")
        self.assertContains(response, 'data-confirm="Bắt đầu làm bài thi này?')

    def test_bai_dang_lam_hien_nut_tiep_tuc(self):
        exam = make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])
        self.student.start_exam(exam.pk)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Tiếp tục làm bài")

    def test_bai_da_nop_khong_con_trong_bang(self):
        exam = make_open_exam(self.teacher, [self.student], [make_question(self.teacher)])
        submission = self.student.start_exam(exam.pk)
        self.student.submit_exam(submission.pk)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Bạn không còn bài thi nào cần làm.")

    def test_khong_thay_de_khong_duoc_giao(self):
        other = make_user()
        make_open_exam(self.teacher, [other], [make_question(self.teacher)])
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Đề kiểm tra")


class LayoutTests(TestCase):
    def test_nhan_vai_tro_tieng_viet_va_hop_xac_nhan_chung(self):
        self.client.force_login(make_user(Role.TEACHER))
        response = self.client.get(reverse("home"))
        self.assertContains(response, '<div class="qes-role mb-2">Giảng viên</div>', html=True)
        self.assertContains(response, 'id="qes-confirm"')
