"""Đăng nhập tạm để chạy thử giao diện: python manage.py dev_login teacher@demo.example

Tạo phiên đăng nhập cho tài khoản rồi in ra giá trị cookie `sessionid` để dán vào trình duyệt
(cách dán xem docs/huong-dan/4-kiem-thu.md). Chỉ chạy khi DEBUG=True, không dùng trên máy chủ thật.
"""
from django.conf import settings
from django.contrib.auth import login
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpRequest

from accounts.models import User


class Command(BaseCommand):
    help = "Tạo phiên đăng nhập tạm cho một tài khoản (chỉ khi DEBUG=True) và in ra sessionid."

    def add_arguments(self, parser):
        parser.add_argument("email", help="email tài khoản, ví dụ student1@demo.example")

    def handle(self, *args, email, **options):
        if not settings.DEBUG:
            raise CommandError("Chỉ dùng dev_login khi DEBUG=True (máy cá nhân).")
        try:
            user = User.objects.get_by_natural_key(email)
        except User.DoesNotExist:
            raise CommandError(f"Không có tài khoản {email}. Chạy python manage.py seed_demo để tạo tài khoản demo.")
        if not user.is_active:
            raise CommandError(f"Tài khoản {email} đang bị khóa hoặc ngừng sử dụng.")
        request = HttpRequest()
        request.session = SessionStore()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.save()
        self.stdout.write(f"Đăng nhập: {user.full_name} ({user.role})")
        self.stdout.write(f"sessionid = {request.session.session_key}")
        self.stdout.write("Dán vào Chrome: F12 > Application > Cookies > http://127.0.0.1:8000 > sessionid, rồi F5.")
        return None
