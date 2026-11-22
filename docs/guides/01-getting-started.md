# 01 · Getting Started

<!-- toc -->

**Mục lục**

- [Environment Variables (`.env`)](#environment-variables-env)
- [Option A: Run with Docker](#option-a-run-with-docker)
- [Option B: Local Development](#option-b-local-development)
- [Audit Logs](#audit-logs)
- [Demo Accounts & Seed Data](#demo-accounts--seed-data)
- [Database Client (Beekeeper / DBeaver)](#database-client-beekeeper--dbeaver)
- [Troubleshooting](#troubleshooting)

<!-- /toc -->

Website chạy bằng Django, database là PostgreSQL chạy trong **Docker Desktop**. Mỗi người có database riêng trên máy mình.

Có hai cách chạy:

| Muốn | Dùng | Cần cài |
| --- | --- | --- |
| Xem, demo | [Option A: Run with Docker](#option-a-run-with-docker) | Docker Desktop |
| Viết code | [Option B: Local Development](#option-b-local-development) | Docker Desktop + Python 3.12–3.14 |

## Environment Variables (`.env`)

Ở thư mục dự án, chép file mẫu: `cp .env.example .env` (Windows: `copy .env.example .env`), mở ra điền:

| Dòng | Điền gì |
| --- | --- |
| `POSTGRES_PASSWORD` | Mật khẩu database, tự đặt |
| `DEMO_PASSWORD` | `Kiemthu2026` (cả nhóm dùng chung để test case ghi cùng một mật khẩu) |
| `SECRET_KEY` | Chạy `python -c "import secrets; print(secrets.token_urlsafe(50))"` rồi dán vào. Chưa có Python thì gõ tạm chuỗi ngẫu nhiên khoảng 50 ký tự |
| `DEBUG`, `ALLOWED_HOSTS` | Giữ như `.env.example` (`DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1`) |

`.env` chỉ nằm trên máy mình, không commit lên GitHub.

## Option A: Run with Docker

```bash
docker compose up -d --build --wait                        # lần đầu mất vài phút; tự tạo bảng mỗi lần khởi động
docker compose exec web python manage.py seed_demo          # tạo dữ liệu mẫu, chạy lại không bị trùng
```

Mở http://127.0.0.1:8000/accounts/login/ và đăng nhập bằng [tài khoản mẫu](#demo-accounts--seed-data).

| Muốn | Lệnh |
| --- | --- |
| Xem log website | `docker compose logs -f web` |
| Xem log tiến trình nền (tự nộp, chấm lại) | `docker compose logs -f worker` |
| Xem nhật ký thao tác (đăng nhập, tài khoản, nộp bài, đề thi) | Xem [Audit Logs](#audit-logs) |
| Sửa code xong, chạy bản mới | `docker compose up -d --build --wait` |
| Chạy bộ kiểm tra | `docker compose exec web python manage.py test` (cuối kết quả có `OK` là đạt) |
| Chạy lệnh `manage.py` khác | Thêm `docker compose exec web` trước `python manage.py ...` |
| Sao lưu / phục hồi database | `scripts/backup_db.sh`, `scripts/restore_db.sh` (xem [05-backup-restore.md](05-backup-restore.md)) |
| Tắt (giữ dữ liệu) | `docker compose stop` |

Website trong Docker chạy bằng `runserver`, chỉ dùng cho máy cá nhân và buổi demo.

## Option B: Local Development

**Lần đầu** (Docker Desktop đang mở):

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d --wait db
cd src
python manage.py migrate
python manage.py seed_demo         # thấy "Đã tạo dữ liệu demo." là xong
python manage.py runserver
```

**Những lần sau:**

```bash
source .venv/bin/activate
docker compose up -d --wait db
cd src
python manage.py runserver
```

Cần tự nộp bài khi hết giờ và chấm lại bài lỗi thì mở thêm một terminal, chạy `python manage.py run_worker`
trong `src` (Ctrl+C để dừng). Chạy bằng Docker thì service `worker` đã tự bật.

Mở http://127.0.0.1:8000/accounts/login/. Đang chạy Option A thì tắt website và worker Docker trước:
`docker compose stop web worker` (để worker trong Docker không chạy code cũ trên cùng database).
Tắt database khi xong việc: `docker compose stop db` (dữ liệu vẫn giữ).

## Audit Logs

Hệ thống ghi nhật ký các thao tác quan trọng (NFR-MAI-03, NFR-SEC-10). Mỗi dòng bắt đầu bằng `[AUDIT]`, có giờ máy
chủ, người làm (`user_id`/`admin_id`), đối tượng và kết quả. **Không ghi mật khẩu, cookie phiên hay đáp án.**

| Nhóm (logger) | Ghi khi | Ví dụ |
| --- | --- | --- |
| `accounts.audit` | Đăng nhập (thành công / thất bại kèm lý do), đăng xuất, đăng ký Student, đổi mật khẩu; Admin tạo, sửa, khóa, mở khóa, xóa tài khoản, đặt lại mật khẩu | `đăng nhập thất bại \| email=... \| sai mật khẩu lần 2 \| ip=...` |
| `attempts.audit` | Mỗi lần nộp bài: nộp tay, hoặc tự nộp kèm lý do (hết giờ, đề đã đóng, bị thu hồi quyền, tài khoản bị khóa) | `nộp bài \| submission_id=... \| tự nộp (hết giờ) \| submitted_at=...` |
| `exams.audit` | Giảng viên đóng đề, lưu trữ đề, công bố điểm; hệ thống tự đóng đề khi hết lịch | `công bố điểm \| user_id=... \| exam_id=... \| 30 bài` |

Nhật ký in ra màn hình của tiến trình đang chạy. Thao tác trên website nằm ở service `web`; tự nộp bài và tự đóng
đề do worker làm nằm ở service `worker`:

```bash
docker compose logs web worker | grep AUDIT                      # toàn bộ nhật ký
docker compose logs web | grep "AUDIT] đăng nhập thất bại"       # chỉ đăng nhập sai
docker compose logs -f web worker | grep --line-buffered AUDIT   # xem trực tiếp
```

Chạy Option B thì nhật ký hiện ngay trong terminal đang chạy `runserver` / `run_worker`. Khi chạy `manage.py test`
nhật ký không in ra (test vẫn kiểm tra bằng `assertLogs`).

Nhật ký chỉ nằm trong log của container: container bị tạo lại (`docker compose down`, hoặc `up --build` sau khi sửa
code) là mất. Cần giữ lâu thì lưu ra file trước, ví dụ `docker compose logs --no-color web worker | grep AUDIT > audit-$(date +%F).log`.

## Demo Accounts & Seed Data

Lệnh `seed_demo` tạo 6 tài khoản, mật khẩu đều là `DEMO_PASSWORD` trong `.env`:

| Vai trò | Email |
| --- | --- |
| Admin | `admin@demo.example` |
| Teacher | `teacher@demo.example` (có đề thi, bài làm), `teacher2@demo.example` (chỉ có câu hỏi) |
| Student | `student1@demo.example`, `student2@demo.example`, `student3@demo.example` |

Dữ liệu có sẵn:

- Câu hỏi: `teacher@` có 3 câu hoàn chỉnh, `teacher2@` có 2 câu (mỗi câu 3 lựa chọn, 1 đáp án đúng); mỗi giảng viên thêm 1 câu nháp.
- 4 đề của `teacher@`: nháp, đang mở (mở 30 ngày), đã đóng chờ chấm, đã công bố điểm.
  `student1`, `student2` được giao cả 4 đề; `student3` được giao đề nháp và đề đang mở, chưa làm bài nào.
- 4 lượt làm: 1 đang làm (hạn 30 phút), 1 chờ chấm, 2 đã chấm; đủ trường hợp đáp án đúng, sai, bỏ trống.
- Điểm: `student1` 6/6, `student2` 2/6.

Chạy lại `seed_demo` **không** thêm trùng, không đổi mật khẩu hay dữ liệu đã có (kể cả khi đổi `DEMO_PASSWORD`),
chỉ tạo phần còn thiếu. Nếu dữ liệu mẫu bị xóa dở hoặc email mẫu đang thuộc vai trò khác, lệnh dừng lại để không ghi đè.
Code của lệnh: `src/accounts/management/commands/seed_demo.py`.

## Database Client (Beekeeper / DBeaver)

Tạo kết nối **PostgreSQL**:

| Ô | Giá trị |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `55433` |
| User | `quiz_app` |
| Database | `quiz_examination` |
| Password | `POSTGRES_PASSWORD` trong `.env` |

Các bảng nằm trong mục `public`:

| Bảng | Lưu gì |
| --- | --- |
| `users` | Tài khoản, vai trò |
| `questions`, `answer_options` | Câu hỏi và các lựa chọn |
| `exams`, `exam_questions` | Đề thi; câu nào trong đề, điểm từng câu |
| `exam_participants` | Sinh viên được giao đề |
| `submissions`, `submission_answers` | Lượt làm bài; đáp án sinh viên chọn |
| `results` | Điểm |

Bảng bắt đầu bằng `django_` hoặc `auth_` là của hệ thống, không cần quan tâm.

## Troubleshooting

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` | Chạy lại `source .venv/bin/activate` |
| Không kết nối được database | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| `password authentication failed` | Sai `POSTGRES_PASSWORD` trong `.env` |
| `DEMO_PASSWORD chưa hợp lệ` | Đặt `DEMO_PASSWORD` ít nhất 8 ký tự, có cả chữ và số |
| `Demo đã tồn tại` | Bình thường, dữ liệu mẫu đã có sẵn |
| `port is already allocated` | Cổng đang bận: đổi `POSTGRES_PORT` hoặc `WEB_PORT` trong `.env` (ví dụ `WEB_PORT=8001`) |
| Muốn xóa sạch dữ liệu, làm lại từ đầu | Sao lưu trước nếu cần (`scripts/backup_db.sh`), rồi `docker compose down -v` và làm lại các lệnh lần đầu |
