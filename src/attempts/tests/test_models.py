"""Test lớp Submission, SubmissionAnswer, Result: làm bài, nộp bài, chấm điểm, xem kết quả.

(UC Take Exam, Submit Exam, Automatic Grading, View Exam Results; FR-09 -> FR-13)
Chạy riêng: cd src && python manage.py test attempts
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from accounts.models import Role
from attempts.models import StaleVersionError, Submission, SubmissionStatus
from config.tests.factories import correct_option, make_open_exam, make_question, make_user, wrong_option
from results.models import Result


class AttemptTestCase(TestCase):
    """Dữ liệu chung: đề 3 câu, câu 1 được 2 điểm, câu 2 được 3 điểm, câu 3 được 5 điểm."""

    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        self.questions = [make_question(self.teacher, content=f"Câu {i}") for i in range(1, 4)]
        self.exam = make_open_exam(self.teacher, [self.student], self.questions)
        for item, points in zip(self.exam.exam_questions.order_by("position"), (2, 3, 5)):
            item.points = Decimal(points)
            item.save()
        self.submission = self.student.start_exam(self.exam.pk)

    def answer(self, question, option):
        """Sinh viên chọn đáp án như trên giao diện (gửi kèm version hiện tại)."""
        self.submission.refresh_from_db()
        return self.student.save_answer({
            "submission_id": self.submission.pk, "question_id": question.pk,
            "option_id": option.pk if option else None, "version": self.submission.version,
        })

    def expire(self):
        """Giả lập hết giờ: lùi giờ bắt đầu và hạn nộp về quá khứ."""
        past = timezone.now() - timedelta(minutes=40)
        Submission.objects.filter(pk=self.submission.pk).update(
            started_at=past, deadline_at=past + timedelta(minutes=30)
        )
        self.submission.refresh_from_db()


class SaveAnswerTests(AttemptTestCase):
    def test_luu_dap_an_tang_version(self):
        version = self.answer(self.questions[0], correct_option(self.questions[0]))
        self.assertEqual(version, 1)
        self.assertEqual(self.submission.answers.get().selected_option, correct_option(self.questions[0]))

    def test_doi_dap_an_thi_ghi_de_khong_tao_dong_moi(self):
        self.answer(self.questions[0], wrong_option(self.questions[0]))
        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.assertEqual(self.submission.answers.count(), 1)

    def test_bo_chon_dap_an(self):
        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.answer(self.questions[0], None)
        self.assertIsNone(self.submission.answers.get().selected_option)

    def test_tab_cu_gui_version_cu_bi_tu_choi(self):
        # BR-20: hai tab cùng mở, tab 1 lưu trước; tab 2 còn version cũ thì phải tải lại.
        old_version = self.submission.version
        self.answer(self.questions[0], correct_option(self.questions[0]))
        with self.assertRaises(StaleVersionError):
            self.submission.save_answer(self.questions[1].pk, correct_option(self.questions[1]).pk, old_version)

    def test_phuong_an_cua_cau_khac_bi_tu_choi(self):
        with self.assertRaisesMessage(ValidationError, "không thuộc câu hỏi"):
            self.answer(self.questions[0], correct_option(self.questions[1]))

    def test_het_gio_khong_luu_duoc(self):
        self.expire()
        with self.assertRaisesMessage(ValidationError, "hết giờ"):
            self.answer(self.questions[0], correct_option(self.questions[0]))


class SubmitAndGradeTests(AttemptTestCase):
    def test_nop_bai_thi_cham_dung_diem(self):
        # Đúng câu 1 (2 điểm) và câu 3 (5 điểm), sai câu 2 -> 7/10, đúng 2/3 câu.
        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.answer(self.questions[1], wrong_option(self.questions[1]))
        self.answer(self.questions[2], correct_option(self.questions[2]))
        self.assertTrue(self.student.submit_exam(self.submission.pk))

        self.submission.refresh_from_db()
        result = Result.objects.get(submission=self.submission)
        self.assertEqual(self.submission.status, SubmissionStatus.GRADED)
        self.assertEqual((result.score, result.max_score), (Decimal("7.00"), Decimal("10.00")))
        self.assertEqual((result.correct_count, result.total_questions), (2, 3))

    def test_bo_trong_tat_ca_duoc_0_diem(self):
        self.student.submit_exam(self.submission.pk)
        result = Result.objects.get(submission=self.submission)
        self.assertEqual((result.score, result.correct_count), (Decimal("0.00"), 0))

    def test_nop_lai_khong_tao_ban_nop_trung(self):
        # NFR-REL-03: mạng chập chờn, bấm Nộp hai lần.
        self.assertTrue(self.student.submit_exam(self.submission.pk))
        self.assertFalse(self.student.submit_exam(self.submission.pk))
        self.assertEqual(Result.objects.filter(submission=self.submission).count(), 1)

    def test_da_nop_thi_khong_sua_duoc(self):
        # NFR-SEC-06: bài đã nộp bị khóa.
        self.student.submit_exam(self.submission.pk)
        with self.assertRaisesMessage(ValidationError, "đã nộp"):
            self.answer(self.questions[0], correct_option(self.questions[0]))

    def test_het_gio_tu_nop_tinh_theo_han_nop(self):
        # BR-21: tự nộp ghi submitted_at = hạn nộp, không tính thời gian trễ xử lý.
        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.expire()
        self.submission.auto_submit()
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.submitted_at, self.submission.deadline_at)
        self.assertEqual(Result.objects.get(submission=self.submission).correct_count, 1)

    def test_cham_loi_van_giu_bai_da_nop(self):
        # UC Submit Exam: chấm lỗi không làm mất bài; giữ SUBMITTED để chấm lại.
        with mock.patch.object(Result, "calculate", side_effect=RuntimeError("lỗi giả lập")), \
                self.assertLogs("attempts.models", "ERROR"):
            self.student.submit_exam(self.submission.pk)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, SubmissionStatus.SUBMITTED)
        self.submission.grade()  # chấm lại thành công
        self.assertEqual(self.submission.status, SubmissionStatus.GRADED)

    def test_cham_lai_bai_da_cham_tra_ket_qua_cu(self):
        self.student.submit_exam(self.submission.pk)
        first = Result.objects.get(submission=self.submission)
        self.assertEqual(self.submission.grade().pk, first.pk)


class ViewResultTests(AttemptTestCase):
    """BR-10, BR-19: ai được xem kết quả."""

    def setUp(self):
        super().setUp()
        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.student.submit_exam(self.submission.pk)
        self.result = Result.objects.get(submission=self.submission)

    def test_sinh_vien_chua_xem_duoc_khi_chua_cong_bo(self):
        self.assertIsNone(self.student.view_result(self.exam.pk))

    def test_sinh_vien_xem_duoc_sau_khi_cong_bo(self):
        self.exam.close()
        self.exam.publish_results()
        self.assertEqual(self.student.view_result(self.exam.pk), self.result)

    def test_giang_vien_xem_duoc_ca_khi_chua_cong_bo(self):
        self.assertEqual(self.teacher.view_results(self.exam.pk), [self.result])
        self.assertTrue(self.result.can_view(self.teacher))

    def test_nguoi_khac_khong_xem_duoc(self):
        self.exam.close()
        self.exam.publish_results()
        self.assertFalse(self.result.can_view(make_user()))  # sinh viên khác
        self.assertFalse(self.result.can_view(make_user(Role.TEACHER)))  # giảng viên khác
