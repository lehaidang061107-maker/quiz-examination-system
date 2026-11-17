"""Kiểm tra quyền phía máy chủ (BR-02, NFR-SEC-02, NFR-SEC-09).

Ẩn nút trên giao diện là chưa đủ: mọi view cần đăng nhập phải có decorator này.

    from accounts.decorators import role_required
    from accounts.models import Role

    @role_required(Role.TEACHER)
    def question_list(request): ...

    @role_required(Role.TEACHER, Role.STUDENT)   # nhiều vai trò cùng vào được
    def result_detail(request, result_id): ...
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Chưa đăng nhập -> chuyển tới trang Đăng nhập; sai vai trò -> 403."""
    if not roles:
        raise ValueError("role_required cần ít nhất một vai trò, ví dụ role_required(Role.TEACHER)")

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied("Bạn không có quyền truy cập trang này.")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def login_required_any_role(view):
    """Trang mọi vai trò đều vào được, chỉ cần đã đăng nhập (ví dụ Trang chủ)."""
    from accounts.models import Role

    return role_required(*Role.values)(view)
