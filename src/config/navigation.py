"""Menu bên trái theo vai trò (giống bản Figma).

Mỗi mục là (tên hiển thị, tên URL). Ai làm trang nào thì đặt `name=` trong urls.py đúng như
bảng dưới; menu tự bật liên kết khi URL tồn tại, chưa có thì hiện mờ "Sắp có".
Đổi tên URL thì sửa ở đây.
"""
from django.urls import NoReverseMatch, reverse

from accounts.models import Role

MENU = {
    Role.ADMIN: [
        ("Trang chủ", "home"),
        ("Quản lý tài khoản", "accounts:user_list"),          # S3-04
    ],
    Role.TEACHER: [
        ("Trang chủ", "home"),
        ("Ngân hàng câu hỏi", "questions:list"),               # S3-06
        ("Quản lý kỳ thi", "exams:list"),                      # S3-11
        ("Kết quả thi", "results:teacher_list"),               # S3-24
    ],
    Role.STUDENT: [
        ("Trang chủ", "home"),
        ("Danh sách bài thi", "attempts:exam_list"),           # S3-16
        ("Lịch sử bài thi", "results:student_list"),           # S3-24
    ],
}


def url_or_none(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def navigation(request):
    """Context processor: đưa menu, vai trò, link đăng xuất vào mọi template."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    current = request.resolver_match.view_name if request.resolver_match else None
    items = [
        {"label": label, "url": url_or_none(name), "active": name == current}
        for label, name in MENU.get(user.role, [])
    ]
    return {
        "nav_items": items,
        "nav_role": user.role,
        "logout_url": url_or_none("accounts:logout"),  # S3-03
    }
