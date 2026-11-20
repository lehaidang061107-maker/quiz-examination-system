"""URL chỉ dùng trong test: thêm một trang Teacher theo đúng mẫu MVC để kiểm tra decorator và messages."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import path

from accounts.decorators import role_required
from accounts.models import Role
from config.urls import urlpatterns as project_urls


@role_required(Role.TEACHER)
def publish_exam(request, exam_id):
    """Mẫu Controller giống docs/guides/03-coding-guidelines.md: gọi Model, lỗi nghiệp vụ hiện bằng messages."""
    teacher = request.user.as_role()
    exam = teacher.manage_exam(exam_id)  # đề của người khác -> PermissionDenied -> 403
    try:
        exam.publish()
        messages.success(request, "Đã phát hành đề thi.")
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    return redirect("home")


urlpatterns = project_urls + [path("test/exams/<int:exam_id>/publish/", publish_exam, name="test_publish")]
