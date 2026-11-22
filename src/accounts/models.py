"""Model tài khoản theo sơ đồ lớp (mục 5 tài liệu đặc tả).

User là lớp cha; Admin, Teacher, Student kế thừa User (proxy model: cùng bảng `users`,
phân biệt bằng cột role). Mỗi lớp có các phương thức đúng như sơ đồ lớp, tên viết theo
kiểu Python: viewAvailableExams() -> view_available_exams().

Các phương thức báo lỗi nghiệp vụ bằng ValidationError (thông báo tiếng Việt, view hiển thị
cho người dùng) và lỗi sai quyền bằng PermissionDenied.
"""
import copy
import logging
from datetime import timedelta

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.db.models import Count, Q
from django.db.models.functions import Now
from django.utils import timezone

LOGIN_MAX_FAILS = 5  # NFR-SEC-07, BR-23
LOGIN_LOCK_TIME = timedelta(minutes=15)

# NFR-MAI-03, NFR-SEC-10: nhật ký đăng nhập và thay đổi tài khoản. Không ghi mật khẩu hay cookie phiên.
audit_log = logging.getLogger("accounts.audit")


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "-") if request is not None else "-"


def _log_text(value, limit=254):
    """Chữ người dùng gõ (email) đưa vào nhật ký: bỏ ký tự xuống dòng để không giả được dòng log khác."""
    return "".join(ch if ch.isprintable() else "?" for ch in str(value or ""))[:limit]


class Role(models.TextChoices):
    ADMIN = "ADMIN", "Quản trị viên"
    TEACHER = "TEACHER", "Giảng viên"
    STUDENT = "STUDENT", "Sinh viên"


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Hoạt động"
    LOCKED = "LOCKED", "Bị khóa"
    DELETED = "DELETED", "Ngừng sử dụng"


