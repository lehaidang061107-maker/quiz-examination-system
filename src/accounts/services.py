from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_user_sessions(user_id: int) -> int:
    """Thu hồi toàn bộ session đang hoạt động của user_id."""
    target_id = str(user_id)
    revoked = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == target_id:
            session.delete()
            revoked += 1
    return revoked

