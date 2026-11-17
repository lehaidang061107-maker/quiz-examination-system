"""Test lớp Question, AnswerOption (UC Manage Questions, FR-05).

Chạy riêng: cd src && python manage.py test questions
"""
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Role
from config.tests.factories import make_open_exam, make_question, make_user
from questions.models import Question, QuestionStatus


class QuestionTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)

    def test_cau_hop_le_thi_kich_hoat_duoc(self):
        question = make_question(self.teacher, activate=False)
        self.assertTrue(question.validate_options())
        question.activate()
        self.assertEqual(question.status, QuestionStatus.ACTIVE)

    def test_thieu_noi_dung_va_phuong_an_thi_bao_ro_ly_do(self):
        question = Question.objects.create(teacher=self.teacher, content="")
        question.add_option({"content": "Chỉ một phương án"})
        self.assertFalse(question.validate_options())
        self.assertEqual(question.option_errors(), [
            "Câu hỏi chưa có nội dung.",
            "Câu hỏi cần ít nhất 2 phương án.",
            "Chưa chọn đáp án đúng.",
        ])
        with self.assertRaises(ValidationError):
            question.activate()

    def test_nhap_cho_phep_chua_hoan_chinh(self):
        # BR-07: câu DRAFT được lưu khi còn thiếu.
        question = Question.objects.create(teacher=self.teacher, content=None)
        self.assertEqual(question.status, QuestionStatus.DRAFT)

    def test_chon_dap_an_dung_moi_thi_bo_dap_an_cu(self):
        # BR-13: câu một lựa chọn chỉ có 1 đáp án đúng.
        question = make_question(self.teacher, options=("A", "B", "C"), correct=0, activate=False)
        option_b = question.options.get(content="B")
        option_b.set_correct(True)
        self.assertEqual(list(question.options.filter(is_correct=True)), [option_b])

    def test_add_option_danh_so_thu_tu_tiep_theo(self):
        question = make_question(self.teacher, options=("A", "B"), activate=False)
        option = question.add_option({"content": "C", "is_correct": True})
        self.assertEqual(option.display_order, 3)
        self.assertEqual(question.options.filter(is_correct=True).get(), option)

    def test_cau_da_dung_trong_de_phat_hanh_khong_sua_duoc(self):
        # BR-14: sửa trực tiếp sẽ làm sai điểm của đề đã phát hành.
        question = make_question(self.teacher)
        make_open_exam(self.teacher, [], [question])
        self.assertTrue(question.is_locked())
        with self.assertRaisesMessage(ValidationError, "tạo phiên bản mới"):
            question.options.first().update_content("Nội dung khác")

    def test_tao_phien_ban_moi_de_sua(self):
        question = make_question(self.teacher, options=("A", "B"), correct=1)
        make_open_exam(self.teacher, [], [question])
        copy = question.create_revision()
        self.assertNotEqual(copy.pk, question.pk)
        self.assertEqual(copy.status, QuestionStatus.DRAFT)
        self.assertEqual(list(copy.options.values_list("content", "is_correct")), [("A", False), ("B", True)])
        copy.options.first().update_content("A mới")  # bản mới thì sửa được

    def test_luu_tru_cau_hoi(self):
        question = make_question(self.teacher)
        question.archive()
        self.assertEqual(question.status, QuestionStatus.ARCHIVED)
