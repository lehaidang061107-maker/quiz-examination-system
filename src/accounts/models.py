from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.db.models.functions import Now


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

    @property
    def is_active(self):
        # Django kiểm tra is_active khi nạp user từ phiên: tài khoản bị khóa tự mất phiên.
        return self.status == UserStatus.ACTIVE

    @property
    def is_staff(self):
        return self.is_active and self.role == Role.ADMIN

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return self.is_staff
