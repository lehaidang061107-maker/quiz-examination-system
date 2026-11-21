from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import AdminUserCreateForm, AdminUserUpdateForm, StudentRegisterForm
from .models import Admin, Role, User, UserStatus
from .services import revoke_user_sessions


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


# ---------------- S3-04: Admin Account Management & Session Revocation ----------------


def _admin_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if getattr(request.user, "role", None) != Role.ADMIN:
            messages.error(request, "Chỉ Quản trị viên mới có quyền truy cập chức năng này.")
            return redirect("home")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _get_admin_actor(user) -> Admin:
    if isinstance(user, Admin):
        return user
    return Admin.objects.get(pk=user.pk)


def _apply_validation_errors(form, exc: ValidationError):
    if hasattr(exc, "message_dict"):
        for field, msgs in exc.message_dict.items():
            for msg in msgs:
                if field in form.fields:
                    form.add_error(field, msg)
                else:
                    form.add_error(None, msg)
    else:
        for msg in exc.messages:
            form.add_error(None, msg)


@_admin_required
def admin_user_list_view(request):
    q = (request.GET.get("q") or "").strip()
    role = (request.GET.get("role") or "").strip()
    status = (request.GET.get("status") or "").strip()

    users_qs = User.objects.all().order_by("-user_id")
    if q:
        users_qs = users_qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))
    if role in Role.values:
        users_qs = users_qs.filter(role=role)
    if status in UserStatus.values:
        users_qs = users_qs.filter(status=status)

    paginator = Paginator(users_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/admin/user_list.html",
        {
            "page_obj": page_obj,
            "q": q,
            "role": role,
            "status": status,
            "roles": Role.choices,
            "statuses": UserStatus.choices,
        },
    )


@_admin_required
def admin_user_create_view(request):
    actor = _get_admin_actor(request.user)
    if request.method == "POST":
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            try:
                created = actor.create_user(form.cleaned_data)
                messages.success(request, f"Đã tạo tài khoản {created.email}.")
                return redirect("accounts:admin_user_list")
            except ValidationError as exc:
                _apply_validation_errors(form, exc)
    else:
        form = AdminUserCreateForm()

    return render(request, "accounts/admin/user_form.html", {"form": form, "mode": "create"})


@_admin_required
def admin_user_update_view(request, user_id: int):
    target_user = get_object_or_404(User, pk=user_id)
    old_role = target_user.role
    actor = _get_admin_actor(request.user)

    if request.method == "POST":
        form = AdminUserUpdateForm(request.POST)
        if form.is_valid():
            try:
                updated = actor.update_user(target_user.pk, form.cleaned_data)
                if updated.role != old_role:
                    revoked = revoke_user_sessions(updated.pk)
                    messages.info(
                        request,
                        f"Vai trò đã thay đổi nên đã thu hồi {revoked} phiên đăng nhập hiện tại.",
                    )
                messages.success(request, f"Đã cập nhật tài khoản {updated.email}.")
                return redirect("accounts:admin_user_list")
            except ValidationError as exc:
                _apply_validation_errors(form, exc)
    else:
        form = AdminUserUpdateForm(
            initial={
                "full_name": target_user.full_name,
                "email": target_user.email,
                "role": target_user.role,
            }
        )

    return render(
        request,
        "accounts/admin/user_form.html",
        {"form": form, "mode": "edit", "target_user": target_user},
    )


@_admin_required
def admin_user_lock_view(request, user_id: int):
    target_user = get_object_or_404(User, pk=user_id)
    actor = _get_admin_actor(request.user)

    if request.method == "POST":
        try:
            actor.lock_user(target_user.pk)
            revoked = revoke_user_sessions(target_user.pk)
            msg = f"Đã khóa tài khoản {target_user.email} và thu hồi {revoked} phiên."
            messages.success(request, msg)
        except ValidationError as exc:
            for m in exc.messages:
                messages.error(request, m)
        return redirect("accounts:admin_user_list")

    return render(
        request,
        "accounts/admin/user_confirm_action.html",
        {
            "target_user": target_user,
            "action": "lock",
            "action_label": "Khóa tài khoản",
        },
    )


@_admin_required
def admin_user_delete_view(request, user_id: int):
    target_user = get_object_or_404(User, pk=user_id)
    actor = _get_admin_actor(request.user)

    if request.method == "POST":
        try:
            actor.delete_user(target_user.pk)
            revoked = revoke_user_sessions(target_user.pk)
            msg = f"Đã xử lý xóa/ngừng hoạt động tài khoản {target_user.email} (thu hồi {revoked} phiên)."
            messages.success(request, msg)
        except ValidationError as exc:
            for m in exc.messages:
                messages.error(request, m)
        return redirect("accounts:admin_user_list")

    return render(
        request,
        "accounts/admin/user_confirm_action.html",
        {
            "target_user": target_user,
            "action": "delete",
            "action_label": "Xóa tài khoản",
        },
    )
