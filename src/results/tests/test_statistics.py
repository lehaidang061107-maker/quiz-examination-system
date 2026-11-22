"""S3-34: thống kê kết quả theo đề và tải bảng điểm CSV.

Chạy riêng: cd src && python manage.py test results.tests.test_statistics
"""
import csv
from decimal import Decimal
from io import StringIO

from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from config.tests.factories import correct_option, make_open_exam, make_question, make_user, wrong_option
from results.statistics import exam_statistics


class StatisticsBase(TestCase):
    """Đề 3 câu x 2 điểm. A đúng 3 (10đ), B đúng 1 sai 1 bỏ 1 (3,33đ), C chưa làm."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.a = make_user(name="An")
        self.b = make_user(name="Bình")
        self.c = make_user(name="Chi")
        self.questions = [make_question(self.teacher, content=f"Câu {i}") for i in range(3)]
        self.exam = make_open_exam(self.teacher, [self.a, self.b, self.c], self.questions)
        self.submit(self.a, right=[0, 1, 2])
        self.submit(self.b, right=[0], wrong=[1])

    def submit(self, student, right=(), wrong=()):
        submission = student.start_exam(self.exam.pk)
        version = submission.version
        for i in right:
            version = submission.save_answer(self.questions[i].pk, correct_option(self.questions[i]).pk, version)
        for i in wrong:
            version = submission.save_answer(self.questions[i].pk, wrong_option(self.questions[i]).pk, version)
        submission.submit()


class ExamStatisticsTests(StatisticsBase):
    def test_so_lieu_tong_quan(self):
        stats = exam_statistics(self.exam)
        self.assertEqual(stats["graded_count"], 2)
        self.assertEqual(stats["participant_count"], 3)
        self.assertEqual(stats["highest"], Decimal("10.00"))
        self.assertEqual(stats["lowest"], Decimal("3.33"))
        self.assertEqual(stats["average"], Decimal("6.67"))  # (10 + 3,33) / 2 = 6,665 -> 6,67
        self.assertEqual((stats["pass_count"], stats["pass_percent"]), (1, 50))

    def test_phan_bo_diem(self):
        bins = {b["label"]: b["count"] for b in exam_statistics(self.exam)["distribution"]}
        self.assertEqual(bins, {"0–2": 0, "2–4": 1, "4–6": 0, "6–8": 0, "8–10": 1})  # 10 điểm nằm ở khoảng cuối

    def test_ty_le_dung_tung_cau(self):
        questions = exam_statistics(self.exam)["questions"]
        self.assertEqual([(q["correct"], q["wrong"], q["blank"]) for q in questions], [(2, 0, 0), (1, 1, 0), (1, 0, 1)])
        self.assertEqual([q["correct_percent"] for q in questions], [100, 50, 50])

    def test_de_chua_co_bai_cham(self):
        exam = make_open_exam(self.teacher, [self.a], [self.questions[0]])
        self.assertEqual(exam_statistics(exam)["graded_count"], 0)


class StatisticsViewTests(StatisticsBase):
    def test_trang_ket_qua_hien_thong_ke(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam", args=[self.exam.pk]))
        self.assertContains(response, "Điểm trung bình")
        self.assertContains(response, "6,67")
        self.assertContains(response, "Tỷ lệ đúng từng câu")
        self.assertContains(response, reverse("results:teacher_exam_csv", args=[self.exam.pk]))

    def test_tai_csv_bang_diem(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("results:teacher_exam_csv", args=[self.exam.pk]))
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
        text = response.content.decode("utf-8")
        self.assertTrue(text.startswith("﻿"))  # BOM để Excel đọc đúng tiếng Việt
        rows = list(csv.reader(StringIO(text.lstrip("﻿"))))
        self.assertEqual(rows[0][:3], ["Họ và tên", "Email", "Trạng thái"])
        by_name = {r[0]: r for r in rows[1:]}
        self.assertEqual(by_name["An"][2:7], ["Đã chấm", "6.00", "6.00", "10.00", "3"])
        self.assertEqual(by_name["Bình"][5:9], ["3.33", "1", "1", "1"])
        self.assertEqual(by_name["Chi"][2], "Chưa làm bài")

    def test_chi_giang_vien_so_huu(self):
        for user in (make_user(Role.TEACHER), self.a):
            with self.subTest(role=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(reverse("results:teacher_exam_csv", args=[self.exam.pk])).status_code, 403)
