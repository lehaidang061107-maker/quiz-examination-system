"""Tiến trình nền tự nộp và chấm lại bài (S3-23): python manage.py run_worker

Mỗi vòng: chốt các lượt quá hạn / đề đã đóng / bị thu hồi quyền, rồi chấm lại bài còn SUBMITTED.
Mặc định chạy mỗi 5 giây (chờ nhóm xác nhận, xem docs/guides/03-coding-guidelines.md); đổi bằng --interval.
Dừng an toàn bằng Ctrl+C hoặc docker compose stop: vòng đang chạy làm xong rồi mới thoát.
Database mất kết nối thì ghi lỗi và thử lại ở vòng sau, không thoát.
"""
import logging
import signal
import threading

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connection

from attempts.worker import process_once

logger = logging.getLogger("attempts.worker")


def refresh_connection():
    """Bỏ kết nối hỏng/cũ để vòng sau tự nối lại khi database khởi động lại.
    Không đụng tới kết nối đang trong giao dịch (ví dụ khi chạy trong TestCase)."""
    if not connection.in_atomic_block:
        close_old_connections()


class Command(BaseCommand):
    help = "Chạy nền: tự nộp lượt thi hết hạn và chấm lại bài chờ chấm."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=5.0, help="số giây giữa hai vòng (mặc định 5)")
        parser.add_argument("--once", action="store_true", help="chạy một vòng rồi thoát (dùng khi kiểm thử)")

    def handle(self, *args, interval, once, **options):
        if interval <= 0:
            raise CommandError("--interval phải lớn hơn 0.")
        if once:
            self.stdout.write(f"Worker: {process_once()}")
            return

        stop = threading.Event()

        def request_stop(signum, frame):
            stop.set()

        previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
        self.stdout.write(f"Worker đã chạy, mỗi {interval:g} giây một vòng. Bấm Ctrl+C để dừng.")
        try:
            while not stop.is_set():
                stats = self.run_round()
                if stats is not None and stats.total:
                    self.stdout.write(f"Worker: {stats}")
                stop.wait(interval)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            refresh_connection()
        self.stdout.write("Worker đã dừng.")

    def run_round(self):
        refresh_connection()
        try:
            return process_once()
        except Exception:
            logger.exception("Worker: vòng xử lý thất bại, sẽ thử lại vòng sau")
            return None
