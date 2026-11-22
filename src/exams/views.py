"""Quản lý đề thi của giảng viên (FR-06, FR-07, UC Create Exam, UC Manage Exams).

Controller theo MVC: kiểm tra vai trò bằng role_required, lấy đề qua Teacher.manage_exam (đề của
người khác -> 403), quy tắc nghiệp vụ gọi phương thức Model, báo kết quả bằng messages.
"""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role
from questions.models import QuestionStatus

from .forms import ExamForm
from .models import Exam, ExamStatus

STATUS_FILTERS = [(value, label) for value, label in ExamStatus.choices]
PAGE_SIZE = 20  # NFR-PER-05: danh sách dài phải phân trang


def _lock_exam(exam):
    """Khóa dòng đề tới hết transaction rồi đọc lại trạng thái mới nhất.

    Hai tab cùng thao tác (vd. một tab sửa nháp, tab kia vừa phát hành) sẽ chạy lần lượt,
    tab sau thấy trạng thái đã đổi nên không sửa được đề đã phát hành (BR-14).
    Phải gọi bên trong transaction.atomic().
    """
    return Exam.objects.select_for_update().get(pk=exam.pk)


def _page_query(request):
    """Tham số lọc hiện tại (bỏ page) để nút Trước/Sau giữ nguyên bộ lọc."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


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
    page_obj = Paginator(exams, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "exams/list.html",
        {
            "exams": page_obj.object_list,
            "page_obj": page_obj,
            "page_query": _page_query(request),
            "selected_status": selected_status,
            "status_choices": STATUS_FILTERS,
        },
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
            with transaction.atomic():
                exam = _lock_exam(exam)
                exam.check_draft()  # tab khác có thể vừa phát hành đề
                exam.apply_settings(form.cleaned_data)
                exam.save()
        except ValidationError as error:
            _attach_errors(form, error)
        else:
            messages.success(request, "Đã lưu thay đổi đề thi.")
            return redirect("exams:detail", exam_id=exam.pk)
    return render(request, "exams/form.html", {"form": form, "exam": exam})


@role_required(Role.TEACHER)
def exam_questions(request, exam_id):
    """S3-12: chọn câu hỏi ACTIVE của mình vào đề nháp, sắp xếp thứ tự, nhập điểm từng câu."""
    exam = request.user.as_role().manage_exam(exam_id)
    if exam.status != ExamStatus.DRAFT:
        messages.error(request, "Đề đã phát hành, không thể sửa nội dung.")
        return redirect("exams:detail", exam_id=exam.pk)

    if request.method == "POST":
        try:
            with transaction.atomic():
                text = _handle_question_action(request, exam)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            if text:
                messages.success(request, text)
        return redirect(request.get_full_path())

    search = request.GET.get("q", "").strip()
    bank = (
        request.user.as_role().manage_questions()
        .filter(status=QuestionStatus.ACTIVE)
        .exclude(exam_questions__exam=exam)
        .annotate(option_count=Count("options"))
    )
    if search:
        bank = bank.filter(content__icontains=search)
    page_obj = Paginator(bank, 10).get_page(request.GET.get("page"))
    context = _detail_context(exam)
    context.update({"page_obj": page_obj, "bank": page_obj.object_list, "search": search})
    return render(request, "exams/questions.html", context)


def _handle_question_action(request, exam):
    """Mỗi nút gửi action dạng "add", "save_points", "remove:<id>", "up:<id>", "down:<id>"."""
    action, _, target = request.POST.get("action", "").partition(":")
    if action == "add":
        ids = request.POST.getlist("question_ids")
        if not ids:
            raise ValidationError("Vui lòng chọn ít nhất 1 câu hỏi.")
        for question_id in ids:
            exam.add_question(_int(question_id), _points(request.POST.get("points")))
        return f"Đã thêm {len(ids)} câu hỏi vào đề."
    if action == "save_points":
        for item in exam.exam_questions.order_by("position"):
            value = request.POST.get(f"points_{item.question_id}")
            if value is None:
                continue
            try:
                item.set_points(_points(value))
            except ValidationError as error:
                raise ValidationError(f"Câu {item.position}: {error.messages[0]}")
        return "Đã lưu điểm các câu hỏi."
    if action == "remove":
        exam.remove_question(_int(target))
        return "Đã bỏ câu hỏi khỏi đề."
    if action in ("up", "down"):
        item = exam.exam_questions.filter(question_id=_int(target)).first()
        if item is None:
            raise ValidationError("Câu hỏi không có trong đề.")
        last = exam.exam_questions.count()
        new_position = item.position - 1 if action == "up" else item.position + 1
        if 1 <= new_position <= last:
            item.set_position(new_position)
        return None
    raise ValidationError("Thao tác không hợp lệ.")


def _points(value):
    """Cho phép gõ dấu phẩy thập phân kiểu Việt Nam (2,5)."""
    value = (value or "").strip().replace(",", ".")
    if not value:
        raise ValidationError("Vui lòng nhập điểm.")
    return value


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError("Câu hỏi không hợp lệ.")


@role_required(Role.TEACHER)
@require_POST
def exam_publish(request, exam_id):
    """S3-12: phát hành đề DRAFT -> PUBLISHED; chưa đủ điều kiện thì báo từng mục cần sửa (BR-17)."""
    exam = request.user.as_role().manage_exam(exam_id)
    try:
        exam.publish()
    except ValidationError as error:
        messages.error(request, "Chưa thể phát hành đề:")
        for text in error.messages:
            messages.error(request, text)
    else:
        messages.success(request, "Đã phát hành đề thi.")
    return redirect("exams:detail", exam_id=exam.pk)


def _detail_context(exam):
    items = list(exam.exam_questions.select_related("question").order_by("position"))
    return {
        "exam": exam,
        "is_draft": exam.status == ExamStatus.DRAFT,
        "items": items,
        "total_points": sum((item.points for item in items), 0),
    }


def _attach_errors(form, error):
    """Lỗi của Model theo từng trường -> hiện dưới đúng ô nhập; lỗi chung -> đầu form."""
    if hasattr(error, "error_dict"):
        for field, texts in error.message_dict.items():
            form.add_error(field if field in form.fields else None, texts)
    else:
        form.add_error(None, error.messages)
