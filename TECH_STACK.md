# Công nghệ và công cụ đã thống nhất

Tài liệu này ghi lại lựa chọn công nghệ cho giai đoạn 3 của Quiz Examination System:
**Python + Django + PostgreSQL**. Mọi PR mới phải theo đúng bộ công nghệ này.
Các mục có nhãn **(chờ nhóm xác nhận)** là đề xuất, cần cả nhóm đồng ý trước khi áp dụng.

> **Thay đổi so với bản trước:** nhóm chuyển từ Flask sang Django và giữ PostgreSQL.
> Schema 9 bảng của S3-21 đang viết bằng Alembic sẽ được chuyển sang Django migrations
> (xem mục 6). Trong lúc chuyển, **không thêm migration Alembic mới**. Tài liệu
> [Tổng quan Giai đoạn 3](docs/Tong%20quan%20Giai%20doan%203.docx) vẫn ghi Flask,
> cần cập nhật theo quyết định này.

## 1. Bộ công nghệ đã chốt

| Hạng mục | Lựa chọn | Ghi chú |
| --- | --- | --- |
| Loại ứng dụng | Web, dùng trên trình duyệt máy tính | Giao diện có thể co giãn cho màn hình nhỏ. |
| Ngôn ngữ | Python 3.12 trở lên | Django 6.x yêu cầu Python ≥ 3.12. |
| Framework | Django 6.1, ghi cố định phiên bản trong `requirements.txt` | Bản đang dùng trong PR #18. |
| Giao diện | Django Templates + HTML/CSS + Bootstrap 5 | Bám bản thiết kế trong `docs/Quiz-Examination-System-UI-Figma-Import/`. Template tự escape HTML; không dùng `|safe` với dữ liệu người dùng. |
| Tương tác trên trình duyệt | JavaScript cơ bản | Đồng hồ đếm ngược, tự lưu đáp án, xác nhận nộp bài. Không chèn dữ liệu người dùng vào JS inline (`onclick="...{{ }}..."`); dùng `data-*` hoặc `json_script`. |
| Cơ sở dữ liệu | PostgreSQL 17, chạy bằng Docker Compose; driver psycopg 3 | Hướng dẫn chạy trong [database/README.md](database/README.md). Không dùng SQLite, kể cả khi test. |
| Truy cập dữ liệu | Django ORM | Truy vấn luôn qua ORM hoặc SQL có tham số. |
| Thay đổi cấu trúc dữ liệu | Django migrations | `makemigrations` rồi đọc lại file sinh ra trước khi commit. Không sửa migration đã merge. |
| Tài khoản | Custom user model `accounts.User`, đăng nhập bằng email, lưu ở bảng `users` | Phải có trước migration đầu tiên (`AUTH_USER_MODEL`). Vai trò `ADMIN`/`TEACHER`/`STUDENT`, trạng thái `ACTIVE`/`LOCKED`/`DELETED` như đặc tả. |
| Đăng nhập và phiên | `django.contrib.auth` + session lưu trong database | NFR-SEC-08: phiên ở máy chủ, đổi mã phiên sau đăng nhập (Django tự làm khi `login()`). NFR-SEC-01: `SESSION_COOKIE_AGE = 1800`, `SESSION_SAVE_EVERY_REQUEST = True` để hết hạn sau 30 phút không hoạt động. |
| Khóa tài khoản | `is_active` suy ra từ `status == 'ACTIVE'` | Tài khoản bị khóa tự bị đăng xuất ở request kế tiếp vì Django kiểm tra `is_active` khi nạp user từ phiên (BR-22). |
| Khóa tạm do đăng nhập sai | Bộ đếm và `locked_until` lưu trong DB, xử lý ở service đăng nhập | NFR-SEC-07, BR-23: khóa 15 phút sau 5 lần sai liên tiếp; tách biệt với `status = LOCKED` do Admin đặt. |
| Băm mật khẩu | Password hasher của Django (`PBKDF2` mặc định) | NFR-SEC-03. Bật `AUTH_PASSWORD_VALIDATORS` với độ dài tối thiểu 8 và thêm kiểm tra có chữ và số. |
| CSRF và form | Middleware CSRF và `ModelForm`/`Form` của Django | Mọi form POST có `{% csrf_token %}`. |
| Phân quyền | Decorator/mixin kiểm tra vai trò và chủ sở hữu ở mỗi view | NFR-SEC-09. Ẩn nút trên giao diện không thay thế kiểm tra quyền. |
| Tiến trình nền | Management command `python manage.py run_worker`, quét mỗi 5 giây **(chờ nhóm xác nhận)** | NFR-REL-06, BR-21: tự nộp bài hết hạn, chấm lại bài chờ chấm. Dùng `select_for_update(skip_locked=True)` để không xử lý trùng. |
| Cấu hình | Biến môi trường trong `.env` (đọc bằng `python-dotenv` trong `settings.py`), mẫu ở `.env.example` | NFR-SEC-10: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, thông tin DB không viết trong code. |
| Kiểm thử tự động | Django `TestCase` + test client, chạy `python manage.py test` | Django tự tạo database test trên PostgreSQL; tài khoản DB cần quyền tạo database. |
| Dữ liệu mẫu | Management command `python manage.py seed_demo` | Thay cho `database/seeds/seed_demo.py` sau khi chuyển schema. |

