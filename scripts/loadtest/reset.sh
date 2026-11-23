#!/usr/bin/env bash
# S3-10: dựng lại database đo tải từ đầu (mỗi sinh viên chỉ nộp được một lần nên mỗi lượt đo cần dữ liệu mới).
# Dùng: scripts/loadtest/reset.sh [số sinh viên, mặc định 500]
set -euo pipefail
cd "$(dirname "$0")/../.."
N="${1:-500}"
C="docker compose -f compose.yaml -f compose.loadtest.yaml"
$C stop web-load >/dev/null
$C exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS quiz_load" -c "CREATE DATABASE quiz_load"'
$C up -d --wait web-load >/dev/null
$C exec -T web-load env LOAD_STUDENTS="$N" python manage.py shell < scripts/loadtest/seed.py | tail -1
