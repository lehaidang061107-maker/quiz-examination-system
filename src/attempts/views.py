import json

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role
from exams.models import Exam, ExamParticipant, ExamQuestion, ExamStatus

from .models import StaleVersionError, Submission, SubmissionAnswer, SubmissionStatus
from .services import finalize_manual_submit, sync_and_finalize_if_needed

FINALIZE_MESSAGES = {
    "expired": "Đã hết thời gian làm bài. Hệ thống đã tự động chốt và nộp bài của bạn.",
    "exam_closed": "Đề thi đã được giảng viên đóng. Hệ thống đã tự động nộp bài của bạn.",
    "revoked": "Quyền dự thi của bạn đã bị thu hồi. Hệ thống đã tự động chốt bài.",
    "already_submitted": "Lượt thi này đã được nộp trước đó.",
    "submitted": "Đã nộp bài thi thành công!",
}


@role_required(Role.STUDENT)
def exam_list(request):
    """S3-16: Danh sách bài thi được giao cho sinh viên và trạng thái từng lượt thi."""
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
        cannot_reason = exam.cannot_start_reason(request.user) if sub is None else None

        exam_items.append(
            {
                "exam": exam,
                "submission": sub,
                "cannot_reason": cannot_reason,
                "is_in_progress": sub is not None and sub.status == SubmissionStatus.IN_PROGRESS,
                "is_submitted": sub is not None
                and sub.status in [SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED],
            }
        )

    return render(
        request,
        "attempts/exam_list.html",
        {
            "exam_items": exam_items,
        },
    )


@role_required(Role.STUDENT)
@require_POST
def start_exam(request, exam_id):
    """S3-16: Bắt đầu một lượt làm bài thi (kiểm tra quyền trước khi tạo Submission)."""
    exam = get_object_or_404(Exam, pk=exam_id)

    existing = Submission.objects.filter(exam=exam, student=request.user).first()
    if existing is not None:
        if existing.status == SubmissionStatus.IN_PROGRESS:
            return redirect("attempts:take_exam", submission_id=existing.pk)
        messages.warning(request, "Bạn đã hoàn thành bài thi này rồi.")
        return redirect("attempts:exam_list")

    try:
        # Model kiểm tra quyền dự thi, lịch thi và tạo lượt (Student.startExam trong sơ đồ lớp).
        submission = request.user.as_role().start_exam(exam.pk)
    except ValidationError as exc:
        msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        messages.error(request, msg)
        return redirect("attempts:exam_list")

    messages.success(request, f"Đã bắt đầu làm bài: {exam.title}.")
    return redirect("attempts:take_exam", submission_id=submission.pk)


@role_required(Role.STUDENT)
def take_exam(request, submission_id):
    """S3-17 & S3-19: Phòng làm bài thi với đồng hồ đếm ngược (nếu có hạn) và kiểm tra chốt bài."""
    submission = get_object_or_404(
        Submission.objects.select_related("exam"),
        pk=submission_id,
        student=request.user,
    )

    forced = sync_and_finalize_if_needed(submission)
    if forced is not None:
        messages.warning(request, FINALIZE_MESSAGES.get(forced.reason, "Lượt thi đã kết thúc."))
        return redirect("attempts:exam_list")

    exam_questions = (
        ExamQuestion.objects.filter(exam=submission.exam)
        .select_related("question")
        .prefetch_related("question__options")
        .order_by("position")
    )

    saved_answers = {
        ans.question_id: ans.selected_option_id
        for ans in SubmissionAnswer.objects.filter(submission=submission)
    }

    question_items = []
    for eq in exam_questions:
        options = sorted(eq.question.options.all(), key=lambda o: o.display_order)
        question_items.append(
            {
                "position": eq.position,
                "points": eq.points,
                "question": eq.question,
                "options": options,
                "selected_option_id": saved_answers.get(eq.question_id),
            }
        )

    has_deadline = submission.deadline_at is not None
    remaining_seconds = (
        max(0, int((submission.deadline_at - timezone.now()).total_seconds()))
        if has_deadline
        else None
    )

    return render(
        request,
        "attempts/take_exam.html",
        {
            "submission": submission,
            "exam": submission.exam,
            "question_items": question_items,
            "has_deadline": has_deadline,
            "remaining_seconds": remaining_seconds,
        },
    )


@role_required(Role.STUDENT)
@require_POST
def save_answer_api(request, submission_id):
    """S3-18 & S3-19: API lưu đáp án tự động, kiểm tra chốt bài & xung đột version."""
    submission = get_object_or_404(
        Submission.objects.select_related("exam"),
        pk=submission_id,
        student=request.user,
    )

    forced = sync_and_finalize_if_needed(submission)
    if forced is not None:
        return JsonResponse(
            {
                "ok": False,
                "finalized": True,
                "reason": forced.reason,
                "error": FINALIZE_MESSAGES.get(forced.reason, "Bài thi đã kết thúc."),
            },
            status=409,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
        if not isinstance(payload, dict):
            return JsonResponse({"ok": False, "error": "Payload JSON phải là object."}, status=400)
        question_id = int(payload.get("question_id"))
        raw_option_id = payload.get("option_id")
        option_id = int(raw_option_id) if raw_option_id is not None else None
        version = int(payload.get("version"))
    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Dữ liệu gửi lên không hợp lệ."}, status=400)

    try:
        new_version = submission.save_answer(
            question_id=question_id,
            option_id=option_id,
            version=version,
        )
    except StaleVersionError as exc:
        msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        return JsonResponse({"ok": False, "stale": True, "error": msg}, status=409)
    except ValidationError as exc:
        msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        return JsonResponse({"ok": False, "error": msg}, status=400)

    return JsonResponse({"ok": True, "version": new_version})


@role_required(Role.STUDENT)
@require_POST
def submit_exam(request, submission_id):
    """S3-19: Nộp bài qua dịch vụ chốt bài thống nhất."""
    submission = get_object_or_404(
        Submission.objects.select_related("exam"),
        pk=submission_id,
        student=request.user,
    )

    result = finalize_manual_submit(submission)
    msg = FINALIZE_MESSAGES.get(result.reason, "Đã xử lý nộp bài.")
    if result.reason == "submitted":
        messages.success(request, f"Đã nộp bài thi '{submission.exam.title}' thành công!")
    elif result.finalized:
        messages.warning(request, msg)
    else:
        messages.info(request, msg)

    return redirect("attempts:exam_list")