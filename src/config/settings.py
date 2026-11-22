"""Cấu hình Django. Mọi giá trị bí mật và thông tin kết nối đọc từ file .env ở thư mục gốc dự án."""
import os
import sys
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # src/
ROOT_DIR = BASE_DIR.parent
load_dotenv(ROOT_DIR / ".env")


def env(name, default=None):
    value = os.getenv(name, default)
    if value is None or value == "":
        raise ImproperlyConfigured(f"Chưa đặt {name} trong file .env (xem .env.example)")
    return value


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("SECRET_KEY")
DEBUG = env_bool("DEBUG", False)
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "questions",
    "exams",
    "attempts",
    "results",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.navigation.navigation",
            ],
        },
    },
]

# PostgreSQL chạy bằng Docker (compose.yaml); dùng chung biến với .env (xem docs/guides/01-getting-started.md).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "55433"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tài khoản riêng của dự án: bảng users, đăng nhập bằng email.
AUTH_USER_MODEL = "accounts.User"

# Mật khẩu ít nhất 8 ký tự, có cả chữ và số (đặc tả).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.LetterAndDigitValidator"},
]

# Phiên lưu trong database, tự hết hạn sau 30 phút không hoạt động (NFR-SEC-01, NFR-SEC-08).
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True  # lưu UTC, hiển thị giờ Việt Nam

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Trang Đăng nhập do S3-03 làm (accounts/urls.py, name="login"). Chưa đăng nhập mà vào trang
# cần quyền thì chuyển tới đây; đăng nhập/đăng xuất xong về Trang chủ.
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = LOGIN_URL

# messages.error(...) hiển thị bằng class Bootstrap "alert-danger".
MESSAGE_TAGS = {message_constants.ERROR: "danger"}

# Nhật ký thao tác quan trọng (NFR-MAI-03, NFR-SEC-10): đăng nhập/đăng xuất, thay đổi tài khoản (accounts.audit),
# nộp bài (attempts.audit), đóng đề/lưu trữ/công bố điểm (exams.audit).
# In ra console, khi chạy Docker xem bằng `docker compose logs web`.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"audit": {"format": "{asctime} [AUDIT] {message}", "style": "{"}},
    # Khi chạy `manage.py test` không in nhật ký ra màn hình cho đỡ rối (test vẫn kiểm tra bằng assertLogs).
    "handlers": {"audit_console": {
        "class": "logging.NullHandler" if sys.argv[1:2] == ["test"] else "logging.StreamHandler",
        "formatter": "audit",
    }},
    "loggers": {
        "exams.audit": {"handlers": ["audit_console"], "level": "INFO", "propagate": False},
        "attempts.audit": {"handlers": ["audit_console"], "level": "INFO", "propagate": False},
        "accounts.audit": {"handlers": ["audit_console"], "level": "INFO", "propagate": False},
    },
}
