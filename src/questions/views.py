from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, models, transaction
from django.db.models import Count, Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import Role
from attempts.models import SubmissionAnswer
from exams.models import ExamQuestion, ExamStatus
from questions.models import Question, QuestionStatus


STATUS_CHOICES = [
    (QuestionStatus.DRAFT, "Nháp"),
    (QuestionStatus.ACTIVE, "Đang dùng"),
    (QuestionStatus.ARCHIVED, "Lưu trữ"),
]


@role_required(Role.TEACHER)
def question_list(request):
    """Hiển thị ngân hàng câu hỏi của giảng viên đang đăng nhập."""

    search_query = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "").strip()

    try:
        teacher = request.user.as_role()

        # Chỉ lấy câu hỏi thuộc giảng viên hiện tại.
        questions = teacher.manage_questions()

        # Ô số đầu trang (màn hình 07 Figma): tổng quan cả ngân hàng, không đổi theo bộ lọc.
        counts = dict(questions.order_by().values_list("status").annotate(n=Count("question_id")))
        # Câu có trong ít nhất một đề đã phát hành (dù còn nằm trong đề nháp khác) — BR-14.
        used = questions.filter(
            Exists(ExamQuestion.objects.filter(question_id=OuterRef("question_id")).exclude(
                exam__status=ExamStatus.DRAFT))
        ).count()
        stats = [
            ("Tổng câu hỏi", counts.get(QuestionStatus.ACTIVE, 0) + counts.get(QuestionStatus.DRAFT, 0)),
            ("Đang dùng", counts.get(QuestionStatus.ACTIVE, 0)),
            ("Nháp", counts.get(QuestionStatus.DRAFT, 0)),
            ("Đã dùng trong đề phát hành", used),
        ]

        # Tìm kiếm theo nội dung câu hỏi.
        if search_query:
            questions = questions.filter(content__icontains=search_query)

        # Mặc định không hiển thị câu hỏi đã lưu trữ; chọn lọc "Lưu trữ" thì mới thấy.
        if selected_status in QuestionStatus.values:
            questions = questions.filter(status=selected_status)
        else:
            selected_status = ""
            questions = questions.exclude(status=QuestionStatus.ARCHIVED)

        # Đếm số phương án và kiểm tra câu hỏi đã được sử dụng.
        questions = questions.annotate(
            option_count=Count("options"),
            is_locked=Exists(
                ExamQuestion.objects.filter(
                    question_id=OuterRef("question_id"),
                ).exclude(
                    exam__status=ExamStatus.DRAFT,
                ),
            ),
        )

        # Phân trang: 10 câu hỏi mỗi trang.
        paginator = Paginator(questions, 10)
        page_obj = paginator.get_page(request.GET.get("page"))

        context = {
            "page_obj": page_obj,
            "questions": page_obj.object_list,
            "search_query": search_query,
            "selected_status": selected_status,
            "status_choices": STATUS_CHOICES,
            "stats": stats,
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
                "status_choices": STATUS_CHOICES,
                "error_message": (
                    "Không thể tải danh sách câu hỏi. "
                    "Vui lòng thử lại sau."
                ),
            },
            status=503,
        )