## 2. Kiến trúc và cấu trúc mã nguồn

Ứng dụng theo **mô hình MVT của Django, thêm một lớp service** cho quy tắc nghiệp vụ **(chờ nhóm xác nhận)**:

| Lớp | Vị trí | Trách nhiệm |
| --- | --- | --- |
| Model | `src/<app>/models.py` | Bảng, ràng buộc dữ liệu. |
| Service | `src/<app>/services.py` | Quy tắc nghiệp vụ BR-xx: khóa đăng nhập, phát hành đề, nộp bài, chấm điểm. Unit test chủ yếu ở lớp này. |
| View | `src/<app>/views.py` | Nhận request, kiểm tra phiên/quyền, gọi service, chọn template. Không viết quy tắc nghiệp vụ ở đây. |
| Template | `src/<app>/templates/<app>/` | Chỉ hiển thị dữ liệu. |

Dự kiến chia Django app:

| App | Trách nhiệm |
| --- | --- |
| `config` | `settings.py`, `urls.py`, cấu hình từ `.env`, trang `/health` |
| `accounts` | Custom User, đăng ký Student, đăng nhập/đăng xuất, khóa tạm, Admin quản lý tài khoản |
| `questions` | Ngân hàng câu hỏi và phương án |
| `exams` | Tạo đề, phát hành, phân công thí sinh |
| `attempts` | Làm bài, lưu đáp án, nộp bài, worker tự nộp |
| `results` | Chấm điểm, công bố, xem kết quả |

Cây thư mục mục tiêu:

```text
src/
  manage.py
  config/            # settings.py, urls.py, wsgi.py, asgi.py
  accounts/  questions/  exams/  attempts/  results/
    models.py  services.py  views.py  urls.py  forms.py
    templates/<app>/  migrations/  tests/
  templates/         # base.html, trang lỗi dùng chung
  static/
database/            # README hướng dẫn PostgreSQL + Docker
compose.yaml         # PostgreSQL 17
```

Mỗi app có `urls.py` riêng và phải được `include()` trong `config/urls.py`.

## 3. Quy ước dữ liệu

