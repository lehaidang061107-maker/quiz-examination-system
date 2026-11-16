from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    """Kiểm tra website đang chạy và kết nối được database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        database = "ok"
    except DatabaseError:
        database = "error"
    status = 200 if database == "ok" else 503
    return JsonResponse({"status": "ok" if status == 200 else "error", "database": database}, status=status)
