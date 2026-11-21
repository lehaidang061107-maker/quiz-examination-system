"""Kết quả theo sơ đồ lớp: Result (FR-11, FR-12, FR-13, UC Automatic Grading, View Exam Results)."""
from decimal import Decimal

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now


class Result(models.Model):
    """Kết quả chấm của một lượt làm bài; mỗi lượt chỉ có một kết quả."""

    result_id = models.BigAutoField(primary_key=True)
    submission = models.ForeignKey("attempts.Submission", on_delete=models.PROTECT, related_name="results")
    score = models.DecimalField(max_digits=12, decimal_places=2)
    max_score = models.DecimalField(max_digits=12, decimal_places=2)
    correct_count = models.IntegerField()
    total_questions = models.IntegerField()
    graded_at = models.DateTimeField(db_default=Now())

    class Meta:
        db_table = "results"
        constraints = [
            models.UniqueConstraint(fields=["submission"], name="uq_results_submission"),
            models.CheckConstraint(
                condition=Q(total_questions__gt=0, correct_count__gte=0, correct_count__lte=F("total_questions")),
                name="ck_results_counts",
            ),
            # ck_results_score (0 <= score <= max_score, chặn NaN): khai báo bằng SQL trong migration 0002.
        ]

    # ----- Sơ đồ lớp: Result -----

    def calculate(self):
        """calculate(): tính điểm từ đáp án đã lưu. Câu đúng được điểm của câu trong đề;
        câu sai hoặc bỏ trống được 0 (UC Automatic Grading, bước 4)."""
        from questions.models import AnswerOption

        submission = self.submission
        items = list(submission.exam.exam_questions.all())
        chosen = dict(submission.answers.values_list("question_id", "selected_option_id"))
        correct_option = dict(
            AnswerOption.objects.filter(question_id__in=[i.question_id for i in items], is_correct=True)
            .values_list("question_id", "option_id")
        )
        right = [i for i in items if chosen.get(i.question_id) is not None
                 and chosen[i.question_id] == correct_option.get(i.question_id)]
        self.score = sum((i.points for i in right), Decimal("0"))
        self.max_score = sum((i.points for i in items), Decimal("0"))
        self.correct_count = len(right)
        self.total_questions = len(items)

    def can_view(self, user):
        """canView(user): Teacher xem kết quả đề mình phụ trách; Student chỉ xem bài của mình
        sau khi đề công bố điểm (BR-10, BR-19)."""
        from accounts.models import Role

        exam = self.submission.exam
        if not user.is_active:
            return False
        if user.role == Role.TEACHER:
            return exam.teacher_id == user.pk
        if user.role == Role.STUDENT:
            return self.submission.student_id == user.pk and exam.results_published
        return False

    # ----- Chi tiết hiển thị (UC View Exam Results, bước 4) -----

    @property
    def answered_count(self):
        """Số câu đã chọn đáp án. Dùng số đếm sẵn nếu truy vấn đã annotate `answered_total`."""
        cached = getattr(self, "answered_total", None)
        if cached is not None:
            return cached
        return self.submission.answers.filter(selected_option__isnull=False).count()

    @property
    def wrong_count(self):
        return self.answered_count - self.correct_count

    @property
    def blank_count(self):
        return self.total_questions - self.answered_count

    @property
    def completion_time(self):
        """Thời gian làm bài = lúc nộp - lúc bắt đầu (bài tự nộp đã ghi submitted_at = hạn nộp)."""
        submission = self.submission
        return submission.submitted_at - submission.started_at
