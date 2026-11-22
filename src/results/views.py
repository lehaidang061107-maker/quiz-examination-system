"""S3-24: Xem kết quả thi theo quyền và điều kiện công bố (FR-13, BR-10, BR-19, UC View Exam Results)."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce, Lower
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import Role, User
from attempts.models import Submission, SubmissionStatus
from exams.models import Exam, ExamParticipant, ExamStatus

# Trạng thái một dòng kết quả, dùng chung cho template.
ROW_NOT_STARTED = "not_started"
ROW_IN_PROGRESS = "in_progress"
ROW_GRADING = "grading"
ROW_UNPUBLISHED = "unpublished"
ROW_GRADED = "graded"

PAGE_SIZE = 20  # NFR-PER-05: danh sách kết quả dài phải phân trang


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
        .order_by("-created_at", "-exam_id")
    )
    page_obj = Paginator(exams, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "results/teacher_list.html", {"exams": page_obj.object_list, "page_obj": page_obj})


@role_required(Role.TEACHER)
def teacher_exam(request, exam_id):
    """Kết quả từng sinh viên của một đề. Đề của Teacher khác -> 403 (manage_exam)."""
    teacher = request.user.as_role()
    exam = teacher.manage_exam(exam_id)
    # Sinh viên đã có bài làm, cộng sinh viên được giao nhưng chưa vào làm (để Teacher theo dõi).
    students = User.objects.filter(
        Q(pk__in=Submission.objects.filter(exam=exam).values("student_id"))
        | Q(pk__in=exam.participants.filter(is_active=True).values("student_id"))
    ).order_by(Lower("full_name"), "pk")
    page_obj = Paginator(students, PAGE_SIZE).get_page(request.GET.get("page"))
    page_ids = [student.pk for student in page_obj.object_list]

    results = {r.submission_id: r for r in teacher.view_results(exam.pk, student_ids=page_ids)}
    submissions = {s.student_id: s for s in Submission.objects.filter(exam=exam, student_id__in=page_ids)}

    rows = []
    for student in page_obj.object_list:
        submission = submissions.get(student.pk)
        if submission is None:
            rows.append({"student": student, "submission": None, "result": None, "state": ROW_NOT_STARTED})
            continue
        result = results.get(submission.pk)
        rows.append({"student": student, "submission": submission, "result": result,
                     "state": _submission_state(submission, result, published=True)})

    return render(request, "results/teacher_exam.html", {
        "exam": exam, "rows": rows, "page_obj": page_obj, "stats": teacher.view_statistics(exam.pk),
    })


STATE_LABELS = {
    ROW_NOT_STARTED: "Chưa làm bài", ROW_IN_PROGRESS: "Đang làm bài", ROW_GRADING: "Đang chấm",
    ROW_UNPUBLISHED: "Đã chấm", ROW_GRADED: "Đã chấm",
}


@role_required(Role.TEACHER)
def teacher_exam_csv(request, exam_id):
    """S3-34: tải bảng điểm cả đề ra CSV (UTF-8 có BOM để Excel đọc đúng tiếng Việt)."""
    import csv

    from django.http import HttpResponse
    from django.utils import timezone

    from results.templatetags.results_extras import duration

    teacher = request.user.as_role()
    exam = teacher.manage_exam(exam_id)
    students = User.objects.filter(
        Q(pk__in=Submission.objects.filter(exam=exam).values("student_id"))
        | Q(pk__in=exam.participants.filter(is_active=True).values("student_id"))
    ).order_by(Lower("full_name"), "pk")
    results = {r.submission_id: r for r in teacher.view_results(exam.pk)}
    submissions = {s.student_id: s for s in Submission.objects.filter(exam=exam)}

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ket-qua-de-{exam.pk}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["Họ và tên", "Email", "Trạng thái", "Điểm", "Điểm tối đa", "Điểm thang 10",
                     "Số câu đúng", "Số câu sai", "Bỏ trống", "Nộp lúc", "Thời gian làm"])
    for student in students:
        submission = submissions.get(student.pk)
        result = results.get(submission.pk) if submission else None
        state = ROW_NOT_STARTED if submission is None else _submission_state(submission, result, published=True)
        submitted = timezone.localtime(submission.submitted_at).strftime("%d/%m/%Y %H:%M") \
            if submission and submission.submitted_at else ""
        if result:
            writer.writerow([student.full_name, student.email, STATE_LABELS[state], result.score, result.max_score,
                             result.score_on_10, result.correct_count, result.wrong_count, result.blank_count,
                             submitted, duration(result.completion_time)])
        else:
            writer.writerow([student.full_name, student.email, STATE_LABELS[state], "", "", "", "", "", "",
                             submitted, ""])
    return response


@role_required(Role.STUDENT)
def student_list(request):
    """Lịch sử bài thi: các bài đã nộp của chính Student, điểm chỉ hiện khi đã công bố."""
    submissions = (
        Submission.objects.filter(student=request.user)
        .exclude(status=SubmissionStatus.IN_PROGRESS)
        .select_related("exam")
        .prefetch_related("results")
        .order_by("-submitted_at", "-pk")
    )
    page_obj = Paginator(submissions, PAGE_SIZE).get_page(request.GET.get("page"))
    rows = []
    for submission in page_obj.object_list:
        result = next(iter(submission.results.all()), None)
        state = _submission_state(submission, result, published=submission.exam.results_published)
        rows.append({"submission": submission, "exam": submission.exam,
                     "result": result if state == ROW_GRADED else None, "state": state})
    return render(request, "results/student_list.html", {"rows": rows, "page_obj": page_obj})


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