@role_required(Role.TEACHER)
def question_create(request):
    """Tạo câu hỏi mới và các phương án trả lời."""

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        option_contents = request.POST.getlist("option_content")
        correct_index = request.POST.get("correct_option", "")
        action = request.POST.get("action", "draft")

        if action not in ("draft", "activate"):
            messages.error(request, "Thao tác không hợp lệ.")
            return redirect("questions:create")

        try:
            with transaction.atomic():
                question = Question.objects.create(
                    teacher=request.user,
                    content=content,
                )

                # Lưu phương án theo đúng vị trí trên biểu mẫu.
                options_by_index = {}

                for index, option_content in enumerate(option_contents):
                    option_content = option_content.strip()

                    # Cho phép bỏ qua phương án trống khi lưu nháp.
                    if not option_content:
                        if action == "activate":
                            raise ValidationError(
                                f"Phương án {index + 1} không được để trống."
                            )
                        continue

                    option = question.add_option({
                        "content": option_content,
                    })
                    options_by_index[index] = option

                # Đánh dấu đáp án đúng theo vị trí đã chọn.
                if correct_index.isdigit():
                    index = int(correct_index)
                    selected_option = options_by_index.get(index)

                    if selected_option:
                        selected_option.set_correct(True)

                # Chỉ kích hoạt khi câu hỏi hợp lệ.
                if action == "activate":
                    question.activate()

            messages.success(
                request,
                "Tạo câu hỏi thành công."
                if action == "draft"
                else "Tạo và kích hoạt câu hỏi thành công.",
            )
            return redirect("questions:list")

        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        except DatabaseError:
            messages.error(
                request,
                "Không thể lưu câu hỏi. Vui lòng thử lại.",
            )

    form_data = None

    if request.method == "POST":
        option_contents = request.POST.getlist("option_content")
        correct_option = request.POST.get("correct_option", "")

        form_options = []

        for index, option_content in enumerate(option_contents):
            form_options.append({
                "option_id": "",
                "content": option_content,
                "is_correct": correct_option == str(index),
            })

        form_data = {
            "content": request.POST.get("content", ""),
            "options": form_options,
        }

    return render(request, "questions/editor.html", {
        "question": None,
        "options": [],
        "form_data": form_data,
        "page_heading": "Tạo câu hỏi",
    })


@role_required(Role.TEACHER)
@require_POST
def question_revision(request, question_id):
    """Tạo phiên bản DRAFT mới từ câu hỏi đã được sử dụng."""

    question = get_object_or_404(
        Question,
        question_id=question_id,
        teacher=request.user,
    )

    if not question.is_locked():
        messages.error(
            request,
            "Chỉ có thể tạo phiên bản mới cho câu hỏi "
            "đã được sử dụng trong đề phát hành.",
        )
        return redirect("questions:list")

    try:
        revision = question.create_revision()
        messages.success(
            request,
            "Đã tạo phiên bản mới. Bạn có thể chỉnh sửa bản sao này.",
        )
        return redirect(
            "questions:edit",
            question_id=revision.question_id,
        )
    except (ValidationError, DatabaseError):
        messages.error(
            request,
            "Không thể tạo phiên bản mới. Vui lòng thử lại.",
        )
        return redirect("questions:list")


