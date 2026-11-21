from django.apps import apps
from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_user_sessions(user_id: int) -> int:
    """Thu hồi toàn bộ session đang hoạt động của user_id."""
    target_id = str(user_id)
    revoked = 0
    for session in Session.objects.all():
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == target_id:
            session.delete()
            revoked += 1
    return revoked


def handle_user_exam_attempts(user) -> list[str]:
    """
    Chốt/khóa lượt thi đang dang dở của tài khoản nếu app attempts có model tương ứng
    và ghi nhận trạng thái xử lý để hiển thị cho Admin.
    """
    notes: list[str] = []
    try:
        Attempt = apps.get_model("attempts", "Attempt")
    except LookupError:
        Attempt = None

    if Attempt is not None:
        field_names = {f.name for f in Attempt._meta.get_fields()}
        user_field = "user" if "user" in field_names else ("student" if "student" in field_names else None)
        if user_field:
            qs = Attempt.objects.filter(**{user_field: user})
            if qs.exists():
                updated_count = 0
                if "status" in field_names and hasattr(Attempt, "Status"):
                    status_choices = getattr(Attempt.Status, "values", [])
                    locked_val = (
                        "LOCKED" if "LOCKED" in status_choices
                        else ("SUBMITTED" if "SUBMITTED" in status_choices else None)
                    )
                    if locked_val:
                        active_qs = qs.exclude(status=locked_val)
                        update_kwargs = {"status": locked_val}
                        if "submitted_at" in field_names:
                            update_kwargs["submitted_at"] = timezone.now()
                        updated_count = active_qs.update(**update_kwargs)
                notes.append(
                    f"Tài khoản có {qs.count()} lượt thi (đã chốt/khóa {updated_count} lượt đang mở)."
                )
    return notes
