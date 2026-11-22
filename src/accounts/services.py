from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_user_sessions(user_id: int, keep_session_key: str | None = None) -> int:
    """Thu hồi toàn bộ session đang hoạt động của user_id (trừ keep_session_key nếu có)."""
    target_id = str(user_id)
    revoked = 0
    sessions = Session.objects.filter(expire_date__gt=timezone.now())
    if keep_session_key:
        sessions = sessions.exclude(session_key=keep_session_key)
    for session in sessions:
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == target_id:
            session.delete()
            revoked += 1
    return revoked

