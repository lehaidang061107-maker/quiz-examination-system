"""S3-12 bổ sung: chọn câu hỏi hàng loạt và đặt cùng điểm cho cả đề.

Chạy riêng: cd src && python manage.py test exams.tests.test_views_bulk
"""
from decimal import Decimal

from django.urls import reverse

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from exams.tests.test_views_publish import ExamQuestionsBase


class AddAllTests(ExamQuestionsBase):
    def test_them_tat_ca_cau_khop_tim_kiem(self):
        make_question(self.teacher, content="Câu hai mươi")
        make_question(self.teacher, content="Câu nháp hai", activate=False)  # nháp: không thêm
        response = self.client.post(self.url + "?q=hai", {"action": "add_all", "q": "hai", "points": "2"}, follow=True)
        self.assertEqual(sorted(self.positions()), ["Câu hai", "Câu hai mươi"])
        self.assertContains(response, "Đã thêm 2 câu hỏi vào đề.")
        self.assertTrue(all(i.points == Decimal("2") for i in self.exam.exam_questions.all()))

    def test_them_tat_ca_khong_tim_kiem_bo_qua_cau_da_co(self):
        self.exam.add_question(self.q1.pk, 1)
        self.client.post(self.url, {"action": "add_all", "q": "", "points": "1"})
        self.assertEqual(self.positions(), ["Câu một", "Câu hai", "Câu ba"])

    def test_khong_them_cau_cua_giang_vien_khac(self):
        make_question(make_user(Role.TEACHER), content="Câu hai của người khác")
        self.client.post(self.url, {"action": "add_all", "q": "hai", "points": "1"})
        self.assertEqual(self.positions(), ["Câu hai"])

    def test_het_cau_de_them(self):
        response = self.client.post(self.url, {"action": "add_all", "q": "không có", "points": "1"}, follow=True)
        self.assertContains(response, "Không còn câu hỏi nào để thêm.")

    def test_diem_sai_thi_khong_them_gi(self):
        response = self.client.post(self.url, {"action": "add_all", "q": "", "points": "0"}, follow=True)
        self.assertEqual(self.positions(), [])
        self.assertContains(response, "alert-danger")

    def test_de_da_phat_hanh_khong_them_duoc(self):
        exam = make_open_exam(self.teacher, [], [self.q1])
        url = reverse("exams:questions", args=[exam.pk])
        self.client.post(url, {"action": "add_all", "q": "", "points": "1"})
        self.assertEqual(exam.exam_questions.count(), 1)


class SetAllPointsTests(ExamQuestionsBase):
    def test_dat_cung_diem_cho_tat_ca(self):
        self.exam.add_question(self.q1.pk, 1)
        self.exam.add_question(self.q2.pk, 3)
        response = self.client.post(self.url, {"action": "set_all_points", "all_points": "2,5"}, follow=True)
        self.assertEqual({i.points for i in self.exam.exam_questions.all()}, {Decimal("2.5")})
        self.assertContains(response, "Đã đặt 2 câu cùng điểm.")

    def test_diem_khong_hop_le(self):
        self.exam.add_question(self.q1.pk, 1)
        response = self.client.post(self.url, {"action": "set_all_points", "all_points": "-1"}, follow=True)
        self.assertEqual(self.exam.exam_questions.get().points, Decimal("1"))
        self.assertContains(response, "alert-danger")


class BulkUiTests(ExamQuestionsBase):
    def test_trang_co_chon_tat_ca_va_nut_them_tat_ca(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'id="pick-all"')
        self.assertContains(response, "Thêm tất cả 3 câu")
