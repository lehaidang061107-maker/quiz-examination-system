# Công nghệ sử dụng

Website viết bằng **Python + Django**, dữ liệu lưu trong **PostgreSQL**.
Cả nhóm dùng chung bộ này; không tự chọn công nghệ khác (ví dụ Flask, SQLite).
Mục ghi **(chờ xác nhận)** là đề xuất, nhóm cần đồng ý trước khi áp dụng.

## 1. Dùng gì cho việc gì

| Việc | Dùng | Ghi chú |
| --- | --- | --- |
| Ngôn ngữ | Python 3.12 – 3.14 | Các bản Django 5.2 hỗ trợ |
| Khung website | Django 5.2 (bản hỗ trợ dài hạn, tới 4/2028) | Ghi bản cụ thể trong `requirements.txt`, hiện là `Django==5.2.19` |
| Giao diện | Django Templates + Bootstrap 5 | Làm theo bản Figma trong `docs/` |
| Lưu dữ liệu | PostgreSQL 17, chạy bằng Docker | [Hướng dẫn](database/README.md). Không dùng SQLite, kể cả khi test |
| Tạo/sửa bảng | Django migrations | Chạy `makemigrations`, đọc lại file sinh ra; không sửa migration đã merge |
| Tài khoản | Model `accounts.User` riêng, đăng nhập bằng email, lưu ở bảng `users` | Phải có trước lần `migrate` đầu tiên |
| Đăng nhập, phiên | Có sẵn của Django, phiên lưu trong database | Tự đăng xuất sau 30 phút không hoạt động; tài khoản bị khóa mất phiên ngay |
| Khóa tạm khi nhập sai | Tự viết | Sai 5 lần liên tiếp thì khóa 15 phút; khác với Admin khóa tài khoản |
| Mật khẩu | Mã hóa có sẵn của Django | Ít nhất 8 ký tự, có cả chữ và số |
| Chống giả mạo form (CSRF) | Có sẵn của Django | Mọi form gửi đi có `{% csrf_token %}` |
| Tự nộp bài khi hết giờ | Lệnh chạy nền `python manage.py run_worker`, kiểm tra mỗi 5 giây **(chờ xác nhận)** | Khóa từng bài khi xử lý để không nộp/chấm trùng |
| Kiểm thử | `python manage.py test` | Django tự tạo database thử riêng, không đụng dữ liệu thật |
| Cấu hình bí mật | File `.env` trên máy mình (mẫu: `.env.example`) | `SECRET_KEY`, mật khẩu không viết trong code, không đưa lên GitHub |

## 2. Code chia thành các phần

| Phần (app) | Lo việc gì |
| --- | --- |
| `config` | Cấu hình chung, đường dẫn gốc, trang `/health` kiểm tra website còn chạy |
| `accounts` | Đăng ký Student, đăng nhập/đăng xuất, khóa tạm, Admin quản lý tài khoản |
| `questions` | Ngân hàng câu hỏi và phương án |
| `exams` | Tạo đề, phát hành đề, giao đề cho sinh viên |
| `attempts` | Làm bài, tự lưu đáp án, nộp bài, tự nộp khi hết giờ |
| `results` | Chấm điểm, công bố và xem kết quả |

Mỗi phần có `urls.py` riêng và phải được khai báo trong `config/urls.py`, nếu không trang sẽ báo 404.
Trong mỗi phần: `views.py` nhận yêu cầu và kiểm tra quyền → `services.py` xử lý nghiệp vụ (tính điểm,
khóa tài khoản…) → `models.py` lưu dữ liệu **(chờ xác nhận)**.

## 3. Quy tắc bắt buộc khi viết code

- Tên bảng, cột đúng như mô hình dữ liệu đã duyệt (ví dụ `users.user_id`, `full_name`, `password_hash`).
- Trạng thái viết HOA: `ADMIN`/`TEACHER`/`STUDENT`; `ACTIVE`/`LOCKED`/`DELETED`; `DRAFT`/`PUBLISHED`/`CLOSED`/`ARCHIVED`; `IN_PROGRESS`/`SUBMITTED`/`GRADED`.
- Không cho xóa dữ liệu đang được bài thi dùng (khóa ngoại `PROTECT`), để giữ lịch sử.
- Lưu giờ chuẩn quốc tế (UTC), hiển thị giờ Việt Nam.
- Email bỏ khoảng trắng, đổi chữ thường trước khi lưu.
- Kiểm tra quyền ở phía máy chủ; ẩn nút trên giao diện là chưa đủ.
- Không chèn dữ liệu người dùng nhập vào JavaScript trong HTML (`onclick="...{{ }}..."`), tránh bị chèn mã độc.

## 4. Việc chưa quyết định

| Việc | Cần quyết định gì |
| --- | --- |
| Đưa website lên mạng | Chỉ demo trên máy cá nhân, hay thuê máy chủ để truy cập qua Internet |
| Thử tải | Cách kiểm tra website chịu được 500 sinh viên thi cùng lúc như đặc tả yêu cầu |
| Sao lưu | Cách sao lưu dữ liệu hằng ngày và khôi phục khi có sự cố |
