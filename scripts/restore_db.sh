#!/usr/bin/env bash
# Phục hồi database từ một bản sao lưu (S3-25, NFR-REL-04).
#
#   scripts/restore_db.sh backups/quiz-20261122-210000.dump
#   scripts/restore_db.sh --yes backups/quiz-...dump      # không hỏi xác nhận
#
# Các bước: kiểm tra file -> sao lưu dữ liệu hiện tại (backups/truoc-phuc-hoi-*.dump) -> tạm dừng web, worker
# -> xóa và tạo lại database -> nạp bản sao lưu -> bật lại web, worker (web tự chạy migrate khi khởi động).
# TOÀN BỘ dữ liệu hiện tại bị thay bằng dữ liệu trong file sao lưu.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-backups}"
yes=0
if [ "${1:-}" = "--yes" ]; then yes=1; shift; fi
file="${1:-}"

if [ -z "$file" ]; then
  echo "Cách dùng: scripts/restore_db.sh [--yes] backups/quiz-YYYYMMDD-HHMMSS.dump" >&2
  echo "Các bản đang có:" >&2
  ls -1 "$BACKUP_DIR"/*.dump 2>/dev/null | sort -r >&2 || echo "  (chưa có bản nào)" >&2
  exit 1
fi
if [ ! -s "$file" ]; then
  echo "Lỗi: không thấy file $file hoặc file rỗng." >&2
  exit 1
fi
if [ -z "$(docker compose ps --status running -q db 2>/dev/null)" ]; then
  echo "Lỗi: database chưa chạy. Chạy: docker compose up -d --wait db" >&2
  exit 1
fi
if ! docker compose exec -T db pg_restore --list < "$file" > /dev/null; then
  echo "Lỗi: $file không phải bản sao lưu hợp lệ của pg_dump, không phục hồi." >&2
  exit 1
fi

# </dev/null: không để docker compose exec đọc mất phần người dùng gõ ở bước xác nhận bên dưới.
db_name=$(docker compose exec -T db sh -c 'echo "$POSTGRES_DB"' </dev/null)
if [ "$yes" -ne 1 ]; then
  echo "Sẽ THAY TOÀN BỘ dữ liệu của database '$db_name' bằng dữ liệu trong $file."
  echo "Dữ liệu hiện tại sẽ được sao lưu trước vào $BACKUP_DIR/truoc-phuc-hoi-*.dump."
  read -r -p "Gõ 'dong y' để tiếp tục: " answer
  if [ "$answer" != "dong y" ]; then
    echo "Đã hủy, không thay đổi gì."
    exit 1
  fi
fi

mkdir -p "$BACKUP_DIR"
safety="$BACKUP_DIR/truoc-phuc-hoi-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' < /dev/null > "$safety"
echo "Đã sao lưu dữ liệu hiện tại: $safety"

# Nhớ service nào đang chạy để bật lại đúng như cũ; dừng web, worker để không còn kết nối tới database.
running=$(docker compose ps --status running --services | grep -E '^(web|worker)$' || true)
restart_services() {
  if [ -n "$running" ]; then
    # shellcheck disable=SC2086
    docker compose start $running > /dev/null
    echo "Đã bật lại: $(echo $running)"
  fi
}
on_error() {
  echo "Phục hồi thất bại. Dữ liệu trước khi phục hồi nằm ở $safety (phục hồi lại bằng chính script này)." >&2
  restart_services
}
trap on_error ERR

if [ -n "$running" ]; then
  # shellcheck disable=SC2086
  docker compose stop $running > /dev/null
  echo "Đã tạm dừng: $(echo $running)"
fi

docker compose exec -T db sh -c '
  set -e
  dropdb -U "$POSTGRES_USER" --if-exists --force "$POSTGRES_DB"
  createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"
' </dev/null
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --exit-on-error' < "$file"
echo "Đã phục hồi database '$db_name' từ $file"

trap - ERR
restart_services
