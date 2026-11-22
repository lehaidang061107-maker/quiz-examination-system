"""S3-33: nhân bản đề và xem trước đề.

Chạy riêng: cd src && python manage.py test exams.tests.test_views_duplicate
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from attempts.models import Submission
from config.tests.factories import make_open_exam, make_question, make_user
from exams.models import Exam, ExamStatus
from questions.models import Question, QuestionStatus


class DuplicateTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.q1 = make_question(self.teacher, content="Câu một")
        self.q2 = make_question(self.teacher, content="Câu hai")
        self.exam = make_open_exam(self.teacher, [self.student], [self.q1, self.q2], points=3)
        self.client.force_login(self.teacher)
        self.url = reverse("exams:duplicate", args=[self.exam.pk])

    def test_nhan_ban_de_da_phat_hanh_thanh_de_nhap(self):
        response = self.client.post(self.url)
        copy = Exam.objects.exclude(pk=self.exam.pk).get()
        self.assertRedirects(response, reverse("exams:detail", args=[copy.pk]))
        self.assertEqual(copy.status, ExamStatus.DRAFT)
        self.assertEqual(copy.title, "Đề kiểm tra (bản sao)")
        self.assertEqual(copy.duration_minutes, self.exam.duration_minutes)
        self.assertIsNone(copy.opens_at)
        self.assertIsNone(copy.closes_at)
        self.assertFalse(copy.results_published)
        self.assertEqual(copy.participants.count(), 0)
        self.assertEqual(list(copy.exam_questions.order_by("position").values_list("question__content", "points")),
                         [("Câu một", Decimal("3")), ("Câu hai", Decimal("3"))])

    def test_de_goc_khong_doi(self):
        self.client.post(self.url)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.PUBLISHED)
        self.assertEqual(self.exam.exam_questions.count(), 2)
        self.assertEqual(self.exam.participants.count(), 1)

    def test_bo_qua_cau_da_luu_tru(self):
        Question.objects.filter(pk=self.q1.pk).update(status=QuestionStatus.ARCHIVED)
        response = self.client.post(self.url, follow=True)
        copy = Exam.objects.exclude(pk=self.exam.pk).get()
        self.assertEqual(list(copy.exam_questions.values_list("question__content", "position")), [("Câu hai", 1)])
        self.assertContains(response, "Bỏ qua 1 câu đã lưu trữ.")

    def test_ten_dai_van_vua_200_ky_tu(self):
        Exam.objects.filter(pk=self.exam.pk).update(title="x" * 200)
        self.client.post(self.url)
        copy = Exam.objects.exclude(pk=self.exam.pk).get()
        self.assertEqual(len(copy.title), 200)
        self.assertTrue(copy.title.endswith("(bản sao)"))

    def test_giang_vien_khac_va_get_bi_chan(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.client.force_login(make_user(Role.TEACHER))
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(Exam.objects.count(), 1)


class PreviewTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.question = make_question(self.teacher, content="1 + 1 = ?", options=("2", "3"))
        self.exam = self.teacher.create_exam({"title": "Đề nháp", "duration_minutes": 15})
        self.exam.add_question(self.question.pk, 2)
        self.client.force_login(self.teacher)
        self.url = reverse("exams:preview", args=[self.exam.pk])

    def test_xem_truoc_hien_cau_hoi_khong_lo_dap_an(self):
        response = self.client.get(self.url)
        self.assertContains(response, "1 + 1 = ?")
        self.assertContains(response, "Câu 1 / 1")
        self.assertNotContains(response, "is_correct")
        self.assertNotContains(response, "correct")
        self.assertEqual(Submission.objects.count(), 0)

    def test_chi_giang_vien_so_huu_xem_duoc(self):
        for user in (make_user(Role.TEACHER), make_user(Role.STUDENT)):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_nut_tren_trang_chi_tiet(self):
        response = self.client.get(reverse("exams:detail", args=[self.exam.pk]))
        self.assertContains(response, self.url)
        self.assertContains(response, reverse("exams:duplicate", args=[self.exam.pk]))
