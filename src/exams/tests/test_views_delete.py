"""Bổ sung S3-11/S3-12: xóa đề nháp (UC Manage Exams) và xác nhận khi bỏ câu khỏi đề (NFR-USA-04).

Chạy riêng: cd src && python manage.py test exams.tests.test_views_delete
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from exams.models import Exam, ExamParticipant, ExamQuestion
from questions.models import Question


class DeleteDraftExamTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.question = make_question(self.teacher)
        self.exam = self.teacher.create_exam({"title": "Đề tạo nhầm", "duration_minutes": 30})
        self.exam.add_question(self.question.pk, 1)
        self.teacher.assign_students(self.exam.pk, [self.student.pk])
        self.client.force_login(self.teacher)
        self.url = reverse("exams:delete", args=[self.exam.pk])

    def test_xoa_de_nhap_xoa_ca_cau_chon_va_phan_cong_nhung_giu_cau_hoi(self):
        with self.assertLogs("exams.audit", level="INFO") as logs:
            response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse("exams:list"))
        self.assertContains(response, "Đã xóa đề nháp &#x27;Đề tạo nhầm&#x27;.")
        self.assertFalse(Exam.objects.filter(pk=self.exam.pk).exists())
        self.assertFalse(ExamQuestion.objects.filter(exam_id=self.exam.pk).exists())
        self.assertFalse(ExamParticipant.objects.filter(exam_id=self.exam.pk).exists())
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())
        self.assertIn(f"xóa đề nháp | user_id={self.teacher.pk}", logs.output[0])
        self.assertIn(f"exam_id={self.exam.pk}", logs.output[0])

    def test_khong_xoa_de_da_phat_hanh(self):
        published = make_open_exam(self.teacher, [self.student], [self.question])
        response = self.client.post(reverse("exams:delete", args=[published.pk]), follow=True)
        self.assertContains(response, "Chỉ xóa được đề nháp.")
        self.assertTrue(Exam.objects.filter(pk=published.pk).exists())

    def test_giang_vien_khac_va_sinh_vien_khong_xoa_duoc(self):
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Exam.objects.filter(pk=self.exam.pk).exists())

    def test_chi_nhan_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_nut_xoa_chi_hien_o_de_nhap_va_co_xac_nhan(self):
        draft = self.client.get(reverse("exams:detail", args=[self.exam.pk]))
        self.assertContains(draft, self.url)
        self.assertContains(draft, "Xóa đề nháp này?")
        published = make_open_exam(self.teacher, [], [self.question])
        page = self.client.get(reverse("exams:detail", args=[published.pk]))
        self.assertNotContains(page, reverse("exams:delete", args=[published.pk]))


class RemoveQuestionConfirmTests(TestCase):
    def test_nut_bo_cau_co_hoi_xac_nhan(self):
        teacher = make_user(Role.TEACHER)
        exam = teacher.create_exam({"title": "Đề nháp", "duration_minutes": 30})
        exam.add_question(make_question(teacher).pk, 1)
        self.client.force_login(teacher)
        response = self.client.get(reverse("exams:questions", args=[exam.pk]))
        self.assertContains(response, "Bỏ câu 1 khỏi đề? Các câu phía sau sẽ dồn lên.")
