# 1. Cài đặt và chạy website

<!-- toc -->

**Mục lục**

- [File `.env` (làm trước, cả hai cách)](#file-env-làm-trước-cả-hai-cách)
- [Cách 1: chạy hết bằng Docker](#cách-1-chạy-hết-bằng-docker)
- [Cách 2: chạy Python trên máy](#cách-2-chạy-python-trên-máy)
- [Tài khoản mẫu](#tài-khoản-mẫu)
- [Xem dữ liệu bằng Beekeeper hoặc DBeaver](#xem-dữ-liệu-bằng-beekeeper-hoặc-dbeaver)
- [Gặp lỗi](#gặp-lỗi)

<!-- /toc -->

Website chạy bằng Django, database là PostgreSQL chạy trong **Docker Desktop**. Mỗi người có database riêng trên máy mình.

Có hai cách chạy:

| Muốn | Dùng | Cần cài |
| --- | --- | --- |
| Xem, demo | [Cách 1: chạy hết bằng Docker](#cách-1-chạy-hết-bằng-docker) | Docker Desktop |
| Viết code | [Cách 2: chạy Python trên máy](#cách-2-chạy-python-trên-máy) | Docker Desktop + Python 3.12–3.14 |

## File `.env` (làm trước, cả hai cách)

Ở thư mục dự án, chép file mẫu: `cp .env.example .env` (Windows: `copy .env.example .env`), mở ra điền:

| Dòng | Điền gì |
| --- | --- |
| `POSTGRES_PASSWORD` | Mật khẩu database, tự đặt |
| `DEMO_PASSWORD` | `Kiemthu2026` (cả nhóm dùng chung để test case ghi cùng một mật khẩu) |
| `SECRET_KEY` | Chạy `python -c "import secrets; print(secrets.token_urlsafe(50))"` rồi dán vào. Chưa có Python thì gõ tạm chuỗi ngẫu nhiên khoảng 50 ký tự |
| `DEBUG`, `ALLOWED_HOSTS` | Giữ như `.env.example` (`DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1`) |

`.env` chỉ nằm trên máy mình, không commit lên GitHub.

## Cách 1: chạy hết bằng Docker

```bash
docker compose up -d --build --wait                        # lần đầu mất vài phút; tự tạo bảng mỗi lần khởi động
docker compose exec web python manage.py seed_demo          # tạo dữ liệu mẫu, chạy lại không bị trùng
```

Mở http://127.0.0.1:8000/accounts/login/ và đăng nhập bằng [tài khoản mẫu](#tài-khoản-mẫu).

| Muốn | Lệnh |
| --- | --- |
| Xem log website | `docker compose logs -f web` |
| Sửa code xong, chạy bản mới | `docker compose up -d --build --wait` |
| Chạy lệnh `manage.py` khác | Thêm `docker compose exec web` trước `python manage.py ...` |
| Tắt (giữ dữ liệu) | `docker compose stop` |

Website trong Docker chạy bằng `runserver`, chỉ dùng cho máy cá nhân và buổi demo.

## Cách 2: chạy Python trên máy

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

Mở http://127.0.0.1:8000/accounts/login/. Đang chạy cách 1 thì tắt website Docker trước: `docker compose stop web`.
Tắt database khi xong việc: `docker compose stop db` (dữ liệu vẫn giữ).

## Tài khoản mẫu

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

## Xem dữ liệu bằng Beekeeper hoặc DBeaver

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

## Gặp lỗi

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` | Chạy lại `source .venv/bin/activate` |
| Không kết nối được database | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| `password authentication failed` | Sai `POSTGRES_PASSWORD` trong `.env` |
| `DEMO_PASSWORD chưa hợp lệ` | Đặt `DEMO_PASSWORD` ít nhất 8 ký tự, có cả chữ và số |
| `Demo đã tồn tại` | Bình thường, dữ liệu mẫu đã có sẵn |
| `port is already allocated` | Cổng đang bận: đổi `POSTGRES_PORT` hoặc `WEB_PORT` trong `.env` (ví dụ `WEB_PORT=8001`) |
| Muốn xóa sạch dữ liệu, làm lại từ đầu | `docker compose down -v`, rồi làm lại các lệnh lần đầu |
