from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import StudentRegisterForm
from .models import Role, User


def _is_safe_next_url(next_url, request):
    """Chỉ cho chuyển tới đường dẫn trong chính website (tránh open redirect, kể cả '/\\evil.com')."""
    return bool(next_url) and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )


def _redirect_after_login(request, next_url=None):
    if _is_safe_next_url(next_url, request):
        return redirect(next_url)
    # Trang chủ tự hiển thị dashboard theo vai trò (Admin, Teacher, Student).
    return redirect("home")


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next")

    if request.user.is_authenticated:
        return _redirect_after_login(request, next_url)

    if request.method == "POST":
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        try:
            User.login(request, email, password)
            return _redirect_after_login(request, next_url)
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


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data["full_name"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                with transaction.atomic():
                    User.objects.create_user(
                        email=email,
                        password=password,
                        full_name=full_name,
                        role=Role.STUDENT,
                    )
            except IntegrityError:
                # Hai người đăng ký cùng email cùng lúc: ràng buộc uq_users_email chặn người đến sau.
                form.add_error("email", "Email này đã được sử dụng. Vui lòng chọn email khác.")
                return render(request, "accounts/register.html", {"form": form})

            messages.success(request, "Đăng ký tài khoản thành công! Vui lòng đăng nhập.")
            return redirect("accounts:login")
    else:
        form = StudentRegisterForm()

    return render(request, "accounts/register.html", {"form": form})
