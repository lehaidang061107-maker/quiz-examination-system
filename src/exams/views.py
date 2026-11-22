"""Quản lý đề thi của giảng viên (FR-06, FR-07, UC Create Exam, UC Manage Exams).

Controller theo MVC: kiểm tra vai trò bằng role_required, lấy đề qua Teacher.manage_exam (đề của
người khác -> 403), quy tắc nghiệp vụ gọi phương thức Model, báo kết quả bằng messages.
"""
import logging

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role, Student, UserStatus
from attempts.models import Submission, SubmissionStatus
from questions.models import QuestionStatus

from .forms import ExamForm
from .models import Exam, ExamParticipant, ExamStatus

audit_log = logging.getLogger("exams.audit")

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
    """S3-11: danh sách đề thuộc giảng viên đang đăng nhập, lọc theo trạng thái và tên đề.

    Ba ô số ở đầu trang như màn hình 09 Figma: tổng số đề, đang mở, đã kết thúc (đóng hoặc lưu trữ).
    """
    teacher = request.user.as_role()
    selected_status = request.GET.get("status", "").strip()
    search = request.GET.get("q", "").strip()
    exams = teacher.exams.all()
    counts = dict(exams.order_by().values_list("status").annotate(n=Count("exam_id")))
    stats = [
        ("Tổng kỳ thi", sum(counts.values())),
        ("Đang mở", counts.get(ExamStatus.PUBLISHED, 0)),
        ("Đã kết thúc", counts.get(ExamStatus.CLOSED, 0) + counts.get(ExamStatus.ARCHIVED, 0)),
    ]
    if search:
        exams = exams.filter(title__icontains=search)
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
            "search": search,
            "stats": stats,
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
                exam = _lock_exam(exam)
                exam.check_draft()  # tab khác có thể vừa phát hành đề
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


def _int(value, error="Câu hỏi không hợp lệ."):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError(error)


@role_required(Role.TEACHER)
@require_POST
def exam_publish(request, exam_id):
    """S3-12: phát hành đề DRAFT -> PUBLISHED; chưa đủ điều kiện thì báo từng mục cần sửa (BR-17)."""
    exam = request.user.as_role().manage_exam(exam_id)
    try:
        with transaction.atomic():
            exam = _lock_exam(exam)  # chờ thao tác sửa câu hỏi/điểm đang chạy xong rồi mới kiểm tra
            exam.publish()
    except ValidationError as error:
        messages.error(request, "Chưa thể phát hành đề:")
        for text in error.messages:
            messages.error(request, text)
    else:
        messages.success(request, "Đã phát hành đề thi.")
    return redirect("exams:detail", exam_id=exam.pk)


@role_required(Role.TEACHER)
def exam_participants(request, exam_id):
    """S3-13: cấp quyền dự thi cho Student ACTIVE và thu hồi quyền, giữ lịch sử phân công (BR-18)."""
    teacher = request.user.as_role()
    exam = teacher.manage_exam(exam_id)

    if request.method == "POST":
        action, _, target = request.POST.get("action", "").partition(":")
        try:
            with transaction.atomic():
                exam = _lock_exam(exam)  # không cấp/thu hồi xen giữa lúc đề đang được đóng
                if action == "grant":
                    text = _grant(teacher, exam, request.POST.getlist("student_ids"))
                elif action == "revoke":
                    text = _revoke(exam, _int(target, "Sinh viên không hợp lệ."))
                else:
                    raise ValidationError("Thao tác không hợp lệ.")
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
        else:
            messages.success(request, text)
        return redirect(request.get_full_path())

    search = request.GET.get("q", "").strip()
    participants = {p.student_id: p for p in exam.participants.all()}
    # Student ACTIVE (để cấp quyền) và mọi người đã từng được phân công (để xem lịch sử, kể cả đã bị khóa).
    students = Student.objects.filter(Q(status=UserStatus.ACTIVE) | Q(pk__in=participants.keys()))
    if search:
        students = students.filter(Q(full_name__icontains=search) | Q(email__icontains=search))
    # NFR-PER-05: hệ thống có thể tới 10.000 tài khoản, chỉ tải từng trang sinh viên.
    page_obj = Paginator(students.order_by("full_name", "user_id"), PAGE_SIZE).get_page(request.GET.get("page"))
    page_ids = [student.pk for student in page_obj.object_list]
    submissions = {s.student_id: s for s in Submission.objects.filter(exam=exam, student_id__in=page_ids)}
    rows = []
    for student in page_obj.object_list:
        participant = participants.get(student.pk)
        rows.append({
            "student": student,
            "participant": participant,
            "submission": submissions.get(student.pk),
            "assigned": bool(participant and participant.is_active),
        })
    context = _detail_context(exam)
    context.update({
        "rows": rows,
        "page_obj": page_obj,
        "page_query": _page_query(request),
        "search": search,
        "can_change": _can_change_participants(exam),
        "assigned_total": sum(1 for p in participants.values() if p.is_active),
    })
    return render(request, "exams/participants.html", context)


