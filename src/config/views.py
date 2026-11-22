from django.db import DatabaseError, connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from accounts.decorators import login_required_any_role
from accounts.models import Role, User, UserStatus
from attempts.models import Submission, SubmissionStatus
from exams.models import ExamStatus


@require_GET
def health(request):
    """Kiểm tra website đang chạy và kết nối được database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except DatabaseError:
        database = "error"
    status = 200 if database == "ok" else 503
    return JsonResponse({"status": "ok" if status == 200 else "error", "database": database}, status=status)


RECENT_LIMIT = 5


@login_required_any_role
def home(request):
    """Trang chủ theo vai trò (màn hình 03, 04 Figma) — trang mẫu MVC.

    Controller chỉ: kiểm tra quyền (decorator) -> lấy lớp con theo vai trò -> gọi phương thức
    của Model -> chọn template. Không tự viết quy tắc nghiệp vụ ở đây.
    Dưới các ô số là một bảng ngắn như Figma: Admin xem tài khoản mới, Teacher xem kỳ thi gần đây,
    Student xem các bài thi chưa nộp.
    """
    user = request.user.as_role()
    context = {}
    if user.role == Role.ADMIN:
        stats = [
            ("Tổng số tài khoản", User.objects.count()),
            ("Đang hoạt động", User.objects.filter(status=UserStatus.ACTIVE).count()),
            ("Bị khóa", User.objects.filter(status=UserStatus.LOCKED).count()),
        ]
        context["recent_users"] = User.objects.order_by("-created_at", "-user_id")[:RECENT_LIMIT]
    elif user.role == Role.TEACHER:
        exams = user.exams.all()
        stats = [
            ("Ngân hàng câu hỏi", user.manage_questions().count()),
            ("Kỳ thi đang mở", exams.filter(status=ExamStatus.PUBLISHED).count()),
            ("Bài thi đã nộp", Submission.objects.filter(exam__in=exams).exclude(
                status=SubmissionStatus.IN_PROGRESS).count()),
            # BR-19: đề đã đóng mà chưa công bố điểm là việc giảng viên còn phải làm.
            ("Đề chờ công bố điểm", exams.filter(status=ExamStatus.CLOSED, results_published=False).count()),
        ]
        context["recent_exams"] = exams.annotate(
            question_total=Count("exam_questions__question", distinct=True),
            participant_total=Count("participants__student", filter=Q(participants__is_active=True), distinct=True),
            submitted_total=Count(
                "submissions", filter=~Q(submissions__status=SubmissionStatus.IN_PROGRESS), distinct=True
            ),
        ).order_by("-created_at", "-exam_id")[:RECENT_LIMIT]
    else:
        exams = list(user.view_available_exams().select_related("teacher"))
        submissions = {s.exam_id: s for s in user.submissions.filter(exam__in=exams)}
        stats = [
            ("Bài thi được giao", len(exams)),
            ("Có thể làm ngay", sum(exam.can_start(user) for exam in exams)),
            ("Đã nộp", user.submissions.exclude(status=SubmissionStatus.IN_PROGRESS).count()),
        ]
        todo = []
        for exam in exams:
            submission = submissions.get(exam.pk)
            if submission is None:
                todo.append({"exam": exam, "in_progress": False, "reason": exam.cannot_start_reason(user)})
            elif submission.status == SubmissionStatus.IN_PROGRESS:
                todo.append({"exam": exam, "in_progress": True, "submission": submission, "reason": None})
        # Bài đang làm lên đầu, rồi tới bài làm được ngay, cuối cùng là bài chưa mở / đã đóng.
        todo.sort(key=lambda item: (not item["in_progress"], item["reason"] is not None))
        context["todo_exams"] = todo[:RECENT_LIMIT]
    context["stats"] = stats
    return render(request, "home.html", context)
