# Getting Started

<!-- toc -->

**Mục lục**

- [Environment Variables (`.env`)](#environment-variables-env)
- [Option A: Run with Docker](#option-a-run-with-docker)
- [Option B: Local Development](#option-b-local-development)
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

Mở http://127.0.0.1:8000/accounts/login/ và đăng nhập bằng [tài khoản mẫu](seeds/README.md).

| Muốn | Lệnh |
| --- | --- |
| Xem log website | `docker compose logs -f web` |
| Sửa code xong, chạy bản mới | `docker compose up -d --build --wait` |
| Chạy lệnh `manage.py` khác | Thêm `docker compose exec web` trước `python manage.py ...` |
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
python manage.py seed_demo         # thấy "Đã tạo dữ liệu demo." là xong, xem seeds/README.md
python manage.py runserver
```

**Những lần sau:**

```bash
source .venv/bin/activate
docker compose up -d --wait db
cd src
python manage.py runserver
```

Mở http://127.0.0.1:8000/accounts/login/. Đang chạy cách 1 thì tắt website Docker trước: `docker compose stop web`.
Tắt database khi xong việc: `docker compose stop db` (dữ liệu vẫn giữ).

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
| Muốn xóa sạch dữ liệu, làm lại từ đầu | `docker compose down -v`, rồi làm lại các lệnh lần đầu |