def _can_change_participants(exam):
    """Chỉ cấp/thu hồi khi đề DRAFT hoặc PUBLISHED chưa hết lịch (BR-18)."""
    if exam.status not in (ExamStatus.DRAFT, ExamStatus.PUBLISHED):
        return False
    return not (exam.closes_at and exam.closes_at <= timezone.now())


def _grant(teacher, exam, raw_ids):
    if not raw_ids:
        raise ValidationError("Vui lòng chọn ít nhất 1 sinh viên.")
    invalid = "Có sinh viên không hợp lệ trong danh sách đã chọn."
    ids = {_int(value, invalid) for value in raw_ids}
    found = set(Student.objects.filter(pk__in=ids).values_list("pk", flat=True))
    if found != ids:
        raise ValidationError(invalid)
    already = set(
        ExamParticipant.objects.filter(exam=exam, student_id__in=ids, is_active=True).values_list("student_id", flat=True)
    )
    new_ids = sorted(ids - already)
    if not new_ids:
        raise ValidationError("Các sinh viên đã chọn đều đã được cấp quyền.")
    teacher.assign_students(exam.pk, new_ids)  # kiểm tra Student ACTIVE và trạng thái đề, lỗi thì không cấp ai
    return f"Đã cấp quyền dự thi cho {len(new_ids)} sinh viên."


def _revoke(exam, student_id):
    participant = ExamParticipant.objects.filter(exam=exam, student_id=student_id).select_related("student").first()
    if participant is None:
        raise ValidationError("Sinh viên chưa được cấp quyền cho đề này.")
    if not participant.is_active:
        raise ValidationError("Sinh viên đã bị thu hồi quyền trước đó.")
    was_working = Submission.objects.filter(
        exam=exam, student_id=student_id, status=SubmissionStatus.IN_PROGRESS
    ).exists()
    participant.revoke_access()
    name = participant.student.full_name
    if was_working:
        return f"Đã thu hồi quyền của {name}. Bài đang làm đã được chốt và nộp bằng đáp án đã lưu."
    return f"Đã thu hồi quyền của {name}."


@role_required(Role.TEACHER)
@require_POST
def exam_close(request, exam_id):
    """S3-14: đóng đề PUBLISHED -> CLOSED; bài đang làm được nộp bằng đáp án đã lưu. Không mở lại được."""
    exam = request.user.as_role().manage_exam(exam_id)
    try:
        with transaction.atomic():
            exam = _lock_exam(exam)
            in_progress = exam.submissions.filter(status=SubmissionStatus.IN_PROGRESS).count()
            exam.close()
    except ValidationError as error:
        _show_errors(request, error)
    else:
        _audit(request, exam, "đóng đề", f"tự nộp {in_progress} bài đang làm")
        text = "Đã đóng đề thi."
        if in_progress:
            text += f" {in_progress} bài đang làm đã được nộp bằng đáp án đã lưu."
        messages.success(request, text)
    return redirect("exams:detail", exam_id=exam.pk)


