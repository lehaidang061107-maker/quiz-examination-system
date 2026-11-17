"""Đề thi theo sơ đồ lớp: Exam, ExamQuestion, ExamParticipant (FR-06, FR-07, UC Create/Manage Exam)."""
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.db.models.functions import Now
from django.utils import timezone


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

    # ----- Sơ đồ lớp: Exam -----

    def apply_settings(self, data):
        """Gán tên, mô tả, thời lượng, lịch thi từ form; kiểm tra hợp lệ (UC Create Exam, luồng thay thế)."""
        self.check_draft()
        title = (data.get("title", self.title) or "").strip()
        duration = data.get("duration_minutes", self.duration_minutes)
        opens_at = data.get("opens_at", self.opens_at)
        closes_at = data.get("closes_at", self.closes_at)
        errors = {}
        if not title:
            errors["title"] = "Vui lòng nhập tên đề thi."
        if duration is not None and duration <= 0:
            errors["duration_minutes"] = "Thời lượng phải lớn hơn 0 phút."
        if opens_at and closes_at and closes_at <= opens_at:
            errors["closes_at"] = "Thời gian đóng phải sau thời gian mở."
        if errors:
            raise ValidationError(errors)
        self.title = title
        self.description = data.get("description", self.description)
        self.duration_minutes = duration
        self.opens_at = opens_at
        self.closes_at = closes_at

    def add_question(self, question_id, points):
        """addQuestion(id, points): thêm câu hỏi của chính giảng viên vào cuối đề nháp."""
        from questions.models import Question, QuestionStatus

        self.check_draft()
        points = _positive_points(points)
        question = Question.objects.filter(pk=question_id, teacher_id=self.teacher_id).first()
        if question is None:
            raise ValidationError("Câu hỏi không thuộc ngân hàng của bạn.")
        if question.status == QuestionStatus.ARCHIVED:
            raise ValidationError("Câu hỏi đã lưu trữ, không thể thêm vào đề mới.")
        with transaction.atomic():
            if self.exam_questions.filter(question=question).exists():
                raise ValidationError("Câu hỏi đã có trong đề.")
            last = self.exam_questions.aggregate(m=models.Max("position"))["m"] or 0
            return ExamQuestion.objects.create(exam=self, question=question, position=last + 1, points=points)

    def publish(self):
        """publish(): DRAFT -> PUBLISHED khi đủ điều kiện (BR-17). Sai thì báo rõ mục cần sửa."""
        from questions.models import QuestionStatus

        self.check_draft()
        errors = []
        if not (self.title or "").strip():
            errors.append("Đề chưa có tên.")
        items = list(self.exam_questions.select_related("question"))
        if not items:
            errors.append("Đề cần ít nhất 1 câu hỏi.")
        for item in items:
            question = item.question
            if question.status != QuestionStatus.ACTIVE or not question.validate_options():
                errors.append(f"Câu {item.position} chưa sẵn sàng (cần ACTIVE, đủ phương án và 1 đáp án đúng).")
        if self.opens_at and self.closes_at and self.closes_at <= self.opens_at:
            errors.append("Thời gian đóng phải sau thời gian mở.")
        if self.closes_at and self.closes_at <= timezone.now():
            errors.append("Thời gian đóng đã qua.")
        if errors:
            raise ValidationError(errors)
        self.status = ExamStatus.PUBLISHED
        self.save(update_fields=["status"])

    def can_start(self, student):
        """canStart(student): True nếu sinh viên được bắt đầu làm bài lúc này."""
        return self.cannot_start_reason(student) is None

    def cannot_start_reason(self, student):
        """Lý do không cho làm bài (để hiển thị ở danh sách bài thi), None nếu được làm."""
        now = timezone.now()
        if not student.is_active:
            return "Tài khoản không còn hoạt động."
        if not self.participants.filter(student=student, is_active=True).exists():
            return "Bạn không được giao đề thi này."
        if self.status != ExamStatus.PUBLISHED:
            return "Đề thi chưa mở hoặc đã đóng."
        if self.opens_at and now < self.opens_at:
            return "Chưa đến giờ làm bài."
        if self.closes_at and now >= self.closes_at:
            return "Đã hết thời gian làm bài."
        if self.submissions.filter(student=student).exists():
            return "Bạn đã làm đề thi này."
        return None

    def close(self):
        """Đóng đề PUBLISHED -> CLOSED; bài đang làm được nộp bằng đáp án đã lưu (BR-17, BR-18)."""
        from attempts.models import SubmissionStatus

        if self.status != ExamStatus.PUBLISHED:
            raise ValidationError("Chỉ đóng được đề đang phát hành.")
        now = timezone.now()
        self.status = ExamStatus.CLOSED
        self.save(update_fields=["status"])
        for submission in self.submissions.filter(status=SubmissionStatus.IN_PROGRESS):
            submission.auto_submit(at=now)

    def publish_results(self):
        """publishResults(): công bố điểm khi đề CLOSED và mọi bài đã chấm (BR-19)."""
        from attempts.models import SubmissionStatus

        if self.status != ExamStatus.CLOSED:
            raise ValidationError("Chỉ công bố điểm sau khi đã đóng đề.")
        pending = self.submissions.exclude(status=SubmissionStatus.GRADED).count()
        if pending:
            raise ValidationError(f"Còn {pending} bài chưa chấm xong, chưa thể công bố.")
        self.results_published = True
        self.save(update_fields=["results_published"])

    def check_draft(self):
        """Đề đã phát hành giữ nguyên nội dung, thứ tự, điểm (BR-14)."""
        if self.pk and self.status != ExamStatus.DRAFT:
            raise ValidationError("Đề đã phát hành, không thể sửa nội dung.")


