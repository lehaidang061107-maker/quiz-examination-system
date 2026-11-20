"""Xử lý nền cho lượt thi (S3-23): tự nộp lượt hết hạn và chấm lại bài chờ chấm.

Không phụ thuộc sinh viên còn mở trình duyệt. Mỗi lượt được khóa riêng bằng
select_for_update(skip_locked=True): lượt đang bị web hoặc worker khác giữ thì bỏ qua,
vòng sau xử lý tiếp. Việc chốt bài và chấm điểm dùng lại đúng dịch vụ của nộp tay
(sync_and_finalize_if_needed, Submission.grade) nên chạy lại nhiều lần không tạo bản nộp
hay kết quả trùng. Log chỉ ghi mã lượt thi, không ghi đáp án.
"""
import logging
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from exams.models import ExamParticipant, ExamStatus

from .models import Submission, SubmissionStatus
from .services import sync_and_finalize_if_needed

logger = logging.getLogger(__name__)

BATCH_SIZE = 200  # số lượt tối đa mỗi loại trong một vòng; còn dư thì vòng sau làm tiếp


@dataclass
class WorkerStats:
    finalized: int = 0  # lượt đang làm được chốt (hết giờ, đề đóng, bị thu hồi quyền)
    graded: int = 0  # bài chờ chấm được chấm lại thành công (bài tự nộp đã chấm ngay khi chốt)
    skipped: int = 0  # lượt đang bị tiến trình khác giữ hoặc đã được xử lý trước
    failed: int = 0  # lỗi khi chốt hoặc chấm; giữ nguyên trạng thái để vòng sau thử lại

    @property
    def total(self):
        return self.finalized + self.graded + self.skipped + self.failed

    def __str__(self):
        return (f"chốt {self.finalized}, chấm lại {self.graded}, "
                f"bỏ qua {self.skipped}, lỗi {self.failed}")


def overdue_submission_ids(now, limit=BATCH_SIZE):
    """Lượt IN_PROGRESS phải chốt: quá hạn nộp, đề đã đóng, hoặc sinh viên bị thu hồi quyền."""
    active_access = ExamParticipant.objects.filter(
        exam_id=OuterRef("exam_id"), student_id=OuterRef("student_id"), is_active=True
    )
    return list(
        Submission.objects.filter(status=SubmissionStatus.IN_PROGRESS)
        .filter(Q(deadline_at__lte=now) | Q(exam__status=ExamStatus.CLOSED) | ~Exists(active_access))
        .order_by("deadline_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )


def ungraded_submission_ids(limit=BATCH_SIZE):
    """Bài đã nộp nhưng chưa có kết quả (lần chấm ngay sau khi nộp bị lỗi)."""
    return list(
        Submission.objects.filter(status=SubmissionStatus.SUBMITTED)
        .order_by("submitted_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )


def _lock(pk, status):
    """Khóa lượt nếu còn đúng trạng thái và chưa ai giữ; trả về None nếu phải bỏ qua."""
    return (
        Submission.objects.select_for_update(skip_locked=True)
        .filter(pk=pk, status=status)
        .first()
    )


def finalize_overdue(stats, now=None):
    now = now or timezone.now()
    for pk in overdue_submission_ids(now):
        try:
            with transaction.atomic():
                submission = _lock(pk, SubmissionStatus.IN_PROGRESS)
                if submission is None:
                    stats.skipped += 1
                    continue
                result = sync_and_finalize_if_needed(submission, now=now)
            if result is not None and result.finalized:
                stats.finalized += 1
            else:
                stats.skipped += 1
        except Exception:
            logger.exception("Worker: chốt lượt thi %s thất bại, sẽ thử lại vòng sau", pk)
            stats.failed += 1


def retry_grading(stats):
    for pk in ungraded_submission_ids():
        try:
            with transaction.atomic():
                submission = _lock(pk, SubmissionStatus.SUBMITTED)
                if submission is None:
                    stats.skipped += 1
                    continue
                submission.grade()
            stats.graded += 1
        except Exception:
            logger.exception("Worker: chấm lại bài %s thất bại, giữ SUBMITTED để thử lại", pk)
            stats.failed += 1


def process_once(now=None):
    """Một vòng xử lý: chốt lượt quá hạn trước, rồi chấm các bài còn chờ chấm."""
    stats = WorkerStats()
    finalize_overdue(stats, now=now)
    retry_grading(stats)
    return stats
