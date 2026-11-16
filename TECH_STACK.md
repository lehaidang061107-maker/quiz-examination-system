# Công nghệ sử dụng

Website viết bằng **Python + Django**, dữ liệu lưu trong **PostgreSQL**.
Cả nhóm dùng chung bộ này; không tự chọn công nghệ khác (ví dụ Flask, SQLite).
Mục ghi **(chờ xác nhận)** là đề xuất, nhóm cần đồng ý trước khi áp dụng.

## 1. Dùng gì cho việc gì

| Việc | Dùng |
| --- | --- |
| Ngôn ngữ lập trình | Python 3.12 trở lên |
| Khung website | Django |
| Giao diện | Django Templates + Bootstrap 5, làm theo bản thiết kế Figma trong `docs/` |
| Lưu dữ liệu | PostgreSQL, chạy bằng Docker ([hướng dẫn](database/README.md)) |
| Tạo/sửa bảng dữ liệu | Django migrations |
| Đăng nhập, phiên, bảo mật form | Dùng sẵn của Django |
| Tự nộp bài khi hết giờ | Một chương trình chạy nền, kiểm tra mỗi 5 giây **(chờ xác nhận)** |
| Kiểm thử | `python manage.py test` |
| Mật khẩu, khóa bí mật | Ghi trong file `.env` trên máy mình, không đưa lên GitHub |

## 2. Code chia thành các phần

| Phần | Lo việc gì |
| --- | --- |
| `accounts` | Đăng ký, đăng nhập, khóa tài khoản, Admin quản lý tài khoản |
| `questions` | Ngân hàng câu hỏi |
| `exams` | Tạo đề, phát hành đề, giao đề cho sinh viên |
| `attempts` | Làm bài, lưu đáp án, nộp bài |
| `results` | Chấm điểm, công bố và xem kết quả |
| `config` | Cấu hình chung của website |

Trong mỗi phần, xử lý nghiệp vụ (ví dụ cách tính điểm) để riêng ở `services.py`,
không viết lẫn vào phần hiển thị **(chờ xác nhận)**.

## 3. Quy tắc bắt buộc khi viết code

- Đặt tên bảng, cột đúng như mô hình dữ liệu đã duyệt.
- Giá trị trạng thái viết HOA: `ADMIN`, `TEACHER`, `STUDENT`, `ACTIVE`, `LOCKED`…
- Không cho xóa dữ liệu đang được bài thi sử dụng, để giữ lịch sử.
- Giờ hiển thị theo giờ Việt Nam.
- Mật khẩu ít nhất 8 ký tự, có cả chữ và số.
- Kiểm tra quyền ở phía máy chủ; ẩn nút trên giao diện là chưa đủ.

## 4. Việc đang chờ

- Database hiện tạo bằng Alembic sẽ chuyển sang Django ngay sau khi dựng xong khung website.
  Trong lúc chờ, không ai tạo thêm bảng mới.
- Chưa chốt: phiên bản Django cụ thể, nơi đưa website lên mạng, cách đo khi 500 sinh viên thi cùng lúc, cách sao lưu dữ liệu.