def _positive_points(value):
    try:
        points = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError("Điểm phải là số.")
    if not points.is_finite() or points <= 0:
        raise ValidationError("Điểm phải lớn hơn 0.")
    return points


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

    # ----- Sơ đồ lớp: ExamQuestion -----

    def set_position(self, value):
        """setPosition(value): đổi thứ tự câu; câu đang ở vị trí đó đổi chỗ sang vị trí cũ."""
        self.exam.check_draft()
        if value <= 0:
            raise ValidationError("Vị trí phải lớn hơn 0.")
        old = self.position
        if value == old:
            return
        with transaction.atomic():
            other = ExamQuestion.objects.filter(exam_id=self.exam_id, position=value)
            # Dời tạm câu kia ra vị trí trống để không vi phạm uq_exam_questions_position.
            temp = (self.exam.exam_questions.aggregate(m=models.Max("position"))["m"] or 0) + 1
            moved = other.update(position=temp)
            ExamQuestion.objects.filter(pk=self.pk).update(position=value)
            if moved:
                ExamQuestion.objects.filter(exam_id=self.exam_id, position=temp).update(position=old)
        self.position = value

    def set_points(self, value):
        """setPoints(value): đặt điểm câu (> 0)."""
        self.exam.check_draft()
        self.points = _positive_points(value)
        ExamQuestion.objects.filter(pk=self.pk).update(points=self.points)


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

    # ----- Sơ đồ lớp: ExamParticipant -----

    def grant_access(self):
        """grantAccess(): cấp quyền dự thi cho Student ACTIVE khi đề DRAFT hoặc PUBLISHED chưa hết lịch (BR-18)."""
        from accounts.models import Role

        exam = self.exam
        if exam.status not in (ExamStatus.DRAFT, ExamStatus.PUBLISHED):
            raise ValidationError("Đề đã đóng, không thể cấp quyền mới.")
        if exam.closes_at and exam.closes_at <= timezone.now():
            raise ValidationError("Đề đã hết lịch thi, không thể cấp quyền mới.")
        if self.student.role != Role.STUDENT or not self.student.is_active:
            raise ValidationError(f"{self.student.full_name} không phải sinh viên đang hoạt động.")
        self.is_active = True
        self.save()

    def revoke_access(self):
        """revokeAccess(): thu hồi quyền, giữ bản ghi lịch sử. Đang làm bài thì nộp bằng đáp án đã lưu."""
        from attempts.models import SubmissionStatus

        if self.exam.status not in (ExamStatus.DRAFT, ExamStatus.PUBLISHED):
            raise ValidationError("Đề đã đóng, không thể thu hồi quyền.")
        now = timezone.now()
        ExamParticipant.objects.filter(pk=self.pk).update(is_active=False)
        self.is_active = False
        for submission in self.exam.submissions.filter(student_id=self.student_id, status=SubmissionStatus.IN_PROGRESS):
            submission.auto_submit(at=now)

    def can_participate(self):
        """canParticipate(): còn quyền dự thi và đề đang mở."""
        return bool(self.is_active) and self.exam.status == ExamStatus.PUBLISHED and self.student.is_active
