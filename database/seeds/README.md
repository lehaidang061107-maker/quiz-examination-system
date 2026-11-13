# Dữ liệu mẫu để xem thử

Seed là lệnh thêm dữ liệu ví dụ vào database. Dùng để nhóm xem và kiểm tra các bảng
trước khi có website hoàn chỉnh. Chỉ chạy trên database phát triển hoặc demo.

## Cách chạy

Sau khi đã thiết lập database theo [hướng dẫn chính](../README.md), mở Terminal
ở thư mục dự án và chạy:

```bash
source .venv/bin/activate
alembic upgrade head
python database/seeds/seed_demo.py
```

Trong `.env` phải có `DEMO_PASSWORD` dài ít nhất 6 ký tự. Đây là mật khẩu tài khoản
demo, khác với `POSTGRES_PASSWORD` dùng để kết nối PostgreSQL.
Mật khẩu trong bảng `users` được lưu dưới dạng băm scrypt qua Werkzeug; không lưu
mật khẩu đọc được. Xem [tài liệu Werkzeug](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash).

## Tài khoản mẫu

| Vai trò | Email |
| --- | --- |
| Admin — quản trị viên | `admin@demo.example` |
| Teacher — giảng viên | `teacher@demo.example` |
| Student — sinh viên một | `student1@demo.example` |
| Student — sinh viên hai | `student2@demo.example` |

Cả 4 dùng mật khẩu `DEMO_PASSWORD` tại lần tạo đầu. Chưa có giao diện đăng nhập;
các tài khoản đang được lưu sẵn để các task tiếp theo sử dụng.

## Có gì để kiểm tra?

- 3 câu hỏi sẵn dùng, mỗi câu 3 lựa chọn và đúng 1 đáp án đúng; 1 câu nháp trống.
- 4 đề: nháp, đang mở, đã đóng/chờ chấm và đã công bố kết quả.
- Hai sinh viên được giao cả 4 đề, có trường hợp chưa bắt đầu làm.
- 4 lượt làm: 1 đang làm, 1 chờ chấm, 2 đã chấm; mỗi sinh viên chỉ có 1 lượt cho mỗi đề.
- Đáp án có ví dụ đúng, sai, bỏ chọn và chưa trả lời.
- Sinh viên một được **6/6**; sinh viên hai được **2/6** (1 đúng, 1 sai, 1 bỏ trống).

| Bảng | Số dòng sau lần tạo đầu |
| --- | ---: |
| users | 4 |
| questions | 4 |
| answer_options | 9 |
| exams | 4 |
| exam_questions | 12 |
| exam_participants | 8 |
| submissions | 4 |
| submission_answers | 10 |
| results | 2 |

## Chạy lại có mất dữ liệu không?

Không. Nếu nhận ra bộ demo cũ, lệnh giữ nguyên dữ liệu, ID và mật khẩu.
Đổi `.env` rồi chạy lại seed không đổi mật khẩu tài khoản đã tạo.
Nếu lỗi giữa chừng, toàn bộ lần tạo đó được hoàn tác; hai lần chạy đồng thời được
xử lý lần lượt. Nếu email demo bị chiếm một phần hoặc thiếu bộ đề đánh dấu demo,
lệnh dừng để tránh ghi đè.

Seed nhận diện demo cũ bằng 4 email và 4 đề; không tự sửa dữ liệu bạn đã chỉnh/xóa.
Muốn bộ demo mới hoàn toàn, dùng database phát triển mới. Seed hiện dành cho
migration `0001`; người phát triển cần cập nhật khi mô hình thay đổi.

Đề đang mở có lịch 30 ngày kể từ lần tạo đầu, lượt đang làm có hạn 30 phút.
Chạy lại seed không dời lịch hoặc gia hạn. Tự nộp bài quá hạn và chấm điểm thật
thuộc các task ứng dụng tiếp theo.