@role_required(Role.TEACHER)
def question_edit(request, question_id):
    """Chỉnh sửa câu hỏi và các phương án trả lời."""

    question = get_object_or_404(
        Question,
        question_id=question_id,
        teacher=request.user,
    )

    try:
        question.check_editable()
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("questions:list")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        option_ids = request.POST.getlist("option_id")
        option_contents = request.POST.getlist("option_content")
        correct_index = request.POST.get("correct_option", "")
        action = request.POST.get("action", "draft")

        if action not in ("draft", "activate"):
            messages.error(request, "Thao tác không hợp lệ.")
            return redirect("questions:edit", question_id=question_id)

        if len(option_ids) != len(option_contents):
            messages.error(request, "Dữ liệu phương án không hợp lệ.")
            return redirect("questions:edit", question_id=question_id)

        try:
            with transaction.atomic():
                question.check_editable()

                # Lấy các phương án hiện có của câu hỏi.
                existing_options = {
                    str(option.option_id): option
                    for option in question.options.all()
                }

                submitted_ids = [
                    option_id for option_id in option_ids
                    if option_id.strip()
                ]

                # Không chấp nhận ID trùng hoặc ID không thuộc câu hỏi.
                if len(submitted_ids) != len(set(submitted_ids)):
                    raise ValidationError("Phương án bị trùng ID.")

                if any(
                    option_id not in existing_options
                    for option_id in submitted_ids
                ):
                    raise ValidationError("Phương án không thuộc câu hỏi này.")

                # Chuyển về nháp để có thể thay đổi đáp án đúng.
                question.status = QuestionStatus.DRAFT
                question.content = content
                question.save(update_fields=["status", "content"])

                # Tạm bỏ đánh dấu đúng ở các phương án cũ.
                for option in existing_options.values():
                    if option.is_correct:
                        option.set_correct(False)

                options_by_index = {}
                ordered_options = []
                retained_ids = set()

                # Cập nhật phương án cũ hoặc thêm phương án mới.
                for index, (option_id, option_content) in enumerate(
                    zip(option_ids, option_contents)
                ):
                    option_content = option_content.strip()

                    if not option_content:
                        if action == "activate":
                            raise ValidationError(
                                f"Phương án {index + 1} không được để trống."
                            )
                        continue

                    if option_id.strip():
                        option = existing_options[option_id]
                        option.update_content(option_content)
                        retained_ids.add(option_id)
                    else:
                        option = question.add_option({
                            "content": option_content,
                        })

                    options_by_index[index] = option
                    ordered_options.append(option)

                # Kiểm tra trước khi xóa phương án không còn trên biểu mẫu.
                removed_options = (
                    set(existing_options.keys()) - retained_ids
                )

                for option_id in removed_options:
                    if SubmissionAnswer.objects.filter(
                        selected_option_id=option_id
                    ).exists():
                        raise ValidationError(
                            "Không thể xóa phương án đã được sử dụng "
                            "trong bài làm của thí sinh."
                        )

                for option_id in removed_options:
                    existing_options[option_id].delete()

                # Sắp xếp lại thứ tự mà không vi phạm ràng buộc duy nhất.
                max_order = (
                    question.options.aggregate(
                        maximum=models.Max("display_order")
                    )["maximum"] or 0
                )

                for index, option in enumerate(ordered_options):
                    option.display_order = max_order + index + 1
                    option.save(update_fields=["display_order"])

                for index, option in enumerate(ordered_options, start=1):
                    option.display_order = index
                    option.save(update_fields=["display_order"])

                # Đánh dấu đáp án đúng theo vị trí trên biểu mẫu.
                if correct_index.isdigit():
                    selected_option = options_by_index.get(
                        int(correct_index)
                    )

                    if selected_option:
                        selected_option.set_correct(True)

                if action == "activate":
                    question.activate()

            messages.success(
                request,
                "Cập nhật câu hỏi thành công."
                if action == "draft"
                else "Cập nhật và kích hoạt câu hỏi thành công.",
            )
            return redirect("questions:list")

        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        except DatabaseError:
            messages.error(
                request,
                "Không thể cập nhật câu hỏi. Vui lòng thử lại.",
            )

    form_data = None

    if request.method == "POST":
        option_ids = request.POST.getlist("option_id")
        option_contents = request.POST.getlist("option_content")
        correct_option = request.POST.get("correct_option", "")

        form_options = []

        for index, option_content in enumerate(option_contents):
            option_id = (
                option_ids[index]
                if index < len(option_ids)
                else ""
            )

            form_options.append({
                "option_id": option_id,
                "content": option_content,
                "is_correct": correct_option == str(index),
            })

        form_data = {
            "content": request.POST.get("content", ""),
            "options": form_options,
        }

    return render(request, "questions/editor.html", {
        "question": question,
        "options": question.options.order_by("display_order"),
        "form_data": form_data,
        "page_heading": "Chỉnh sửa câu hỏi",
    })


def _own_question(request, question_id):
    # Câu hỏi của giảng viên khác trả 404 như các trang sửa câu hỏi.
    return get_object_or_404(Question, question_id=question_id, teacher=request.user)


def _back_to_list(request):
    """Quay lại đúng trang/bộ lọc đang xem (chỉ nhận đường dẫn của trang danh sách câu hỏi)."""
    back = request.POST.get("next", "")
    list_url = reverse("questions:list")
    return redirect(back if back.startswith(list_url) else list_url)


@role_required(Role.TEACHER)
@require_POST
def question_delete(request, question_id):
    """UC Manage Questions: xóa câu hỏi chưa dùng trong đề nào, có xác nhận ở giao diện."""
    question = _own_question(request, question_id)
    try:
        question.delete_unused()
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    else:
        messages.success(request, "Đã xóa câu hỏi.")
    return _back_to_list(request)


