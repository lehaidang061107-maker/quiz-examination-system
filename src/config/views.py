from django.db import DatabaseError, connection
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


@login_required_any_role
def home(request):
    """Trang chủ theo vai trò (màn hình 03, 04 Figma) — trang mẫu MVC.

    Controller chỉ: kiểm tra quyền (decorator) -> lấy lớp con theo vai trò -> gọi phương thức
    của Model -> chọn template. Không tự viết quy tắc nghiệp vụ ở đây.
    """
    user = request.user.as_role()
    if user.role == Role.ADMIN:
        stats = [
            ("Tổng số tài khoản", User.objects.count()),
            ("Đang hoạt động", User.objects.filter(status=UserStatus.ACTIVE).count()),
            ("Bị khóa", User.objects.filter(status=UserStatus.LOCKED).count()),
        ]
    elif user.role == Role.TEACHER:
        exams = user.exams.all()
        stats = [
            ("Ngân hàng câu hỏi", user.manage_questions().count()),
            ("Kỳ thi đang mở", exams.filter(status=ExamStatus.PUBLISHED).count()),
            ("Bài thi đã nộp", Submission.objects.filter(exam__in=exams).exclude(
                status=SubmissionStatus.IN_PROGRESS).count()),
        ]
    else:
        exams = user.view_available_exams()
        stats = [
            ("Bài thi được giao", exams.count()),
            ("Có thể làm ngay", sum(exam.can_start(user) for exam in exams)),
            ("Đã nộp", user.submissions.exclude(status=SubmissionStatus.IN_PROGRESS).count()),
        ]
    return render(request, "home.html", {"stats": stats})
