from django.conf import settings
from django.db import models
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
