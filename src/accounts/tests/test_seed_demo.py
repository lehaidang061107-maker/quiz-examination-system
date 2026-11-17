"""Test lệnh seed_demo (S3-30): đủ dữ liệu demo, chạy lại không trùng.

Chạy riêng: cd src && python manage.py test accounts.tests.test_seed_demo
"""
import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from accounts.management.commands.seed_demo import EXAM_TITLES, seed_demo
from accounts.models import Role, User
from attempts.models import Submission, SubmissionStatus
from exams.models import Exam, ExamParticipant, ExamStatus
from questions.models import AnswerOption, Question, QuestionStatus
from results.models import Result

PASSWORD = "Demo2026abc"


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (User, Question, AnswerOption, Exam, ExamParticipant, Submission, Result)
    }


class SeedDemoTests(TestCase):
    def test_tao_du_du_lieu_theo_yeu_cau(self):
        self.assertTrue(seed_demo(PASSWORD))

        self.assertEqual(User.objects.filter(role=Role.ADMIN).count(), 1)
        self.assertEqual(User.objects.filter(role=Role.TEACHER).count(), 2)
        self.assertEqual(User.objects.filter(role=Role.STUDENT).count(), 3)
        self.assertTrue(User.objects.get(email="teacher@demo.example").check_password(PASSWORD))
        for email in ("teacher@demo.example", "teacher2@demo.example"):
            self.assertTrue(Question.objects.filter(teacher__email=email, status=QuestionStatus.ACTIVE).exists())
        self.assertTrue(Exam.objects.filter(status=ExamStatus.DRAFT, title__in=EXAM_TITLES).exists())
        self.assertTrue(Exam.objects.filter(status=ExamStatus.PUBLISHED, title__in=EXAM_TITLES).exists())
        self.assertTrue(Submission.objects.filter(status=SubmissionStatus.GRADED, results__isnull=False).exists())
        self.assertEqual(
            sorted(Result.objects.values_list("correct_count", flat=True)), [1, 3]
        )

    def test_chay_lai_khong_tao_trung_va_khong_doi_mat_khau(self):
        seed_demo(PASSWORD)
        before = counts()

        self.assertFalse(seed_demo("MatKhauKhac123"))

        self.assertEqual(counts(), before)
        self.assertTrue(User.objects.get(email="admin@demo.example").check_password(PASSWORD))

    def test_bo_sung_phan_con_thieu(self):
        """Database seed bằng bản cũ (thiếu teacher2, student3) chạy lại thì được bổ sung."""
        seed_demo(PASSWORD)
        teacher2 = User.objects.get(email="teacher2@demo.example")
        AnswerOption.objects.filter(question__teacher=teacher2).delete()
        Question.objects.filter(teacher=teacher2).delete()
        teacher2.delete()
        before = counts()

        self.assertTrue(seed_demo(PASSWORD))

        self.assertTrue(User.objects.filter(email="teacher2@demo.example").exists())
        self.assertEqual(Exam.objects.count(), before["Exam"])
        self.assertEqual(User.objects.count(), before["User"] + 1)

    def test_mat_khau_khong_hop_le_thi_dung(self):
        with self.assertRaisesMessage(CommandError, "DEMO_PASSWORD chưa hợp lệ"):
            seed_demo("abc")
        self.assertEqual(User.objects.count(), 0)

    def test_email_demo_bi_dung_sai_vai_tro_thi_khong_ghi_de(self):
        User.objects.create_user("teacher2@demo.example", PASSWORD, full_name="Người khác", role=Role.STUDENT)
        with self.assertRaisesMessage(CommandError, "không ghi đè"):
            seed_demo(PASSWORD)
        self.assertEqual(User.objects.count(), 1)

    def test_lenh_in_thong_bao(self):
        out = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_PASSWORD": PASSWORD}):
            call_command("seed_demo", stdout=out)
            self.assertIn("Đã tạo dữ liệu demo.", out.getvalue())
            call_command("seed_demo", stdout=out)
        self.assertIn("Demo đã tồn tại", out.getvalue())