def normalize_email(email):
    """Bỏ khoảng trắng đầu/cuối và đổi chữ thường (ràng buộc ck_users_email_normalized)."""
    return (email or "").strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, *, full_name, role=Role.STUDENT, **extra):
        user = self.model(email=normalize_email(email), full_name=full_name.strip(), role=role, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("full_name", "Quản trị viên")
        return self.create_user(email, password, **extra)

    def get_by_natural_key(self, email):
        return self.get(email=normalize_email(email))


class User(AbstractBaseUser):
    """Tài khoản: mỗi người đúng một vai trò (BR-12). Lưu ở bảng `users`."""

    user_id = models.BigAutoField(primary_key=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    password = models.CharField(max_length=128, db_column="password_hash")
    role = models.CharField(max_length=10, choices=Role.choices)
    status = models.CharField(max_length=10, choices=UserStatus.choices, db_default=UserStatus.ACTIVE)
    # Khóa tạm do đăng nhập sai (NFR-SEC-07, BR-23); khác với status=LOCKED do Admin đặt.
    failed_login_count = models.IntegerField(db_default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(db_default=Now())
    updated_at = models.DateTimeField(db_default=Now())  # trigger cập nhật khi sửa

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(fields=["email"], name="uq_users_email"),
            models.CheckConstraint(condition=models.Q(role__in=Role.values), name="ck_users_role"),
            models.CheckConstraint(condition=models.Q(status__in=UserStatus.values), name="ck_users_status"),
            models.CheckConstraint(condition=models.Q(failed_login_count__gte=0), name="ck_users_failed_login_count"),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    # ----- Sơ đồ lớp: User -----

    @property
    def is_active(self):
        """isActive(): chỉ tài khoản ACTIVE được dùng hệ thống.

        Django kiểm tra is_active mỗi lần nạp user từ phiên, nên tài khoản bị khóa/xóa
        tự mất phiên ngay (BR-22).
        """
        return self.status == UserStatus.ACTIVE

    @classmethod
    def login(cls, request, email, password):
        """login(email, password): đăng nhập, trả về True khi thành công (FR-02, UC Login).

        Thất bại thì báo ValidationError kèm thông báo cho người dùng. Sai mật khẩu 5 lần
        liên tiếp thì khóa tạm 15 phút; đăng nhập đúng thì đặt lại bộ đếm (BR-23).
        """
        wrong = "Email hoặc mật khẩu không đúng."
        error = None
        reason = None  # lý do thất bại ghi vào nhật ký (không lộ cho người dùng)
        with transaction.atomic():
            user = cls.objects.select_for_update().filter(email=normalize_email(email)).first()
            now = timezone.now()
            if user is None:
                error, reason = wrong, "email không tồn tại"
            elif user.locked_until and user.locked_until > now:
                minutes = int((user.locked_until - now).total_seconds() // 60) + 1
                error = f"Bạn đã nhập sai {LOGIN_MAX_FAILS} lần. Vui lòng thử lại sau {minutes} phút."
                reason = "đang bị khóa tạm do nhập sai"
            elif not user.check_password(password):
                user.failed_login_count += 1
                reason = f"sai mật khẩu lần {user.failed_login_count}"
                if user.failed_login_count >= LOGIN_MAX_FAILS:
                    user.failed_login_count = 0
                    user.locked_until = now + LOGIN_LOCK_TIME
                    reason += f", khóa tạm {int(LOGIN_LOCK_TIME.total_seconds() // 60)} phút"
                user.save(update_fields=["failed_login_count", "locked_until"])
                error = wrong
            elif not user.is_active:
                error = "Tài khoản đã bị khóa hoặc ngừng sử dụng. Vui lòng liên hệ quản trị viên."
                reason = f"tài khoản {user.status}"
            else:
                user.failed_login_count = 0
                user.locked_until = None
                user.save(update_fields=["failed_login_count", "locked_until"])
        # Báo lỗi sau khi giao dịch đã lưu bộ đếm sai (báo lỗi trong giao dịch sẽ hoàn tác bộ đếm).
        if error:
            audit_log.warning(
                "đăng nhập thất bại | email=%s | user_id=%s | %s | ip=%s",
                _log_text(normalize_email(email)), user.pk if user else "-", reason, _client_ip(request),
            )
            raise ValidationError(error)
        # Django đổi mã phiên sau đăng nhập (NFR-SEC-08).
        auth_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        audit_log.info("đăng nhập | user_id=%s (%s) | %s | ip=%s", user.pk, user.email, user.role, _client_ip(request))
        return True

    def logout(self, request):
        """logout(): hủy phiên hiện tại (FR-03)."""
        audit_log.info("đăng xuất | user_id=%s (%s) | ip=%s", self.pk, self.email, _client_ip(request))
        auth_logout(request)

    def as_role(self):
        """Trả về đúng lớp con theo vai trò, ví dụ request.user.as_role() -> Teacher."""
        cls = {Role.ADMIN: Admin, Role.TEACHER: Teacher, Role.STUDENT: Student}[self.role]
        if isinstance(self, cls):
            return self
        user = copy.copy(self)
        user.__class__ = cls  # proxy dùng chung bảng nên đổi lớp là đủ, không cần truy vấn lại
        return user

    @property
    def is_staff(self):
        return self.is_active and self.role == Role.ADMIN

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff


class RoleManager(UserManager):
    """Chỉ lấy tài khoản của một vai trò, ví dụ Teacher.objects.all() chỉ có giảng viên."""

    use_in_migrations = False

    def __init__(self, role):
        super().__init__()
        self.role = role

    def get_queryset(self):
        return super().get_queryset().filter(role=self.role)

    def deconstruct(self):
        return False, "accounts.models.RoleManager", None, (self.role,), {}


class Admin(User):
    """Quản trị viên: quản lý tài khoản (FR-04, UC Manage User Accounts)."""

    objects = RoleManager(Role.ADMIN)

    class Meta:
        proxy = True
        verbose_name = "Quản trị viên"

    def create_user(self, data):
        """createUser(data): tạo tài khoản mới. data gồm full_name, email, password, role."""
        full_name = (data.get("full_name") or "").strip()
        email = normalize_email(data.get("email"))
        password = data.get("password") or ""
        role = data.get("role")
        errors = {}
        if not full_name:
            errors["full_name"] = "Vui lòng nhập họ tên."
        if not email:
            errors["email"] = "Vui lòng nhập email."
        elif User.objects.filter(email=email).exists():
            errors["email"] = "Email đã được sử dụng."
        if role not in Role.values:
            errors["role"] = "Vai trò không hợp lệ."
        try:
            validate_password(password)
        except ValidationError as exc:
            errors["password"] = exc.messages
        if errors:
            raise ValidationError(errors)
        user = User.objects.create_user(email, password, full_name=full_name, role=role)
        audit_log.info("tạo tài khoản | admin_id=%s | user_id=%s (%s) | %s", self.pk, user.pk, user.email, role)
        return user

    def update_user(self, user_id, data):
        """updateUser(id, data): sửa họ tên, email, vai trò (BR-22)."""
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            before = {"full_name": user.full_name, "email": user.email, "role": user.role}
            if "full_name" in data:
                if not (data["full_name"] or "").strip():
                    raise ValidationError({"full_name": "Vui lòng nhập họ tên."})
                user.full_name = data["full_name"].strip()
            if "email" in data:
                email = normalize_email(data["email"])
                if not email:
                    raise ValidationError({"email": "Vui lòng nhập email."})
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    raise ValidationError({"email": "Email đã được sử dụng."})
                user.email = email
            new_role = data.get("role", user.role)
            if new_role != user.role:
                if new_role not in Role.values:
                    raise ValidationError({"role": "Vai trò không hợp lệ."})
                self._check_not_last_admin(user)
                if _has_business_data(user):
                    raise ValidationError(
                        "Tài khoản đã có dữ liệu thi/câu hỏi nên không đổi được vai trò. Hãy khóa hoặc ngừng sử dụng."
                    )
                user.role = new_role
            user.save()
        changed = [field for field, old in before.items() if getattr(user, field) != old]
        if changed:
            role_note = f" ({before['role']} -> {user.role})" if "role" in changed else ""
            audit_log.info(
                "sửa tài khoản | admin_id=%s | user_id=%s (%s) | đổi %s%s",
                self.pk, user.pk, user.email, ", ".join(changed), role_note,
            )
        return user

    def lock_user(self, user_id):
        """lockUser(id): Admin khóa tài khoản (status=LOCKED); phiên của người đó mất ngay."""
        self._change_status(user_id, UserStatus.LOCKED, allowed_from=[UserStatus.ACTIVE],
                            wrong_status="Chỉ khóa được tài khoản đang hoạt động.")

    def unlock_user(self, user_id):
        """Mở khóa tài khoản Admin đã khóa (LOCKED -> ACTIVE), xóa luôn khóa tạm do nhập sai mật khẩu."""
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            if user.status != UserStatus.LOCKED:
                raise ValidationError("Chỉ mở khóa được tài khoản đang bị khóa.")
            user.status = UserStatus.ACTIVE
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["status", "failed_login_count", "locked_until"])
        audit_log.info("mở khóa tài khoản | admin_id=%s | user_id=%s (%s)", self.pk, user.pk, user.email)
        return user

    def delete_user(self, user_id):
        """deleteUser(id): xóa nghiệp vụ (status=DELETED), giữ dữ liệu lịch sử (BR-15)."""
        self._change_status(user_id, UserStatus.DELETED, allowed_from=[UserStatus.ACTIVE, UserStatus.LOCKED],
                            wrong_status="Tài khoản đã ngừng sử dụng.")

    def _change_status(self, user_id, status, allowed_from, wrong_status):
        from attempts.models import SubmissionStatus

        if user_id == self.pk:
            raise ValidationError("Không thể khóa hoặc xóa chính tài khoản bạn đang dùng.")
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user_id)
            if user.status not in allowed_from:
                raise ValidationError(wrong_status)
            self._check_not_last_admin(user)
            user.status = status
            user.save(update_fields=["status"])
            # BR-18: bài đang làm được nộp bằng các đáp án đã lưu, tính tại thời điểm khóa.
            in_progress = list(user.submissions.filter(status=SubmissionStatus.IN_PROGRESS))
        action = "khóa tài khoản" if status == UserStatus.LOCKED else "xóa tài khoản (ngừng sử dụng)"
        audit_log.info(
            "%s | admin_id=%s | user_id=%s (%s) | tự nộp %s bài đang làm",
            action, self.pk, user.pk, user.email, len(in_progress),
        )
        for submission in in_progress:
            submission.auto_submit(at=timezone.now(), reason="account_locked")

    @staticmethod
    def _check_not_last_admin(user):
        """Không khóa/xóa/hạ quyền Admin ACTIVE cuối cùng (BR-22)."""
        if user.role != Role.ADMIN or user.status != UserStatus.ACTIVE:
            return
        others = (
            User.objects.select_for_update()
            .filter(role=Role.ADMIN, status=UserStatus.ACTIVE)
            .exclude(pk=user.pk)
        )
        if not others.exists():
            raise ValidationError("Không thể thực hiện với quản trị viên đang hoạt động cuối cùng.")


class Teacher(User):
    """Giảng viên: quản lý câu hỏi, đề thi, phân công và xem kết quả (FR-05, 06, 07, 13)."""

    objects = RoleManager(Role.TEACHER)

    class Meta:
        proxy = True
        verbose_name = "Giảng viên"

    def manage_questions(self):
        """manageQuestions(): các câu hỏi thuộc giảng viên này (ngân hàng câu hỏi riêng)."""
        return self.questions.all().order_by("-updated_at")

    def create_exam(self, data):
        """createExam(data): tạo đề nháp DRAFT. data gồm title, description, duration_minutes,
        opens_at, closes_at (đều có thể bỏ trống trừ title)."""
        from exams.models import Exam

        exam = Exam(teacher=self)
        exam.apply_settings(data)
        exam.save()
        return exam

    def manage_exam(self, exam_id):
        """manageExam(id): lấy đề của chính giảng viên; đề của người khác thì từ chối."""
        from exams.models import Exam

        try:
            return Exam.objects.get(pk=exam_id, teacher=self)
        except Exam.DoesNotExist:
            raise PermissionDenied("Bạn không phụ trách đề thi này.")

    def assign_students(self, exam_id, student_ids):
        """assignStudents(id, ids): cấp quyền dự thi cho danh sách sinh viên (BR-18)."""
        from exams.models import ExamParticipant

        exam = self.manage_exam(exam_id)
        participants = []
        with transaction.atomic():
            for student_id in student_ids:
                participant = ExamParticipant.objects.filter(exam=exam, student_id=student_id).first()
                participant = participant or ExamParticipant(exam=exam, student_id=student_id)
                participant.grant_access()
                participants.append(participant)
        return participants

    def view_results(self, exam_id, student_ids=None):
        """viewResults(id): kết quả các bài của đề mình phụ trách (Teacher xem kể cả chưa công bố).
        student_ids: chỉ lấy kết quả của các sinh viên này (trang kết quả phân trang)."""
        from results.models import Result

        exam = self.manage_exam(exam_id)
        results = Result.objects.filter(submission__exam=exam)
        if student_ids is not None:
            results = results.filter(submission__student_id__in=student_ids)
        return list(
            results
            .select_related("submission__student")
            .annotate(
                answered_total=Count(
                    "submission__answers", filter=Q(submission__answers__selected_option__isnull=False)
                )
            )
            .order_by("submission__student__full_name")
        )


class Student(User):
    """Sinh viên: xem đề được giao, làm bài, nộp bài, xem kết quả (FR-08 -> FR-13)."""

    objects = RoleManager(Role.STUDENT)

    class Meta:
        proxy = True
        verbose_name = "Sinh viên"

    def view_available_exams(self):
        """viewAvailableExams(): các đề sinh viên đang được giao (không gồm đề nháp)."""
        from exams.models import Exam, ExamStatus

        return (
            Exam.objects.filter(participants__student=self, participants__is_active=True)
            .exclude(status=ExamStatus.DRAFT)
            .order_by("opens_at", "exam_id")
        )

    def start_exam(self, exam_id):
        """startExam(examId): bắt đầu hoặc tiếp tục lượt làm bài (UC Take Exam).

        Mở lại/đăng nhập lại dùng đúng lượt cũ, không đặt lại thời gian (BR-20, BR-21).
        """
        from attempts.models import Submission
        from exams.models import Exam

        exam = Exam.objects.get(pk=exam_id)
        existing = Submission.objects.filter(exam=exam, student=self).first()
        if existing and existing.is_editable():
            return existing
        reason = exam.cannot_start_reason(self)
        if reason:
            raise ValidationError(reason)
        return Submission.start(exam, self)

    def save_answer(self, data):
        """saveAnswer(data): lưu đáp án. data gồm submission_id, question_id, option_id
        (None = bỏ chọn) và version. Trả về version mới."""
        submission = self._own_submission(data["submission_id"])
        return submission.save_answer(data["question_id"], data.get("option_id"), data["version"])

    def submit_exam(self, submission_id):
        """submitExam(id): nộp bài (FR-10). Gọi lại nhiều lần vẫn chỉ ghi nhận một lần."""
        return self._own_submission(submission_id).submit()

    def view_result(self, exam_id):
        """viewResult(id): kết quả của chính mình; None nếu chưa chấm hoặc chưa công bố (BR-10)."""
        from results.models import Result

        result = (
            Result.objects.filter(submission__exam_id=exam_id, submission__student=self)
            .select_related("submission__exam")
            .first()
        )
        return result if result and result.can_view(self) else None

    def _own_submission(self, submission_id):
        from attempts.models import Submission

        try:
            return Submission.objects.get(pk=submission_id, student=self)
        except Submission.DoesNotExist:
            raise PermissionDenied("Bài làm không thuộc về bạn.")


def _has_business_data(user):
    """Tài khoản đã có câu hỏi, đề, phân công hoặc bài làm thì không đổi vai trò được (BR-22)."""
    return (
        user.questions.exists()
        or user.exams.exists()
        or user.exam_assignments.exists()
        or user.submissions.exists()
    )
