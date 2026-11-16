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
