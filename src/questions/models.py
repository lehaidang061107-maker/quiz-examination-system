"""Ngân hàng câu hỏi theo sơ đồ lớp: Question, AnswerOption (FR-05, UC Manage Questions)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.functions import Now


class QuestionType(models.TextChoices):
    SINGLE_CHOICE = "SINGLE_CHOICE", "Một đáp án đúng"


class QuestionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Nháp"
    ACTIVE = "ACTIVE", "Đang dùng"
    ARCHIVED = "ARCHIVED", "Lưu trữ"


class Question(models.Model):
    question_id = models.BigAutoField(primary_key=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="questions")
    content = models.TextField(null=True, blank=True)
    question_type = models.CharField(
        max_length=20, choices=QuestionType.choices, db_default=QuestionType.SINGLE_CHOICE
    )
    status = models.CharField(max_length=10, choices=QuestionStatus.choices, db_default=QuestionStatus.DRAFT)
    created_at = models.DateTimeField(db_default=Now())
    updated_at = models.DateTimeField(db_default=Now())  # trigger cập nhật khi sửa

    class Meta:
        db_table = "questions"
        indexes = [models.Index(fields=["teacher", "status"], name="ix_questions_teacher_status")]
        constraints = [
            models.CheckConstraint(condition=models.Q(question_type__in=QuestionType.values), name="ck_questions_type"),
            models.CheckConstraint(condition=models.Q(status__in=QuestionStatus.values), name="ck_questions_status"),
            # ck_questions_active_content dùng btrim(): khai báo bằng SQL trong migration 0002.
        ]

    def __str__(self):
        return (self.content or "(câu nháp)")[:60]

    # ----- Sơ đồ lớp: Question -----

    def add_option(self, data):
        """addOption(data): thêm phương án. data gồm content, is_correct (mặc định False)."""
        self.check_editable()
        content = (data.get("content") or "").strip()
        if not content:
            raise ValidationError("Nội dung phương án không được để trống.")
        with transaction.atomic():
            last = self.options.aggregate(m=models.Max("display_order"))["m"] or 0
            option = AnswerOption.objects.create(question=self, content=content, display_order=last + 1)
            if data.get("is_correct"):
                option.set_correct(True)
        return option

    def validate_options(self):
        """validateOptions(): True nếu câu hỏi đủ điều kiện ACTIVE (BR-07, BR-13):
        nội dung không trống, ít nhất 2 phương án và đúng 1 đáp án đúng."""
        return not self.option_errors()

    def option_errors(self):
        """Danh sách lý do câu hỏi chưa đủ điều kiện, để giao diện báo cho giảng viên."""
        errors = []
        if not (self.content or "").strip():
            errors.append("Câu hỏi chưa có nội dung.")
        options = list(self.options.all())
        if len(options) < 2:
            errors.append("Câu hỏi cần ít nhất 2 phương án.")
        correct = sum(o.is_correct for o in options)
        if correct != 1:
            errors.append("Câu hỏi phải có đúng 1 đáp án đúng." if correct else "Chưa chọn đáp án đúng.")
        return errors

    def activate(self):
        """Lưu và sẵn sàng: chuyển DRAFT -> ACTIVE khi hợp lệ (UC Manage Questions, bước 4)."""
        errors = self.option_errors()
        if errors:
            raise ValidationError(errors)
        self.status = QuestionStatus.ACTIVE
        self.save(update_fields=["status"])

    def create_revision(self):
        """createRevision(): tạo bản sao DRAFT để sửa câu đã dùng trong đề phát hành (BR-14).
        Đề cũ vẫn giữ câu cũ nên điểm và kết quả cũ không đổi."""
        with transaction.atomic():
            copy = Question.objects.create(teacher_id=self.teacher_id, content=self.content)
            AnswerOption.objects.bulk_create(
                AnswerOption(question=copy, content=o.content, display_order=o.display_order, is_correct=o.is_correct)
                for o in self.options.all()
            )
        return copy

    def archive(self):
        """archive(): ngừng dùng câu hỏi cho đề mới; lịch sử vẫn đọc được."""
        if self.status == QuestionStatus.ARCHIVED:
            raise ValidationError("Câu hỏi đã được lưu trữ trước đó.")
        self.status = QuestionStatus.ARCHIVED
        self.save(update_fields=["status"])

    def restore(self):
        """Khôi phục câu đã lưu trữ về DRAFT; muốn dùng lại cho đề mới thì kiểm tra rồi chuyển ACTIVE."""
        if self.status != QuestionStatus.ARCHIVED:
            raise ValidationError("Chỉ khôi phục được câu hỏi đang lưu trữ.")
        self.status = QuestionStatus.DRAFT
        self.save(update_fields=["status"])

    def delete_unused(self):
        """Xóa hẳn câu hỏi chưa từng được chọn vào đề nào (UC Manage Questions, bước 2-3).

        Câu đã dùng trong đề phát hành thì từ chối xóa để giữ đề và kết quả cũ (BR-14), chỉ lưu trữ được.
        Câu đang nằm trong đề nháp thì phải bỏ khỏi đề trước.
        """
        from exams.models import ExamStatus

        with transaction.atomic():
            Question.objects.select_for_update().filter(pk=self.pk).first()  # chặn thêm vào đề cùng lúc
            used = self.exam_questions.select_related("exam")
            if used.exclude(exam__status=ExamStatus.DRAFT).exists():
                raise ValidationError(
                    "Câu hỏi đã dùng trong đề đã phát hành nên không xóa được. "
                    "Hãy lưu trữ để ngừng dùng cho đề mới."
                )
            drafts = [item.exam.title for item in used]
            if drafts:
                raise ValidationError(
                    f"Câu hỏi đang nằm trong đề nháp: {', '.join(drafts)}. Hãy bỏ câu hỏi khỏi đề trước khi xóa."
                )
            self.options.all().delete()
            self.delete()

    def is_locked(self):
        """True nếu câu đã nằm trong đề đã phát hành: không được sửa trực tiếp (BR-14)."""
        from exams.models import ExamStatus

        return self.exam_questions.exclude(exam__status=ExamStatus.DRAFT).exists()

    def check_editable(self):
        if self.is_locked():
            raise ValidationError("Câu hỏi đã dùng trong đề đã phát hành. Hãy tạo phiên bản mới để sửa.")


class AnswerOption(models.Model):
    option_id = models.BigAutoField(primary_key=True)
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="options")
    content = models.TextField()
    display_order = models.IntegerField()
    is_correct = models.BooleanField(db_default=False)

    class Meta:
        db_table = "answer_options"
        constraints = [
            models.UniqueConstraint(fields=["question", "display_order"], name="uq_options_display_order"),
            # Cho phép khóa ngoại nhiều cột từ submission_answers (question_id, selected_option_id).
            models.UniqueConstraint(fields=["question", "option_id"], name="uq_options_question_option"),
            models.CheckConstraint(condition=models.Q(display_order__gt=0), name="ck_options_display_order"),
            # ck_options_content dùng btrim(): khai báo bằng SQL trong migration 0002.
        ]

    def __str__(self):
        return self.content[:60]

    # ----- Sơ đồ lớp: AnswerOption -----

    def update_content(self, text):
        """updateContent(text): sửa nội dung phương án."""
        self.question.check_editable()
        text = (text or "").strip()
        if not text:
            raise ValidationError("Nội dung phương án không được để trống.")
        self.content = text
        self.save(update_fields=["content"])

    def set_correct(self, flag):
        """setCorrect(flag): đặt đáp án đúng. Câu một lựa chọn nên chọn phương án này
        thì các phương án khác tự bỏ đúng (BR-13)."""
        self.question.check_editable()
        if not flag and self.is_correct and self.question.status == QuestionStatus.ACTIVE:
            raise ValidationError("Câu hỏi đang dùng phải có 1 đáp án đúng. Hãy chọn đáp án đúng khác.")
        with transaction.atomic():
            if flag:
                self.question.options.exclude(pk=self.pk).update(is_correct=False)
            self.is_correct = flag
            self.save(update_fields=["is_correct"])
