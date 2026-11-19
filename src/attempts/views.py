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

from .models import Submission, SubmissionAnswer, SubmissionStatus


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


@role_required(Role.STUDENT)
def take_exam(request, submission_id):
    """S3-17: Phòng làm bài thi với đồng hồ đếm ngược và danh sách câu hỏi."""
    submission = get_object_or_404(
        Submission.objects.select_related("exam"),
        pk=submission_id,
        student=request.user,
    )

    if submission.status != SubmissionStatus.IN_PROGRESS:
        messages.info(request, "Lượt thi này đã được nộp.")
        return redirect("attempts:exam_list")

    # Nếu đã quá hạn nộp thì tự động chốt bài
    if timezone.now() >= submission.deadline_at:
        submission.auto_submit()
        messages.warning(request, "Đã hết thời gian làm bài. Hệ thống đã tự động nộp bài của bạn.")
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

    remaining_seconds = max(0, int((submission.deadline_at - timezone.now()).total_seconds()))

    return render(
        request,
        "attempts/take_exam.html",
        {
            "submission": submission,
            "exam": submission.exam,
            "question_items": question_items,
            "remaining_seconds": remaining_seconds,
        },
    )


@role_required(Role.STUDENT)
@require_POST
def save_answer_api(request, submission_id):
    """S3-17: API AJAX lưu đáp án tự động và kiểm tra version chống mở 2 tab."""
    submission = get_object_or_404(Submission, pk=submission_id, student=request.user)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        question_id = int(payload.get("question_id"))
        raw_option_id = payload.get("option_id")
        option_id = int(raw_option_id) if raw_option_id is not None else None
        version = int(payload.get("version"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Dữ liệu gửi lên không hợp lệ."}, status=400)

    try:
        new_version = submission.save_answer(
            question_id=question_id,
            option_id=option_id,
            version=version,
        )
    except ValidationError as exc:
        msg = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
        return JsonResponse({"ok": False, "error": msg}, status=409)

    return JsonResponse({"ok": True, "version": new_version})


@role_required(Role.STUDENT)
@require_POST
def submit_exam(request, submission_id):
    """S3-18: Sinh viên bấm nộp bài thủ công."""
    submission = get_object_or_404(Submission, pk=submission_id, student=request.user)

    if submission.status == SubmissionStatus.IN_PROGRESS:
        submission.submit()
        messages.success(request, f"Đã nộp bài thi '{submission.exam.title}' thành công!")
    else:
        messages.info(request, "Bài thi này đã được nộp trước đó.")

    return redirect("attempts:exam_list")