@role_required(Role.TEACHER)
@require_POST
def question_archive(request, question_id):
    """Lưu trữ: ngừng dùng câu hỏi cho đề mới, đề cũ và kết quả cũ giữ nguyên (BR-14)."""
    question = _own_question(request, question_id)
    try:
        question.archive()
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    else:
        messages.success(request, "Đã lưu trữ câu hỏi. Câu hỏi không còn được chọn vào đề mới.")
    return _back_to_list(request)


@role_required(Role.TEACHER)
@require_POST
def question_restore(request, question_id):
    """Khôi phục câu hỏi đã lưu trữ về Nháp."""
    question = _own_question(request, question_id)
    try:
        question.restore()
    except ValidationError as error:
        for text in error.messages:
            messages.error(request, text)
    else:
        messages.success(request, "Đã khôi phục câu hỏi về Nháp. Kiểm tra lại rồi lưu để dùng.")
    return _back_to_list(request)


IMPORT_SESSION_KEY = "question_import"


def _import_target_exam(request, teacher):
    """Đề nháp sẽ nhận các câu vừa nhập (khi mở từ trang chọn câu hỏi của đề), hoặc None."""
    exam_id = request.POST.get("exam") or request.GET.get("exam")
    if not exam_id:
        return None
    try:
        exam = teacher.manage_exam(int(exam_id))  # đề của người khác: PermissionDenied -> 403
    except (TypeError, ValueError):
        return None
    return exam if exam.status == ExamStatus.DRAFT else None


@role_required(Role.TEACHER)
def question_import(request):
    """S3-32: nhập câu hỏi từ Excel. Bước 1 tải file lên và xem trước, bước 2 xác nhận nhập."""
    from questions import importer

    teacher = request.user.as_role()
    exam = _import_target_exam(request, teacher)
    context = {"exam": exam, "max_rows": importer.MAX_ROWS, "default_points": "1"}

    if request.method == "POST" and request.POST.get("step") == "confirm":
        data = request.session.get(IMPORT_SESSION_KEY)
        if not data or not data.get("rows"):
            messages.error(request, "Phiên nhập đã hết hoặc không còn câu hợp lệ. Hãy tải file lên lại.")
            return redirect(request.get_full_path())
        add_to_exam = exam is not None and request.POST.get("add_to_exam") == "1"
        try:
            with transaction.atomic():
                created = teacher.import_questions(data["rows"])
                if add_to_exam:
                    points = (request.POST.get("points") or "").strip().replace(",", ".")
                    for question in created:
                        exam.add_question(question.pk, points)
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            context.update(data.get("preview", {}))
            return render(request, "questions/import.html", context)
        request.session.pop(IMPORT_SESSION_KEY, None)
        if add_to_exam:
            messages.success(request, f"Đã nhập {len(created)} câu hỏi và thêm vào đề '{exam.title}'.")
            return redirect("exams:questions", exam_id=exam.pk)
        messages.success(request, f"Đã nhập {len(created)} câu hỏi vào ngân hàng.")
        return redirect("questions:list")

    if request.method == "POST":
        upload = request.FILES.get("file")
        if upload is None:
            context["file_error"] = "Vui lòng chọn file Excel."
            return render(request, "questions/import.html", context)
        try:
            rows = importer.read_workbook(upload)
        except ValidationError as error:
            context["file_error"] = error.messages[0]
            return render(request, "questions/import.html", context)
        valid = [row for row in rows if row.valid]
        preview = {
            "file_name": upload.name,
            "rows": [
                {"row": r.row, "content": r.content, "option_count": len(r.options),
                 "correct": r.correct_letter, "errors": r.errors}
                for r in rows
            ],
            "valid_count": len(valid),
            "error_count": len(rows) - len(valid),
        }
        request.session[IMPORT_SESSION_KEY] = {"rows": [r.as_dict() for r in valid], "preview": preview}
        context.update(preview)
    return render(request, "questions/import.html", context)


@role_required(Role.TEACHER)
def question_import_template(request):
    """Tải file Excel mẫu để soạn câu hỏi."""
    from django.http import HttpResponse

    from questions.importer import build_template

    response = HttpResponse(
        build_template(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="mau-cau-hoi.xlsx"'
    return response
