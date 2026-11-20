from dataclasses import dataclass

from django.utils import timezone

from exams.models import ExamParticipant, ExamStatus

from .models import Submission, SubmissionStatus


@dataclass
class FinalizeResult:
    finalized: bool
    reason: str  # "submitted" | "already_submitted" | "expired" | "exam_closed" | "revoked"


def sync_and_finalize_if_needed(submission: Submission, now=None) -> FinalizeResult | None:
    """
    S3-19: Kiểm tra các điều kiện bắt buộc phải chốt bài ngay lập tức:
    1. Lượt thi đã nộp trước đó.
    2. Quá hạn thời gian làm bài (deadline_at).
    3. Đề thi đã bị giảng viên đóng (ExamStatus.CLOSED).
    4. Sinh viên bị thu hồi quyền dự thi (ExamParticipant.is_active=False).
    Trả về FinalizeResult nếu bài đã chốt; trả về None nếu vẫn hợp lệ để làm tiếp.
    """
    now = now or timezone.now()

    if submission.status != SubmissionStatus.IN_PROGRESS:
        return FinalizeResult(finalized=False, reason="already_submitted")

    if submission.deadline_at is not None and now >= submission.deadline_at:
        submission.auto_submit(at=submission.deadline_at)
        return FinalizeResult(finalized=True, reason="expired")

    if submission.exam.status == ExamStatus.CLOSED:
        submission.auto_submit(at=now)
        return FinalizeResult(finalized=True, reason="exam_closed")

    has_active_access = ExamParticipant.objects.filter(
        exam=submission.exam,
        student=submission.student,
        is_active=True,
    ).exists()
    if not has_active_access:
        submission.auto_submit(at=now)
        return FinalizeResult(finalized=True, reason="revoked")

    return None


def finalize_manual_submit(submission: Submission) -> FinalizeResult:
    """S3-19: Dịch vụ nộp bài thống nhất khi sinh viên chủ động bấm Nộp bài."""
    forced = sync_and_finalize_if_needed(submission)
    if forced is not None:
        return forced

    created = submission.submit()
    return FinalizeResult(
        finalized=created,
        reason="submitted" if created else "already_submitted",
    )