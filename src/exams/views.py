"""Quản lý đề thi của giảng viên (FR-06, FR-07, UC Create Exam, UC Manage Exams).

Controller theo MVC: kiểm tra vai trò bằng role_required, lấy đề qua Teacher.manage_exam (đề của
người khác -> 403), quy tắc nghiệp vụ gọi phương thức Model, báo kết quả bằng messages.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import Role

from .forms import ExamForm
from .models import ExamStatus

STATUS_FILTERS = [(value, label) for value, label in ExamStatus.choices]


@role_required(Role.TEACHER)
def exam_list(request):
    """S3-11: danh sách đề thuộc giảng viên đang đăng nhập, lọc theo trạng thái."""
    teacher = request.user.as_role()
    selected_status = request.GET.get("status", "").strip()
    exams = teacher.exams.all()
    if selected_status in ExamStatus.values:
        exams = exams.filter(status=selected_status)
    else:
        selected_status = ""
    exams = exams.annotate(
        question_total=Count("exam_questions__question", distinct=True),
        participant_total=Count("participants__student", filter=Q(participants__is_active=True), distinct=True),
    ).order_by("-created_at", "-exam_id")
    return render(
        request,
        "exams/list.html",
        {"exams": exams, "selected_status": selected_status, "status_choices": STATUS_FILTERS},
    )


@role_required(Role.TEACHER)
def exam_create(request):
    """S3-11: tạo đề nháp DRAFT (Teacher.create_exam)."""
    teacher = request.user.as_role()
    form = ExamForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            exam = teacher.create_exam(form.cleaned_data)
        except ValidationError as error:
            _attach_errors(form, error)
        else:
            messages.success(request, "Đã tạo đề thi nháp.")
            return redirect("exams:detail", exam_id=exam.pk)
    return render(request, "exams/form.html", {"form": form, "exam": None})


@role_required(Role.TEACHER)
def exam_detail(request, exam_id):
    """S3-11: xem thông tin một đề của mình."""
    exam = request.user.as_role().manage_exam(exam_id)
    return render(request, "exams/detail.html", _detail_context(exam))


@role_required(Role.TEACHER)
def exam_edit(request, exam_id):
    """S3-11: sửa thông tin đề, chỉ khi đề còn DRAFT (BR-14, BR-17)."""
    exam = request.user.as_role().manage_exam(exam_id)
    if exam.status != ExamStatus.DRAFT:
        messages.error(request, "Đề đã phát hành, không thể sửa nội dung.")
        return redirect("exams:detail", exam_id=exam.pk)

    form = ExamForm(request.POST or None, initial=ExamForm.initial_from(exam))
    if request.method == "POST" and form.is_valid():
        try:
            exam.apply_settings(form.cleaned_data)
            exam.save()
        except ValidationError as error:
            _attach_errors(form, error)
        else:
            messages.success(request, "Đã lưu thay đổi đề thi.")
            return redirect("exams:detail", exam_id=exam.pk)
    return render(request, "exams/form.html", {"form": form, "exam": exam})


def _detail_context(exam):
    return {"exam": exam, "is_draft": exam.status == ExamStatus.DRAFT}


def _attach_errors(form, error):
    """Lỗi của Model theo từng trường -> hiện dưới đúng ô nhập; lỗi chung -> đầu form."""
    if hasattr(error, "error_dict"):
        for field, texts in error.message_dict.items():
            form.add_error(field if field in form.fields else None, texts)
    else:
        form.add_error(None, error.messages)
