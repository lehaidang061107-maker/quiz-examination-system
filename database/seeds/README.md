# Dữ liệu mẫu

<!-- toc -->

**Mục lục**

- [Tài khoản mẫu](#tài-khoản-mẫu)
- [Có sẵn những gì](#có-sẵn-những-gì)
- [Chạy lại có sao không](#chạy-lại-có-sao-không)

<!-- /toc -->

Dữ liệu mẫu cho nhóm có sẵn tài khoản, câu hỏi, đề thi để xem và thử, không phải tự nhập.
Chỉ dùng trên database của máy mình hoặc máy demo.

Tạo bằng lệnh (sau khi đã cài database theo [hướng dẫn](../README.md)):

```bash
cd src
python manage.py seed_demo
```

Chạy website bằng Docker thì dùng: `docker compose exec web python manage.py seed_demo`.

Code của lệnh nằm ở `src/accounts/management/commands/seed_demo.py`.

## Tài khoản mẫu

Mật khẩu cả 6 tài khoản là `DEMO_PASSWORD` trong file `.env` (ít nhất 8 ký tự, có cả chữ và số,
khác mật khẩu database), được lưu dạng mã hóa. Đăng nhập bằng email.

| Vai trò | Email |
| --- | --- |
| Quản trị viên | `admin@demo.example` |
| Giảng viên | `teacher@demo.example` (có đề thi, bài làm), `teacher2@demo.example` (chỉ có câu hỏi) |
| Sinh viên | `student1@demo.example`, `student2@demo.example`, `student3@demo.example` |

## Có sẵn những gì

- Ngân hàng câu hỏi: `teacher@` có 3 câu hoàn chỉnh, `teacher2@` có 2 câu (mỗi câu 3 lựa chọn, 1 đáp án đúng); mỗi giảng viên thêm 1 câu nháp.
- 4 đề của `teacher@`: nháp, đang mở (mở 30 ngày), đã đóng chờ chấm, đã công bố điểm. Sinh viên một, hai được giao cả 4 đề;
  sinh viên ba được giao đề nháp và đề đang mở, chưa làm bài nào.
- 4 lượt làm: 1 đang làm (hạn 30 phút), 1 chờ chấm, 2 đã chấm. Có đủ trường hợp đáp án đúng, sai, bỏ trống, chưa trả lời.
- Điểm: sinh viên một 6/6, sinh viên hai 2/6.

## Chạy lại có sao không

- Chạy lại **không** thêm trùng, không đổi dữ liệu hay mật khẩu đã có, không gia hạn lịch thi.
- Phần nào còn thiếu thì được tạo thêm. Ví dụ database đã seed bằng bản cũ (4 tài khoản) chạy lại sẽ có thêm
  `teacher2@`, `student3@` và câu hỏi của `teacher2@`; riêng 4 đề cũ giữ nguyên nên `student3@` chưa được giao đề nào.
- Đổi `DEMO_PASSWORD` rồi chạy lại cũng không đổi mật khẩu tài khoản đã tạo.
- Nếu bộ đề mẫu bị xóa dở dang, hoặc email mẫu đang thuộc vai trò khác, lệnh dừng lại để không ghi đè. Muốn bộ mới hoàn toàn: làm lại database từ đầu (xem [hướng dẫn](../README.md)).
