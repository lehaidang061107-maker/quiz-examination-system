# Quiz Examination System

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.

**Hiện có:** tài liệu đặc tả và thiết kế; database 9 bảng kèm dữ liệu mẫu và kiểm thử; khung website Django.
**Chưa có:** các chức năng của website. Công nghệ: Python + Django + PostgreSQL.

## Chạy website

Làm trước phần "Lần đầu cài" trong [database/README.md](database/README.md). Sau đó:

1. Mở file `.env`, thêm 3 dòng (xem mẫu ở `.env.example`):
   `SECRET_KEY=` (chuỗi bí mật, tạo bằng `python -c "import secrets; print(secrets.token_urlsafe(50))"`),
   `DEBUG=True`, `ALLOWED_HOSTS=localhost,127.0.0.1`.
2. Chạy:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d --wait db
cd src
python manage.py runserver
```

3. Mở http://127.0.0.1:8000/health/ — thấy `{"status": "ok", "database": "ok"}` là chạy đúng.

Kiểm thử: trong thư mục `src`, chạy `python manage.py test`; cuối kết quả có `OK` là đạt.

> **Chưa chạy `python manage.py migrate`.** Bảng tài khoản riêng của dự án sẽ có khi chuyển
> database sang Django; migrate trước sẽ tạo sai bảng tài khoản và phải làm lại.

## Muốn làm gì thì đọc đâu

| Muốn | Đọc |
| --- | --- |
| Biết công nghệ và quy tắc viết code | [TECH_STACK.md](TECH_STACK.md) |
| Cài và chạy database, xem bằng Beekeeper/DBeaver | [database/README.md](database/README.md) |
| Tài khoản và dữ liệu demo | [database/seeds/README.md](database/seeds/README.md) |
| Kết quả kiểm tra database | [database/VERIFICATION.md](database/VERIFICATION.md) |
| Quy trình Git và Jira | [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md) |
| Kế hoạch các giai đoạn | [PROJECT_PLAN.md](PROJECT_PLAN.md) |
| Yêu cầu môn học | [GUIDELINES.md](GUIDELINES.md) |

## Các thư mục

| Thư mục | Chứa gì |
| --- | --- |
| `docs/` | Tài liệu đặc tả (Word), sơ đồ dữ liệu, sơ đồ lớp, thiết kế giao diện |
| `database/` | Tạo bảng, dữ liệu mẫu, hướng dẫn database |
| `tests/` | Kiểm thử |
| `src/` | Mã nguồn website: `config/` (cấu hình) và các app `accounts`, `questions`, `exams`, `attempts`, `results` |

Cấu trúc bảng theo mục 6 tài liệu đặc tả và `docs/DataModel-Reviewed.drawio`.
Mật khẩu và thông tin kết nối riêng của mỗi máy để trong `.env`; chỉ đưa `.env.example` lên GitHub.
