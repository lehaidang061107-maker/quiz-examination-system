from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class SubmissionStatus(models.TextChoices):
    IN_PROGRESS = "IN_PROGRESS", "Đang làm"
    SUBMITTED = "SUBMITTED", "Đã nộp"
    GRADED = "GRADED", "Đã chấm"


class Submission(models.Model):
    """Một lượt làm bài. Mỗi sinh viên chỉ có một lượt cho mỗi đề (BR-20)."""

    submission_id = models.BigAutoField(primary_key=True)
    # Khóa ngoại nhiều cột (exam_id, student_id) -> exam_participants: khai báo bằng SQL trong migration 0002.
    exam = models.ForeignKey("exams.Exam", on_delete=models.PROTECT, related_name="submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="submissions")
    attempt_no = models.IntegerField(db_default=1)
    status = models.CharField(
        max_length=15, choices=SubmissionStatus.choices, db_default=SubmissionStatus.IN_PROGRESS
    )
    started_at = models.DateTimeField(db_default=Now())
    deadline_at = models.DateTimeField(null=True, blank=True)
    last_saved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    version = models.IntegerField(db_default=0)  # chống ghi đè khi mở nhiều tab

    class Meta:
        db_table = "submissions"
        indexes = [
            models.Index(fields=["student", "exam", "status"], name="ix_sub_student_exam_status"),
            models.Index(
                fields=["deadline_at"], name="ix_sub_pending_deadline", condition=Q(status="IN_PROGRESS")
            ),
            models.Index(
                fields=["submitted_at"], name="ix_submissions_grading_queue", condition=Q(status="SUBMITTED")
            ),
        ]
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="uq_submissions_participant"),
            # Cho phép khóa ngoại nhiều cột từ submission_answers (submission_id, exam_id).
            models.UniqueConstraint(fields=["submission_id", "exam"], name="uq_submissions_exam"),
            models.CheckConstraint(condition=Q(attempt_no=1), name="ck_submissions_attempt"),
            models.CheckConstraint(condition=Q(version__gte=0), name="ck_submissions_version"),
            models.CheckConstraint(condition=Q(status__in=SubmissionStatus.values), name="ck_submissions_status"),
            models.CheckConstraint(
                condition=Q(status=SubmissionStatus.IN_PROGRESS, submitted_at__isnull=True)
                | Q(status__in=[SubmissionStatus.SUBMITTED, SubmissionStatus.GRADED], submitted_at__isnull=False),
                name="ck_submissions_status_time",
            ),
            models.CheckConstraint(
                condition=(Q(deadline_at__isnull=True) | Q(deadline_at__gte=F("started_at")))
                & (Q(last_saved_at__isnull=True) | Q(last_saved_at__gte=F("started_at")))
                & (Q(submitted_at__isnull=True) | Q(submitted_at__gte=F("started_at"))),
                name="ck_submissions_time",
            ),
        ]


class SubmissionAnswer(models.Model):
    """Đáp án sinh viên chọn cho một câu. selected_option=NULL nghĩa là bỏ chọn."""

    pk = models.CompositePrimaryKey("submission_id", "question_id")
    # Các khóa ngoại nhiều cột bảo đảm câu thuộc đề, đáp án thuộc câu: khai báo bằng SQL trong migration 0002.
    submission = models.ForeignKey(Submission, on_delete=models.PROTECT, related_name="answers")
    exam = models.ForeignKey("exams.Exam", on_delete=models.PROTECT, related_name="+")
    question = models.ForeignKey("questions.Question", on_delete=models.PROTECT, related_name="+")
    selected_option = models.ForeignKey(
        "questions.AnswerOption", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    saved_at = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "submission_answers"
        indexes = [
            models.Index(fields=["exam", "question"], name="ix_answers_exam_question"),
            models.Index(fields=["question", "selected_option"], name="ix_answers_question_option"),
        ]
