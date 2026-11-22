"""Bổ sung S3-07: xóa, lưu trữ, khôi phục câu hỏi (FR-05, UC Manage Questions bước 2-3, BR-14).

Chạy riêng: cd src && python manage.py test questions.tests.test_delete_archive
"""
from django.test import TestCase
from django.urls import reverse

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from questions.models import AnswerOption, Question, QuestionStatus


class QuestionDeleteArchiveTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.client.force_login(self.teacher)
        self.question = make_question(self.teacher, content="Câu chưa dùng")

    def post(self, name, question, **data):
        return self.client.post(reverse(f"questions:{name}", args=[question.pk]), data, follow=True)

    def test_xoa_cau_chua_dung_xoa_ca_phuong_an(self):
        response = self.post("delete", self.question)
        self.assertContains(response, "Đã xóa câu hỏi.")
        self.assertFalse(Question.objects.filter(pk=self.question.pk).exists())
        self.assertFalse(AnswerOption.objects.filter(question_id=self.question.pk).exists())

    def test_khong_xoa_cau_da_dung_trong_de_phat_hanh(self):
        make_open_exam(self.teacher, [], [self.question])
        response = self.post("delete", self.question)
        self.assertContains(response, "không xóa được")
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_khong_xoa_cau_dang_trong_de_nhap(self):
        exam = self.teacher.create_exam({"title": "Đề nháp A", "duration_minutes": 30})
        exam.add_question(self.question.pk, 1)
        response = self.post("delete", self.question)
        self.assertContains(response, "Đề nháp A")
        self.assertTrue(Question.objects.filter(pk=self.question.pk).exists())

    def test_luu_tru_cau_da_dung_de_cu_giu_nguyen(self):
        exam = make_open_exam(self.teacher, [], [self.question])
        response = self.post("archive", self.question)
        self.assertContains(response, "Đã lưu trữ câu hỏi.")
        self.question.refresh_from_db()
        self.assertEqual(self.question.status, QuestionStatus.ARCHIVED)
        self.assertEqual(list(exam.exam_questions.values_list("question_id", flat=True)), [self.question.pk])

    def test_cau_luu_tru_an_khoi_danh_sach_mac_dinh_va_khong_chon_vao_de_moi(self):
        self.question.archive()
        listing = self.client.get(reverse("questions:list"))
        self.assertNotContains(listing, "Câu chưa dùng")
        archived = self.client.get(reverse("questions:list"), {"status": QuestionStatus.ARCHIVED})
        self.assertContains(archived, "Câu chưa dùng")
        self.assertContains(archived, "Khôi phục")
        exam = self.teacher.create_exam({"title": "Đề mới", "duration_minutes": 30})
        bank = self.client.get(reverse("exams:questions", args=[exam.pk]))
        self.assertNotContains(bank, "Câu chưa dùng")

    def test_khoi_phuc_ve_nhap(self):
        self.question.archive()
        response = self.post("restore", self.question)
        self.assertContains(response, "Đã khôi phục câu hỏi về Nháp.")
        self.question.refresh_from_db()
        self.assertEqual(self.question.status, QuestionStatus.DRAFT)

    def test_luu_tru_hai_lan_va_khoi_phuc_cau_chua_luu_tru_bi_tu_choi(self):
        self.question.archive()
        self.assertContains(self.post("archive", self.question), "đã được lưu trữ trước đó")
        other = make_question(self.teacher)
        self.assertContains(self.post("restore", other), "Chỉ khôi phục được")

    def test_giang_vien_khac_khong_thao_tac_duoc(self):
        other = make_user(Role.TEACHER)
        self.client.force_login(other)
        for name in ("delete", "archive", "restore"):
            response = self.client.post(reverse(f"questions:{name}", args=[self.question.pk]))
            self.assertEqual(response.status_code, 404)
        self.assertTrue(Question.objects.filter(pk=self.question.pk, status=QuestionStatus.ACTIVE).exists())

    def test_chi_nhan_post_va_dung_vai_tro(self):
        response = self.client.get(reverse("questions:delete", args=[self.question.pk]))
        self.assertEqual(response.status_code, 405)
        self.client.force_login(make_user(Role.STUDENT))
        response = self.client.post(reverse("questions:delete", args=[self.question.pk]))
        self.assertEqual(response.status_code, 403)

    def test_quay_lai_dung_bo_loc_va_chan_chuyen_huong_ra_ngoai(self):
        back = reverse("questions:list") + "?status=ACTIVE&page=1"
        response = self.client.post(reverse("questions:archive", args=[self.question.pk]), {"next": back})
        self.assertRedirects(response, back, fetch_redirect_response=False)
        other = make_question(self.teacher)
        response = self.client.post(reverse("questions:delete", args=[other.pk]), {"next": "https://evil.example/"})
        self.assertRedirects(response, reverse("questions:list"), fetch_redirect_response=False)

    def test_danh_sach_hien_nut_dung_theo_trang_thai(self):
        used = make_question(self.teacher, content="Câu đã dùng")
        make_open_exam(self.teacher, [], [used])
        html = self.client.get(reverse("questions:list")).content.decode()
        self.assertIn(reverse("questions:delete", args=[self.question.pk]), html)
        self.assertNotIn(reverse("questions:delete", args=[used.pk]), html)
        self.assertIn(reverse("questions:archive", args=[used.pk]), html)
