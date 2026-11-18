from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role
from exams.models import Exam, ExamParticipant, ExamStatus

from .models import Submission, SubmissionStatus


@role_required(Role.STUDENT)
def exam_list(request):
    """S3-16: Danh sách bài thi được giao cho sinh viên và trạng thái từng lượt thi."""
    now = timezone.now()
    participants = (
        ExamParticipant.objects.filter(
            student=request.user,
            is_active=True,
            exam__status__in=[ExamStatus.PUBLISHED, ExamStatus.CLOSED],
        )
        .select_related("exam", "exam__teacher")
        .order_by("-exam__opens_at", "-exam__created_at")
    )

    submissions = {
        sub.exam_id: sub
        for sub in Submission.objects.filter(student=request.user)
    }

    exam_items = []
    for p in participants:
        exam = p.exam
        sub = submissions.get(exam.pk)
        cannot_reason = None

        if sub is None:
            cannot_reason = exam.cannot_start_reason(request.user)

        exam_items.append(
            {
                "exam": exam,
                "submission": sub,
                "cannot_reason": cannot_reason,
                "is_in_progress": sub is not None and sub.status == SubmissionStatus.IN_PROGRESS,
                "is_submitted": sub is not None
                and sub.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED],
                "now": now,
            }
        )

    return render(
        request,
        "attempts/exam_list.html",
        {
            "exam_items": exam_items,
            "now": now,
        },
    )


@role_required(Role.STUDENT)
@require_POST
def start_exam(request, exam_id):
    """S3-16: Bắt đầu một lượt làm bài thi (tạo Submission duy nhất)."""
    exam = get_object_or_404(Exam, pk=exam_id)

    # Nếu sinh viên đang có lượt làm dở thì cho quay lại tiếp tục làm
    existing = Submission.objects.filter(exam=exam, student=request.user).first()
    if existing is not None:
        if existing.status == SubmissionStatus.IN_PROGRESS:
            return redirect("attempts:take_exam", submission_id=existing.pk)
        messages.warning(request, "Bạn đã hoàn thành bài thi này rồi.")
        return redirect("attempts:exam_list")

    try:
        submission = Submission.start(exam=exam, student=request.user)
    except ValidationError as exc:
        msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        messages.error(request, msg)
        return redirect("attempts:exam_list")

    messages.success(request, f"Đã bắt đầu làm bài: {exam.title}.")
    return redirect("attempts:take_exam", submission_id=submission.pk)