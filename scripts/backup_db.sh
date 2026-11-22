#!/usr/bin/env bash
# Sao lưu database PostgreSQL trong Docker (S3-25, NFR-REL-04).
#
#   scripts/backup_db.sh
#
# Tạo backups/quiz-YYYYMMDD-HHMMSS.dump (định dạng custom của pg_dump), kiểm tra file đọc lại được,
# rồi chỉ giữ 7 bản mới nhất. Đổi số bản giữ lại: KEEP=10 scripts/backup_db.sh
# Chạy hằng ngày bằng cron: xem docs/guides/05-backup-restore.md.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP="${KEEP:-7}"

if [ -z "$(docker compose ps --status running -q db 2>/dev/null)" ]; then
  echo "Lỗi: database chưa chạy. Mở Docker Desktop rồi chạy: docker compose up -d --wait db" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
file="$BACKUP_DIR/quiz-$(date +%Y%m%d-%H%M%S).dump"
tmp="$file.part"
trap 'rm -f "$tmp"' EXIT

# Biến POSTGRES_USER/POSTGRES_DB lấy trong container db nên không cần đọc .env ở đây.
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$tmp"

# File rỗng hoặc hỏng thì pg_restore --list báo lỗi: không giữ lại bản sao lưu hỏng.
if ! docker compose exec -T db pg_restore --list < "$tmp" > /dev/null; then
  echo "Lỗi: file sao lưu không đọc lại được, đã bỏ." >&2
  exit 1
fi
mv "$tmp" "$file"
echo "Đã sao lưu: $file ($(du -h "$file" | awk '{print $1}'))"

# Tên file có ngày giờ nên sắp theo tên là sắp theo thời gian; xóa các bản cũ hơn KEEP bản mới nhất.
ls -1 "$BACKUP_DIR"/quiz-*.dump | sort -r | tail -n +$((KEEP + 1)) | while read -r old; do
  rm -f -- "$old"
  echo "Xóa bản cũ: $old"
done
echo "Đang giữ $(ls -1 "$BACKUP_DIR"/quiz-*.dump | wc -l | tr -d ' ') bản trong $BACKUP_DIR/"
