
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Count
from django.shortcuts import render

from accounts.decorators import role_required
from accounts.models import Role
from questions.models import QuestionStatus


@role_required(Role.TEACHER)
def question_list(request):
    """Hiển thị ngân hàng câu hỏi của giảng viên đang đăng nhập."""

    search_query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()

    try:
        teacher = request.user.as_role()

        # Chỉ lấy câu hỏi thuộc giảng viên hiện tại.
        questions = teacher.manage_questions()

        # Mặc định không hiển thị câu hỏi đã lưu trữ.
        questions = questions.exclude(status=QuestionStatus.ARCHIVED)

        # Tìm kiếm theo nội dung câu hỏi.
        if search_query:
            questions = questions.filter(content__icontains=search_query)

        # Chỉ chấp nhận hai trạng thái được phép lọc.
        if selected_status in (
            QuestionStatus.DRAFT,
            QuestionStatus.ACTIVE,
        ):
            questions = questions.filter(status=selected_status)
        else:
            selected_status = ""

        # Đếm số phương án trả lời của từng câu hỏi.
        questions = questions.annotate(
            option_count=Count("options")
        )

        # Phân trang: 10 câu hỏi mỗi trang.
        paginator = Paginator(questions, 10)
        page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "page_obj": page_obj,
            "questions": page_obj.object_list,
            "search_query": search_query,
            "selected_status": selected_status,
            "status_choices": [
                (QuestionStatus.DRAFT, "Nháp"),
                (QuestionStatus.ACTIVE, "Đang dùng"),
            ],
        }

        return render(
            request,
            "questions/list.html",
            context,
        )

    except DatabaseError:
        return render(
            request,
            "questions/list.html",
            {
                "page_obj": None,
                "questions": [],
                "search_query": search_query,
                "selected_status": selected_status,
                "status_choices": [
                    (QuestionStatus.DRAFT, "Nháp"),
                    (QuestionStatus.ACTIVE, "Đang dùng"),
                ],
                "error_message": (
                    "Không thể tải danh sách câu hỏi. "
                    "Vui lòng thử lại sau."
                ),
            },
            status=503,
        )
