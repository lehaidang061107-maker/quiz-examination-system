"""Bổ sung S3-19: nhật ký nộp bài (NFR-MAI-03, NFR-SEC-10), phân trang danh sách bài thi (NFR-PER-05),
trang làm bài có cơ chế lưu tin cậy (NFR-REL-02).

Phần chạy trên trình duyệt (gom 1 giây, gửi lại 10 giây, cảnh báo mất mạng) kiểm tra tay theo S3-19.csv;
ở đây chỉ kiểm tra trang có đủ các thành phần đó.

Chạy riêng: cd src && python manage.py test attempts.tests.test_reliability
"""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission
from attempts.tests.test_models import AttemptTestCase
from attempts.worker import process_once
from config.tests.factories import make_open_exam, make_question, make_user
from exams.models import ExamParticipant


class SubmitAuditLogTests(AttemptTestCase):
    def test_nop_tay_ghi_nhat_ky_khong_ghi_dap_an(self):
        self.client.force_login(self.student)
        with self.assertLogs("attempts.audit", level="INFO") as logs:
            self.client.post(reverse("attempts:submit_exam", args=[self.submission.pk]))
        self.assertEqual(len(logs.output), 1)
        line = logs.output[0]
        self.assertIn("nộp bài", line)
        self.assertIn(f"submission_id={self.submission.pk}", line)
        self.assertIn(f"student_id={self.student.pk}", line)
        self.assertIn(f"exam_id={self.exam.pk}", line)
        self.assertIn("nộp tay", line)
        self.assertNotIn("option", line)

    def test_nop_lai_khong_ghi_them(self):
        self.submission.submit()
        with self.assertNoLogs("attempts.audit", level="INFO"):
            self.submission.submit()

    def test_tu_nop_ghi_ly_do_het_gio(self):
        past = timezone.now() - timedelta(minutes=40)
        Submission.objects.filter(pk=self.submission.pk).update(started_at=past, deadline_at=past + timedelta(minutes=30))
        with self.assertLogs("attempts.audit", level="INFO") as logs:
            process_once()
        self.assertIn("tự nộp (hết giờ)", logs.output[0])

    def test_tu_nop_ghi_ly_do_thu_hoi_quyen(self):
        participant = ExamParticipant.objects.get(exam=self.exam, student=self.student)
        with self.assertLogs("attempts.audit", level="INFO") as logs:
            participant.revoke_access()
        self.assertIn("tự nộp (bị thu hồi quyền)", logs.output[0])

    def test_tu_nop_ghi_ly_do_dong_de(self):
        with self.assertLogs("attempts.audit", level="INFO") as logs:
            self.exam.close()
        self.assertIn("tự nộp (đề đã đóng)", logs.output[0])


class StudentExamListPaginationTests(TestCase):
    def setUp(self):
        self.teacher = make_user(Role.TEACHER)
        self.student = make_user()
        question = make_question(self.teacher)
        for _ in range(23):
            make_open_exam(self.teacher, [self.student], [question])
        self.client.force_login(self.student)
        self.url = reverse("attempts:exam_list")

    def test_moi_trang_20_de(self):
        first = self.client.get(self.url)
        self.assertEqual(len(first.context["exam_items"]), 20)
        self.assertContains(first, "1/2")
        second = self.client.get(self.url, {"page": 2})
        self.assertEqual(len(second.context["exam_items"]), 3)

    def test_trang_sai_ve_trang_cuoi(self):
        response = self.client.get(self.url, {"page": 99})
        self.assertEqual(len(response.context["exam_items"]), 3)


class TakeExamReliableSaveTests(AttemptTestCase):
    def test_trang_lam_bai_co_luu_tin_cay(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("attempts:take_exam", args=[self.submission.pk]))
        self.assertContains(response, 'id="offline-alert"')
        self.assertContains(response, "const DEBOUNCE_MS = 1000;")
        self.assertContains(response, "const RETRY_MS = 10000;")
        self.assertContains(response, '"beforeunload"')
        self.assertContains(response, 'addEventListener("online"')


class TakeExamProgressTests(AttemptTestCase):
    """UC Take Exam bước 4 (tiến độ) và UC Submit Exam bước 2 (xác nhận kèm số câu đã trả lời)."""

    def test_hien_so_cau_da_tra_loi_tu_may_chu(self):
        from config.tests.factories import correct_option

        self.answer(self.questions[0], correct_option(self.questions[0]))
        self.client.force_login(self.student)
        response = self.client.get(reverse("attempts:take_exam", args=[self.submission.pk]))
        self.assertEqual(response.context["answered_count"], 1)
        self.assertContains(response, '<strong id="answered-count">1</strong>/<span id="question-total">3</span> câu',
                            html=False)

    def test_hop_xac_nhan_nop_bai_co_so_cau(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("attempts:take_exam", args=[self.submission.pk]))
        self.assertContains(response, '"Bạn đã trả lời " + answered + "/" + totalQuestions + " câu"')
        # S3-17: hộp xác nhận dùng modal chung và ghi rõ số thứ tự các câu chưa làm.
        self.assertContains(response, '" câu chưa trả lời (câu " + unanswered.join(", ")')
        self.assertContains(response, "window.qesConfirm(summary")
