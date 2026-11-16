# Hướng dẫn mở database

Database lưu tài khoản, câu hỏi, đề thi, bài làm và điểm. Nó chạy bằng **Docker Desktop**
trên máy bạn; mỗi người có database riêng.

## Lần đầu (làm 1 lần)

**1. Cài sẵn:** Python 3.12–3.14 và Docker Desktop. Mở Docker Desktop lên.

**2. Mở Terminal ở thư mục dự án, cài thư viện:**

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. Tạo file `.env`:** chép `.env.example` thành `.env` (`cp .env.example .env`), mở ra điền:

| Dòng | Điền gì |
| --- | --- |
| `POSTGRES_PASSWORD` | Mật khẩu database, tự đặt |
| `DEMO_PASSWORD` | Mật khẩu tài khoản demo, tự đặt: ít nhất 8 ký tự, có cả chữ và số |
| `SECRET_KEY` | Chạy `python -c "import secrets; print(secrets.token_urlsafe(50))"` rồi dán kết quả vào |

**4. Bật database, tạo bảng và dữ liệu mẫu:**

```bash
docker compose up -d --wait db
cd src
python manage.py migrate
python manage.py seed_demo
```

Thấy `Đã tạo dữ liệu demo.` là xong. Tài khoản demo xem ở [seeds/README.md](seeds/README.md).

## Những lần sau

```bash
source .venv/bin/activate
docker compose up -d --wait db
```

Dùng xong muốn tắt: `docker compose stop db` (dữ liệu vẫn giữ).

## Xem dữ liệu bằng Beekeeper hoặc DBeaver

Tạo kết nối mới, chọn **PostgreSQL**, điền:

| Ô | Giá trị |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `55433` |
| User | `quiz_app` |
| Database | `quiz_examination` |
| Password | `POSTGRES_PASSWORD` trong `.env` |

Bấm **Connect**, mở mục `public` để thấy các bảng:

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
| Không tìm thấy `python` | Chạy lại lệnh `source .venv/bin/activate` |
| Không kết nối được | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| `password authentication failed` | Sai `POSTGRES_PASSWORD` trong `.env` |
| `DEMO_PASSWORD chưa hợp lệ` | Đổi `DEMO_PASSWORD` thành ít nhất 8 ký tự, có cả chữ và số |
| `Demo đã tồn tại` | Bình thường, dữ liệu mẫu đã có sẵn |

Muốn xóa hết dữ liệu để làm lại từ đầu: `docker compose down -v`, rồi làm lại bước 4.
