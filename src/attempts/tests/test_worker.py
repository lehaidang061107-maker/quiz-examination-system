"""Test tiến trình nền tự nộp và chấm lại bài (S3-23, lệnh run_worker).

Chạy riêng: cd src && python manage.py test attempts.tests.test_worker
"""
import signal
import threading
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from accounts.models import Role
from attempts.models import Submission, SubmissionStatus
from attempts.services import sync_and_finalize_if_needed
from attempts.tests.test_models import AttemptTestCase
from attempts.worker import process_once
from config.tests.factories import correct_option, make_open_exam, make_question, make_user
from exams.models import ExamParticipant, ExamStatus
from questions.models import AnswerOption
from results.models import Result


class WorkerTests(AttemptTestCase):
    """Đề mẫu 3 câu 2đ/3đ/5đ của AttemptTestCase; self.submission đang làm."""

    def fail_grading(self):
        return mock.patch.object(Result, "calculate", side_effect=RuntimeError("lỗi giả lập"))

    def status(self, submission=None):
        submission = submission or self.submission
        submission.refresh_from_db()
        return submission.status

    def test_luot_qua_han_duoc_tu_nop_va_cham(self):
        # Sinh viên lưu 1 câu đúng rồi đóng trình duyệt; hết giờ worker tự nộp theo hạn nộp.
        self.answer(self.questions[2], correct_option(self.questions[2]))
        self.expire()
        stats = process_once()
        self.assertEqual((stats.finalized, stats.failed), (1, 0))
        self.assertEqual(self.status(), SubmissionStatus.GRADED)
        self.assertEqual(self.submission.submitted_at, self.submission.deadline_at)
        self.assertEqual(Result.objects.get(submission=self.submission).score, Decimal("5.00"))

    def test_luot_con_gio_khong_dong_vao(self):
        stats = process_once()
        self.assertEqual(stats.total, 0)
        self.assertEqual(self.status(), SubmissionStatus.IN_PROGRESS)

    def test_de_da_dong_thi_chot_bai(self):
        type(self.exam).objects.filter(pk=self.exam.pk).update(status=ExamStatus.CLOSED)
        self.assertEqual(process_once().finalized, 1)
        self.assertEqual(self.status(), SubmissionStatus.GRADED)

    def test_de_het_lich_duoc_tu_dong_va_nop_tai_gio_dong(self):
        # S3-14 (BR-17): đến closes_at hệ thống tự đóng đề, bài đang làm nộp tại giờ đóng.
        now = timezone.now()
        closes_at = now - timedelta(minutes=1)
        Submission.objects.filter(pk=self.submission.pk).update(started_at=now - timedelta(minutes=10))
        type(self.exam).objects.filter(pk=self.exam.pk).update(closes_at=closes_at)
        with self.assertLogs("exams.audit", level="INFO") as logs:
            stats = process_once()
        self.assertEqual((stats.exams_closed, stats.failed), (1, 0))
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.CLOSED)
        self.assertEqual(self.status(), SubmissionStatus.GRADED)
        self.assertEqual(self.submission.submitted_at, closes_at)
        self.assertIn("hệ thống tự đóng đề", logs.output[0])
        # Đã đóng thì giảng viên công bố điểm được ngay, không cần bấm Đóng đề.
        self.exam.publish_results()
        self.assertTrue(self.exam.results_published)

    def test_de_con_lich_hoac_khong_gioi_han_khong_bi_dong(self):
        type(self.exam).objects.filter(pk=self.exam.pk).update(closes_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(process_once().exams_closed, 0)
        type(self.exam).objects.filter(pk=self.exam.pk).update(closes_at=None)
        self.assertEqual(process_once().exams_closed, 0)
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.PUBLISHED)

    def test_bi_thu_hoi_quyen_thi_chot_bai(self):
        ExamParticipant.objects.filter(exam=self.exam, student=self.student).update(is_active=False)
        self.assertEqual(process_once().finalized, 1)
        self.assertEqual(self.status(), SubmissionStatus.GRADED)

    def test_cham_lai_bai_cham_loi(self):
        self.answer(self.questions[0], correct_option(self.questions[0]))
        with self.fail_grading(), self.assertLogs("attempts.models", "ERROR"):
            self.student.submit_exam(self.submission.pk)
        self.assertEqual(self.status(), SubmissionStatus.SUBMITTED)

        stats = process_once()
        self.assertEqual((stats.graded, stats.failed), (1, 0))
        self.assertEqual(self.status(), SubmissionStatus.GRADED)
        self.assertEqual(Result.objects.get(submission=self.submission).score, Decimal("2.00"))

    def test_chay_hai_lan_khong_nop_cham_trung(self):
        self.expire()
        first = process_once()
        second = process_once()
        self.assertEqual(first.finalized, 1)
        self.assertEqual(second.total, 0)
        self.assertEqual(Result.objects.filter(submission=self.submission).count(), 1)

    def test_cham_van_loi_thi_giu_submitted_va_log_khong_co_dap_an(self):
        chosen = correct_option(self.questions[0])
        AnswerOption.objects.filter(pk=chosen.pk).update(content="DAP-AN-BI-MAT-S323")
        self.answer(self.questions[0], chosen)
        with self.fail_grading(), self.assertLogs("attempts.models", "ERROR"):
            self.student.submit_exam(self.submission.pk)

        with self.fail_grading(), self.assertLogs("attempts.worker", "ERROR") as logs:
            stats = process_once()
        self.assertEqual((stats.graded, stats.failed), (0, 1))
        self.assertEqual(self.status(), SubmissionStatus.SUBMITTED)
        output = "\n".join(logs.output)
        self.assertIn(str(self.submission.pk), output)
        self.assertNotIn("DAP-AN-BI-MAT-S323", output)

    def test_mot_bai_loi_khong_chan_bai_khac(self):
        other_student = make_user()
        ExamParticipant.objects.create(exam=self.exam, student=other_student)
        other = other_student.start_exam(self.exam.pk)
        self.expire()
        Submission.objects.filter(pk=other.pk).update(
            started_at=self.submission.started_at, deadline_at=self.submission.deadline_at
        )
        def flaky(submission, now=None):
            if submission.pk == self.submission.pk:
                raise RuntimeError("lỗi giả lập")
            return sync_and_finalize_if_needed(submission, now=now)

        with mock.patch("attempts.worker.sync_and_finalize_if_needed", side_effect=flaky), \
                self.assertLogs("attempts.worker", "ERROR"):
            stats = process_once()
        self.assertEqual((stats.finalized, stats.failed), (1, 1))
        self.assertEqual(self.status(), SubmissionStatus.IN_PROGRESS)
        self.assertEqual(self.status(other), SubmissionStatus.GRADED)
        # Vòng sau (hết lỗi) xử lý nốt lượt còn lại.
        self.assertEqual(process_once().finalized, 1)
        self.assertEqual(self.status(), SubmissionStatus.GRADED)

    def test_lenh_run_worker_once(self):
        self.expire()
        out = StringIO()
        call_command("run_worker", "--once", stdout=out)
        self.assertIn("chốt 1", out.getvalue())
        self.assertEqual(self.status(), SubmissionStatus.GRADED)

    def test_lenh_dung_an_toan_khi_nhan_tin_hieu(self):
        out = StringIO()

        def send_stop(handlers, timeout):
            handlers[signal.SIGINT](signal.SIGINT, None)
            return True

        self.run_worker_with_signal(out, send_stop)

        self.assertIn("Worker đã dừng.", out.getvalue())

    def run_worker_with_signal(self, out, wait_callback):
        original_signal = signal.signal
        handlers = {}

        def capture_signal(sig, handler):
            if handler is not None:
                handlers[sig] = handler
            return original_signal(sig, handler)

        def fake_wait(timeout=None):
            return wait_callback(handlers, timeout)

        with mock.patch(
            "attempts.management.commands.run_worker.signal.signal",
            side_effect=capture_signal,
        ), mock.patch(
            "threading.Event.wait",
            side_effect=fake_wait,
        ):
            call_command("run_worker", "--interval", "0.1", stdout=out)

    def test_loi_database_trong_vong_khong_lam_dung_worker(self):
        out = StringIO()
        calls = []

        def boom():
            calls.append(1)
            raise RuntimeError("mất kết nối giả lập")

        def send_stop_after_retries(handlers, timeout):
            if len(calls) >= 2:
                handlers[signal.SIGINT](signal.SIGINT, None)
                return True
            return False

        with mock.patch(
            "attempts.management.commands.run_worker.process_once",
            side_effect=boom,
        ), self.assertLogs("attempts.worker", "ERROR"):
            self.run_worker_with_signal(out, send_stop_after_retries)

        self.assertGreaterEqual(len(calls), 2)
        self.assertIn("Worker đã dừng.", out.getvalue())


