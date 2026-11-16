# Dữ liệu mẫu

Dữ liệu mẫu cho nhóm có sẵn tài khoản, câu hỏi, đề thi để xem và thử, không phải tự nhập.
Chỉ dùng trên database của máy mình hoặc máy demo.

Tạo bằng lệnh (sau khi đã cài database theo [hướng dẫn](../README.md)):

```bash
cd src
python manage.py seed_demo
```

Code của lệnh nằm ở `src/accounts/management/commands/seed_demo.py`.

## Tài khoản mẫu

Mật khẩu cả 4 tài khoản là `DEMO_PASSWORD` trong file `.env` (ít nhất 8 ký tự, có cả chữ và số,
khác mật khẩu database), được lưu dạng mã hóa. Đăng nhập bằng email.

| Vai trò | Email |
| --- | --- |
| Quản trị viên | `admin@demo.example` |
| Giảng viên | `teacher@demo.example` |
| Sinh viên | `student1@demo.example`, `student2@demo.example` |

## Có sẵn những gì

- 3 câu hỏi hoàn chỉnh (mỗi câu 3 lựa chọn, 1 đáp án đúng) và 1 câu nháp.
- 4 đề: nháp, đang mở (mở 30 ngày), đã đóng chờ chấm, đã công bố điểm. Cả 2 sinh viên được giao cả 4 đề.
- 4 lượt làm: 1 đang làm (hạn 30 phút), 1 chờ chấm, 2 đã chấm. Có đủ trường hợp đáp án đúng, sai, bỏ trống, chưa trả lời.
- Điểm: sinh viên một 6/6, sinh viên hai 2/6.

## Chạy lại có sao không

- Chạy lại **không** thêm trùng, không đổi dữ liệu hay mật khẩu đã có, không gia hạn lịch thi.
- Đổi `DEMO_PASSWORD` rồi chạy lại cũng không đổi mật khẩu tài khoản đã tạo.
- Nếu dữ liệu mẫu bị sửa dở dang, lệnh dừng lại để không ghi đè. Muốn bộ mới hoàn toàn: làm lại database từ đầu (xem [hướng dẫn](../README.md)).
