from urllib.parse import urlsplit

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Role, User


def _is_safe_next_url(next_url, request):
    if not next_url:
        return False
    parsed = urlsplit(next_url)
    # Chỉ cho phép đường dẫn nội bộ tương đối (tránh open redirect)
    return not parsed.scheme and not parsed.netloc and next_url.startswith("/")


def _redirect_by_role(user, next_url=None, request=None):
    if request and _is_safe_next_url(next_url, request):
        return redirect(next_url)

    if user.role == Role.ADMIN:
        return redirect("admin:index")
    if user.role == Role.TEACHER:
        # Đổi tên route dashboard giảng viên nếu app của bạn đặt tên khác
        return redirect("exams:teacher_dashboard")
    return redirect("home")


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.user.is_authenticated:
        return _redirect_by_role(request.user, next_url=next_url, request=request)

    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        try:
            User.login(request, email, password)
            return _redirect_by_role(request.user, next_url=next_url, request=request)
        except ValidationError as exc:
            for msg in exc.messages:
                messages.error(request, msg)

    return render(request, "accounts/login.html", {"next": next_url or ""})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        request.user.logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect("accounts:login")