class WorkerLockingTests(TransactionTestCase):
    """Cần PostgreSQL thật để select_for_update(skip_locked=True) có tác dụng."""

    def setUp(self):
        teacher = make_user(Role.TEACHER)
        self.student = make_user()
        exam = make_open_exam(teacher, [self.student], [make_question(teacher)])
        self.submission = self.student.start_exam(exam.pk)
        past = timezone.now() - timedelta(minutes=40)
        Submission.objects.filter(pk=self.submission.pk).update(
            started_at=past, deadline_at=past + timedelta(minutes=30)
        )

    def test_luot_dang_bi_giu_thi_bo_qua_roi_vong_sau_xu_ly(self):
        locked, release = threading.Event(), threading.Event()
        lock_errors = []

        def hold_lock():
            try:
                connection.ensure_connection()
                with transaction.atomic():
                    Submission.objects.select_for_update().get(pk=self.submission.pk)
                    locked.set()
                    release.wait(30)
            except Exception as exc:
                lock_errors.append(exc)
            finally:
                connection.close()

        holder = threading.Thread(target=hold_lock)
        holder.start()
        try:
            acquired = locked.wait(60)
            self.assertTrue(acquired, f"Luồng phụ không lấy được khóa Submission. Lỗi: {lock_errors!r}")
            stats = process_once()  # không bị treo chờ khóa
            self.assertEqual((stats.skipped, stats.finalized), (1, 0))
        finally:
            release.set()
            holder.join()
        self.assertEqual(process_once().finalized, 1)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, SubmissionStatus.GRADED)

    def test_hai_worker_chay_cung_luc_khong_trung(self):
        barrier = threading.Barrier(2)
        results, errors = [], []

        def run():
            try:
                barrier.wait()
                results.append(process_once())
            except Exception as exc:
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(sum(s.finalized for s in results), 1)
        self.assertEqual(Result.objects.filter(submission=self.submission).count(), 1)
