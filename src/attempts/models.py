"""Làm bài theo sơ đồ lớp: Submission, SubmissionAnswer (FR-09, FR-10, UC Take/Submit Exam)."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import F, Q
from django.db.models.functions import Now
from django.utils import timezone

logger = logging.getLogger(__name__)
# NFR-MAI-03, NFR-SEC-10: nhật ký nộp bài (ai, lượt nào, nộp tay hay tự nộp và lý do). Không ghi đáp án.
audit_log = logging.getLogger("attempts.audit")

AUTO_SUBMIT_REASONS = {
    "expired": "hết giờ",
    "exam_closed": "đề đã đóng",
    "revoked": "bị thu hồi quyền",
    "account_locked": "tài khoản bị khóa",
}


class StaleVersionError(ValidationError):
    """Bài đã được lưu ở tab khác: giao diện cần tải lại trạng thái mới (BR-20)."""


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

    @classmethod
    def start(cls, exam, student):
        """Tạo lượt làm bài. Hạn nộp = giờ bắt đầu + thời lượng, không quá giờ đóng đề (BR-21)."""
        now = timezone.now()
        deadlines = []
        if exam.duration_minutes:
            deadlines.append(now + timedelta(minutes=exam.duration_minutes))
        if exam.closes_at:
            deadlines.append(exam.closes_at)
        try:
            with transaction.atomic():
                return cls.objects.create(
                    exam=exam, student=student, started_at=now, deadline_at=min(deadlines, default=None)
                )
        except IntegrityError:
            # Hai tab bấm Bắt đầu cùng lúc: uq_submissions_participant chỉ cho một lượt, dùng lại lượt đó.
            return cls.objects.get(exam=exam, student=student)

    # ----- Sơ đồ lớp: Submission -----

    def is_editable(self):
        """isEditable(): còn sửa đáp án được (đang làm và chưa hết hạn theo giờ máy chủ)."""
        if self.status != SubmissionStatus.IN_PROGRESS:
            return False
        return self.deadline_at is None or timezone.now() < self.deadline_at

    def save_answer(self, question_id, option_id, version):
        """saveAnswer(data): lưu một đáp án (option_id=None là bỏ chọn); trả về version mới.

        Chỉ ghi khi version gửi lên khớp version hiện tại, rồi tăng version. Tab cũ gửi version
        cũ sẽ nhận StaleVersionError để tải lại (BR-20, UC Take Exam).
        """
        from questions.models import AnswerOption

        with transaction.atomic():
            current = Submission.objects.select_for_update().get(pk=self.pk)
            if not current.is_editable():
                raise ValidationError("Bài đã nộp hoặc đã hết giờ, không thể sửa đáp án.")
            if int(version) != current.version:
                raise StaleVersionError("Bài làm đã được cập nhật ở nơi khác. Vui lòng tải lại trang.")
            if not current.exam.exam_questions.filter(question_id=question_id).exists():
                raise ValidationError("Câu hỏi không thuộc đề thi này.")
            if option_id is not None and not AnswerOption.objects.filter(pk=option_id, question_id=question_id).exists():
                raise ValidationError("Phương án không thuộc câu hỏi này.")
            answer = SubmissionAnswer.objects.filter(submission=current, question_id=question_id).first()
            answer = answer or SubmissionAnswer(submission=current, exam_id=current.exam_id, question_id=question_id)
            if option_id is None:
                answer.clear_selection()
            else:
                answer.select_option(option_id)
            now = timezone.now()
            current.version += 1
            current.last_saved_at = now
            current.save(update_fields=["version", "last_saved_at"])
        self.version, self.last_saved_at = current.version, current.last_saved_at
        return current.version

    def submit(self):
        """submit(): Student nộp bài. Trả về True nếu lần này ghi nhận, False nếu bài đã nộp trước đó
        (gọi lại không tạo bản nộp trùng, NFR-REL-03). Nộp xong thì chấm luôn (Submit include Grading)."""
        return self._finalize(effective_at=None)

    def auto_submit(self, at=None, reason="expired"):
        """autoSubmit(): tự nộp khi hết giờ, khóa tài khoản, thu hồi quyền hoặc đóng đề.
        submitted_at là thời điểm hiệu lực (mặc định là hạn nộp), chỉ dùng đáp án đã lưu (BR-21).
        reason: một khóa của AUTO_SUBMIT_REASONS, ghi vào nhật ký."""
        return self._finalize(effective_at=at or self.deadline_at or timezone.now(), reason=reason)

    def _finalize(self, effective_at, reason=None):
        with transaction.atomic():
            current = Submission.objects.select_for_update().get(pk=self.pk)
            if current.status != SubmissionStatus.IN_PROGRESS:
                self.refresh_from_db()
                return False
            now = timezone.now()
            if effective_at is None:  # nộp tay: quá hạn thì tính tại hạn nộp
                late = current.deadline_at is not None and now >= current.deadline_at
                effective_at = current.deadline_at if late else now
            current.status = SubmissionStatus.SUBMITTED
            current.submitted_at = max(effective_at, current.started_at)
            current.save(update_fields=["status", "submitted_at"])
        self.refresh_from_db()
        how = "nộp tay" if reason is None else f"tự nộp ({AUTO_SUBMIT_REASONS.get(reason, reason)})"
        audit_log.info(
            "nộp bài | submission_id=%s | student_id=%s | exam_id=%s | %s | submitted_at=%s",
            self.pk, self.student_id, self.exam_id, how, self.submitted_at.isoformat(),
        )
        try:
            self.grade()
        except Exception:
            # Chấm lỗi không làm mất bài đã nộp: giữ SUBMITTED để chấm lại sau (UC Submit Exam).
            logger.exception("Chấm bài %s thất bại, giữ SUBMITTED để thử lại", self.pk)
        return True

    def grade(self):
        """grade(): chấm bài SUBMITTED, lưu Result và chuyển GRADED trong cùng giao dịch (UC Automatic Grading).
        Bài đã GRADED thì trả kết quả có sẵn, không tạo kết quả thứ hai."""
        from results.models import Result

        with transaction.atomic():
            current = Submission.objects.select_for_update().get(pk=self.pk)
            if current.status == SubmissionStatus.GRADED:
                return Result.objects.get(submission=current)
            if current.status != SubmissionStatus.SUBMITTED:
                raise ValidationError("Bài chưa nộp, chưa thể chấm.")
            result = Result(submission=current)
            result.calculate()
            result.save()
            current.status = SubmissionStatus.GRADED
            current.save(update_fields=["status"])
        self.refresh_from_db()
        return result


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

    # ----- Sơ đồ lớp: SubmissionAnswer -----
    # Chỉ gọi qua Submission.save_answer() để luôn kiểm tra hạn nộp và version.

    def select_option(self, option_id):
        """selectOption(id): chọn một phương án (mỗi câu tối đa một phương án, BR-13)."""
        self.selected_option_id = option_id
        self.saved_at = timezone.now()
        self.save()

    def clear_selection(self):
        """clearSelection(): bỏ chọn, câu được tính là chưa trả lời."""
        self.select_option(None)
