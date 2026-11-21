"""S3-24: Xem kết quả thi theo quyền và điều kiện công bố (FR-13, BR-10, BR-19, UC View Exam Results)."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import Role
from attempts.models import Submission, SubmissionStatus
from exams.models import Exam, ExamParticipant, ExamStatus

# Trạng thái một dòng kết quả, dùng chung cho template.
ROW_NOT_STARTED = "not_started"
ROW_IN_PROGRESS = "in_progress"
ROW_GRADING = "grading"
ROW_UNPUBLISHED = "unpublished"
ROW_GRADED = "graded"


@role_required(Role.TEACHER)
def teacher_list(request):
    """Danh sách đề Teacher phụ trách (trừ đề nháp) kèm số lượt đang làm / đang chấm / đã chấm."""
    active_participants = (
        ExamParticipant.objects.filter(exam=OuterRef("pk"), is_active=True)
        .order_by()
        .values("exam")
        .annotate(n=Count("student"))
        .values("n")
    )
    exams = (
        Exam.objects.filter(teacher=request.user)
        .exclude(status=ExamStatus.DRAFT)
        .annotate(
            participant_total=Coalesce(Subquery(active_participants), 0),
            in_progress_total=Count("submissions", filter=Q(submissions__status=SubmissionStatus.IN_PROGRESS)),
            grading_total=Count("submissions", filter=Q(submissions__status=SubmissionStatus.SUBMITTED)),
            graded_total=Count("submissions", filter=Q(submissions__status=SubmissionStatus.GRADED)),
        )
        .order_by("-created_at")
    )
    return render(request, "results/teacher_list.html", {"exams": exams})


@role_required(Role.TEACHER)
def teacher_exam(request, exam_id):
    """Kết quả từng sinh viên của một đề. Đề của Teacher khác -> 403 (manage_exam)."""
    teacher = request.user.as_role()
    exam = teacher.manage_exam(exam_id)
    results = {r.submission_id: r for r in teacher.view_results(exam.pk)}
    submissions = {
        s.student_id: s for s in Submission.objects.filter(exam=exam).select_related("student")
    }

    rows = []
    for submission in submissions.values():
        result = results.get(submission.pk)
        rows.append({"student": submission.student, "submission": submission, "result": result,
                     "state": _submission_state(submission, result, published=True)})
    # Sinh viên được giao nhưng chưa vào làm cũng hiện để Teacher theo dõi.
    for participant in exam.participants.filter(is_active=True).select_related("student"):
        if participant.student_id not in submissions:
            rows.append({"student": participant.student, "submission": None, "result": None,
                         "state": ROW_NOT_STARTED})
    rows.sort(key=lambda row: (row["student"].full_name.lower(), row["student"].pk))

    return render(request, "results/teacher_exam.html", {"exam": exam, "rows": rows})


@role_required(Role.STUDENT)
def student_list(request):
    """Lịch sử bài thi: các bài đã nộp của chính Student, điểm chỉ hiện khi đã công bố."""
    submissions = (
        Submission.objects.filter(student=request.user)
        .exclude(status=SubmissionStatus.IN_PROGRESS)
        .select_related("exam")
        .prefetch_related("results")
        .order_by("-submitted_at")
    )
    rows = []
    for submission in submissions:
        result = next(iter(submission.results.all()), None)
        state = _submission_state(submission, result, published=submission.exam.results_published)
        rows.append({"submission": submission, "exam": submission.exam,
                     "result": result if state == ROW_GRADED else None, "state": state})
    return render(request, "results/student_list.html", {"rows": rows})


@role_required(Role.STUDENT)
def student_detail(request, exam_id):
    """Kết quả một đề của chính Student. Đổi ID sang đề không có bài của mình -> 403."""
    student = request.user.as_role()
    submission = Submission.objects.filter(exam_id=exam_id, student=student).select_related("exam").first()
    if submission is None:
        raise PermissionDenied("Bạn không có kết quả cho đề thi này.")
    if submission.status == SubmissionStatus.IN_PROGRESS:
        messages.info(request, "Bạn chưa nộp bài thi này.")
        return redirect("attempts:exam_list")

    result = student.view_result(exam_id)  # None nếu chưa chấm hoặc chưa công bố
    state = _submission_state(submission, result, published=submission.exam.results_published)
    return render(
        request,
        "results/student_detail.html",
        {"exam": submission.exam, "submission": submission, "result": result, "state": state},
    )


def _submission_state(submission, result, published):
    """Bài đã nộp mà chưa có kết quả là 'đang chấm', không coi là 0 điểm."""
    if submission.status == SubmissionStatus.IN_PROGRESS:
        return ROW_IN_PROGRESS
    if result is None and submission.status == SubmissionStatus.SUBMITTED:
        return ROW_GRADING
    if not published:
        return ROW_UNPUBLISHED
    if result is None:
        return ROW_GRADING
    return ROW_GRADED