@role_required(Role.TEACHER)
@require_POST
def exam_publish_results(request, exam_id):
    """S3-14: công bố điểm khi đề CLOSED và mọi bài đã chấm (BR-19). Chưa có thao tác thu hồi công bố."""
    exam = request.user.as_role().manage_exam(exam_id)
    if exam.results_published:
        messages.info(request, "Điểm của đề này đã được công bố trước đó.")
        return redirect("exams:detail", exam_id=exam.pk)
    try:
        with transaction.atomic():
            exam = _lock_exam(exam)
            exam.publish_results()
    except ValidationError as error:
        _show_errors(request, error)
    else:
        _audit(request, exam, "công bố điểm", f"{exam.submissions.count()} bài")
        messages.success(request, "Đã công bố điểm. Sinh viên đã xem được kết quả của mình.")
    return redirect("exams:detail", exam_id=exam.pk)


@role_required(Role.TEACHER)
@require_POST
def exam_delete(request, exam_id):
    """Xóa đề nháp (có xác nhận ở giao diện). Đề đã phát hành không xóa được."""
    exam = request.user.as_role().manage_exam(exam_id)
    try:
        with transaction.atomic():
            exam = _lock_exam(exam)
            title, pk = exam.title, exam.pk
            exam.delete_draft()
    except ValidationError as error:
        _show_errors(request, error)
        return redirect("exams:detail", exam_id=exam.pk)
    exam.pk = pk  # delete() đặt pk về None; giữ lại để ghi nhật ký
    _audit(request, exam, "xóa đề nháp")
    messages.success(request, f"Đã xóa đề nháp '{title}'.")
    return redirect("exams:list")


@role_required(Role.TEACHER)
@require_POST
def exam_archive(request, exam_id):
    """S3-14: lưu trữ đề CLOSED -> ARCHIVED khi không còn bài đang làm/chờ chấm (BR-17)."""
    exam = request.user.as_role().manage_exam(exam_id)
    try:
        with transaction.atomic():
            exam = _lock_exam(exam)
            exam.archive()
    except ValidationError as error:
        _show_errors(request, error)
    else:
        _audit(request, exam, "lưu trữ đề")
        messages.success(request, "Đã lưu trữ đề thi.")
    return redirect("exams:detail", exam_id=exam.pk)


def _show_errors(request, error):
    for text in error.messages:
        messages.error(request, text)


def _audit(request, exam, action, note=""):
    """Ghi ai làm gì, lúc nào (giờ máy chủ) với đề nào để truy vết."""
    audit_log.info(
        "%s | user_id=%s (%s) | exam_id=%s '%s'%s",
        action, request.user.pk, request.user.email, exam.pk, exam.title, f" | {note}" if note else "",
    )


def _submission_counts(exam):
    counts = dict(
        exam.submissions.order_by().values_list("status").annotate(n=Count("submission_id")).values_list("status", "n")
    )
    return {
        "in_progress": counts.get(SubmissionStatus.IN_PROGRESS, 0),
        "submitted": counts.get(SubmissionStatus.SUBMITTED, 0),
        "graded": counts.get(SubmissionStatus.GRADED, 0),
    }


def _detail_context(exam):
    items = list(exam.exam_questions.select_related("question").order_by("position"))
    return {
        "exam": exam,
        "is_draft": exam.status == ExamStatus.DRAFT,
        "items": items,
        "total_points": sum((item.points for item in items), 0),
        "participant_total": exam.participants.filter(is_active=True).count(),
        "counts": _submission_counts(exam),
    }


def _attach_errors(form, error):
    """Lỗi của Model theo từng trường -> hiện dưới đúng ô nhập; lỗi chung -> đầu form."""
    if hasattr(error, "error_dict"):
        for field, texts in error.message_dict.items():
            form.add_error(field if field in form.fields else None, texts)
    else:
        form.add_error(None, error.messages)