- Tên bảng và cột giữ như mô hình dữ liệu đã duyệt (mục 6 tài liệu đặc tả, S3-21): đặt `db_table` và `db_column` khi tên Django khác, ví dụ `users.user_id`, `users.full_name`, `users.password_hash`.
- Giá trị trạng thái viết HOA như đặc tả: `ADMIN`/`TEACHER`/`STUDENT`; `ACTIVE`/`LOCKED`/`DELETED`; `DRAFT`/`PUBLISHED`/`CLOSED`/`ARCHIVED`; `IN_PROGRESS`/`SUBMITTED`/`GRADED`. Khai báo bằng `models.TextChoices`.
- Ràng buộc CHECK, UNIQUE và chỉ mục khai báo trong `Meta.constraints` / `Meta.indexes`. Ràng buộc Django không biểu diễn được (khóa ngoại nhiều cột, ví dụ `submission_answers → answer_options(question_id, option_id)`) viết bằng `migrations.RunSQL` có cả câu lệnh đảo ngược.
- Khóa ngoại dùng `on_delete=models.PROTECT` để giữ lịch sử thi; không dùng `CASCADE` cho dữ liệu nghiệp vụ.
- `USE_TZ = True`, `TIME_ZONE = 'Asia/Ho_Chi_Minh'`: lưu UTC, hiển thị giờ Việt Nam.
- Email bỏ khoảng trắng đầu/cuối và chuyển chữ thường trước khi lưu.
- Mật khẩu tối thiểu 8 ký tự, có cả chữ và số (UC đăng ký, UC quản lý tài khoản).

## 4. Công cụ làm việc

| Công việc | Công cụ / định dạng |
| --- | --- |
| Quản lý phiên bản | Git, GitHub; làm việc qua branch và Pull Request theo [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md). |
| Theo dõi công việc và lỗi | Jira (dự án `CNPM`). |
| Vẽ DFD, Use Case, Class Diagram và mô hình dữ liệu | diagrams.net / draw.io; giữ file nguồn `.drawio` trong `docs/`. |
| Thiết kế giao diện | Figma; bản xuất trong `docs/Quiz-Examination-System-UI-Figma-Import/`. |
| Soạn và tổng hợp báo cáo | Microsoft Word (`.docx`); xuất PDF khi cần bàn giao. |
| Xem dữ liệu PostgreSQL | Beekeeper Studio hoặc DBeaver. |
| Tài liệu trong repo | Markdown (`.md`), mã hóa UTF-8 không BOM theo `.editorconfig`. |

Phân công thành viên nằm trong [kế hoạch dự án](PROJECT_PLAN.md).

## 5. Những điểm chưa chốt

- **Các mục có nhãn "chờ nhóm xác nhận"** ở mục 1 và 2.
- **Triển khai:** chưa chốt hosting, tên miền và cách đóng gói ứng dụng (hiện Docker chỉ dùng cho PostgreSQL).
- **Hiệu năng:** chưa đo tải 500 Student thi đồng thời theo NFR-PER-01.
- **Sao lưu và phục hồi:** chưa có quy trình theo NFR-REL-04.

## 6. Chuyển schema S3-21 từ Alembic sang Django

| Hiện tại (S3-21) | Sau khi chuyển |
| --- | --- |
| `alembic.ini`, `database/migrations/` | Xóa; schema nằm trong `src/<app>/migrations/` |
| `0001_create_business_tables.py` | Model của các app `accounts`, `questions`, `exams`, `attempts`, `results` cùng migration Django tương ứng |
| Trigger `updated_at` | `auto_now=True` |
| `database/seeds/seed_demo.py` | `python manage.py seed_demo` |
| `tests/integration/test_database.py` | Test ràng buộc trong `src/<app>/tests/` |
| `compose.yaml`, `.env.example`, `database/README.md` | Giữ, cập nhật lệnh chạy |

Việc chuyển do người phụ trách S3-21 làm, ngay sau khi khung Django merge. 37 tình huống dữ liệu sai trong test S3-21 phải được giữ lại trong test mới.

## 7. Cách triển khai với AI hỗ trợ

- Làm theo từng chức năng và FR / Use Case đã chốt; hoàn thành một luồng có giao diện, xử lý và lưu dữ liệu trước khi chuyển việc tiếp theo.
- Khi gửi yêu cầu cho AI, nêu rõ: Django, PostgreSQL, custom user `accounts.User`, tên bảng/cột và giá trị trạng thái ở mục 3, BR/NFR liên quan và tiêu chí nghiệm thu. Không để AI tự chọn framework hoặc database khác.
- Người nhận task đọc lại mã nguồn, chạy thử, viết và chạy test, rồi mới gửi Pull Request.
- Với phân quyền, chấm điểm, nộp bài và giới hạn giờ, kiểm tra ở phía máy chủ; giao diện chỉ hỗ trợ thao tác và hiển thị.
