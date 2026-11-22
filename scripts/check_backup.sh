#!/usr/bin/env bash
# Kiểm tra một bản sao lưu phục hồi được, KHÔNG đụng tới dữ liệu đang dùng (S3-25, NFR-REL-04:
# "kiểm tra phục hồi trước kỳ thi").
#
#   scripts/check_backup.sh                         # kiểm tra bản mới nhất trong backups/
#   scripts/check_backup.sh backups/quiz-...dump
#
# Nạp bản sao lưu vào một database tạm (quiz_kiemtra_phuchoi), đếm số dòng 9 bảng nghiệp vụ,
# so với database đang chạy, rồi xóa database tạm.
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-backups}"
CHECK_DB="quiz_kiemtra_phuchoi"
TABLES="users questions answer_options exams exam_questions exam_participants submissions submission_answers results"

file="${1:-$(ls -1 "$BACKUP_DIR"/quiz-*.dump 2>/dev/null | sort -r | head -n 1 || true)}"
if [ -z "$file" ] || [ ! -s "$file" ]; then
  echo "Lỗi: chưa có bản sao lưu nào. Chạy scripts/backup_db.sh trước." >&2
  exit 1
fi
if [ -z "$(docker compose ps --status running -q db 2>/dev/null)" ]; then
  echo "Lỗi: database chưa chạy. Chạy: docker compose up -d --wait db" >&2
  exit 1
fi

cleanup() {
  docker compose exec -T -e CHECK_DB="$CHECK_DB" db sh -c 'dropdb -U "$POSTGRES_USER" --if-exists --force "$CHECK_DB"' 2>/dev/null || true
}
trap cleanup EXIT

echo "Kiểm tra: $file"
start=$(date +%s)
cleanup
docker compose exec -T -e CHECK_DB="$CHECK_DB" db sh -c 'createdb -U "$POSTGRES_USER" "$CHECK_DB"'
docker compose exec -T -e CHECK_DB="$CHECK_DB" db sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$CHECK_DB" --no-owner --exit-on-error' < "$file"
elapsed=$(( $(date +%s) - start ))

count() {  # count <database> <bảng>: số dòng, hoặc THIẾU nếu bảng không có
  docker compose exec -T -e TARGET_DB="$1" db sh -c \
    "psql -U \"\$POSTGRES_USER\" -d \"\$TARGET_DB\" -tAc 'SELECT count(*) FROM $2' 2>/dev/null" </dev/null || echo "THIẾU"
}

live_db=$(docker compose exec -T db sh -c 'echo "$POSTGRES_DB"')
missing=0
echo "Bảng                  Bản sao lưu   Đang chạy"  # chữ có dấu làm printf đếm lệch, nên viết sẵn
for t in $TABLES; do
  restored=$(count "$CHECK_DB" "$t")
  live=$(count "$live_db" "$t")
  [ "$restored" = "THIẾU" ] && missing=1
  printf "%-20s %13s %11s\n" "$t" "$restored" "$live"
done

if [ "$missing" -ne 0 ]; then
  echo "KHÔNG ĐẠT: bản sao lưu thiếu bảng nghiệp vụ." >&2
  exit 1
fi
echo "ĐẠT: phục hồi thử thành công trong ${elapsed} giây (database tạm đã xóa)."
echo "Số dòng khác nhau là bình thường nếu có thao tác sau lúc sao lưu."
