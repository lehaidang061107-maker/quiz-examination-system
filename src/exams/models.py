from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class ExamStatus(models.TextChoices):
    DRAFT = "DRAFT", "Nháp"
    PUBLISHED = "PUBLISHED", "Đã phát hành"
    CLOSED = "CLOSED", "Đã đóng"
    ARCHIVED = "ARCHIVED", "Lưu trữ"


class Exam(models.Model):
    exam_id = models.BigAutoField(primary_key=True)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exams")
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ExamStatus.choices, db_default=ExamStatus.DRAFT)
    duration_minutes = models.IntegerField(null=True, blank=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    results_published = models.BooleanField(db_default=False)
    created_at = models.DateTimeField(db_default=Now())
    updated_at = models.DateTimeField(db_default=Now())  # trigger cập nhật khi sửa

    class Meta:
        db_table = "exams"
        indexes = [models.Index(fields=["teacher", "status"], name="ix_exams_teacher_status")]
        constraints = [
            models.CheckConstraint(condition=Q(status__in=ExamStatus.values), name="ck_exams_status"),
            models.CheckConstraint(
                condition=Q(duration_minutes__isnull=True) | Q(duration_minutes__gt=0), name="ck_exams_duration"
            ),
            models.CheckConstraint(
                condition=Q(opens_at__isnull=True) | Q(closes_at__isnull=True) | Q(closes_at__gt=F("opens_at")),
                name="ck_exams_schedule",
            ),
            models.CheckConstraint(
                condition=Q(results_published=False) | Q(status__in=[ExamStatus.CLOSED, ExamStatus.ARCHIVED]),
                name="ck_exams_publication_status",
            ),
            # ck_exams_title dùng btrim(): khai báo bằng SQL trong migration 0002.
        ]

    def __str__(self):
        return self.title


class ExamQuestion(models.Model):
    """Câu hỏi trong đề: thứ tự và điểm."""

    pk = models.CompositePrimaryKey("exam_id", "question_id")
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="exam_questions")
    question = models.ForeignKey("questions.Question", on_delete=models.PROTECT, related_name="exam_questions")
    position = models.IntegerField()
    points = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "exam_questions"
        indexes = [models.Index(fields=["question"], name="ix_exam_questions_question")]
        constraints = [
            models.UniqueConstraint(fields=["exam", "position"], name="uq_exam_questions_position"),
            models.CheckConstraint(condition=Q(position__gt=0), name="ck_exam_questions_position"),
            # ck_exam_questions_points (chặn số âm và NaN): khai báo bằng SQL trong migration 0002.
        ]


class ExamParticipant(models.Model):
    """Sinh viên được giao đề. Thu hồi quyền bằng is_active=False để giữ lịch sử."""

    pk = models.CompositePrimaryKey("exam_id", "student_id")
    exam = models.ForeignKey(Exam, on_delete=models.PROTECT, related_name="participants")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="exam_assignments")
    assigned_at = models.DateTimeField(db_default=Now())
    is_active = models.BooleanField(db_default=True)

    class Meta:
        db_table = "exam_participants"
        indexes = [
            models.Index(fields=["student", "is_active", "exam"], name="ix_part_student_active_exam"),
        ]
