# Dữ liệu mẫu

Dữ liệu mẫu giúp nhóm có sẵn tài khoản, câu hỏi, đề thi để xem và thử, không phải tự nhập.

Tạo bằng lệnh (sau khi đã cài database theo [hướng dẫn](../README.md)):

```bash
python database/seeds/seed_demo.py
```

## Tài khoản mẫu

Mật khẩu của cả 4 tài khoản là giá trị `DEMO_PASSWORD` bạn điền trong file `.env`.

| Vai trò | Email |
| --- | --- |
| Quản trị viên | `admin@demo.example` |
| Giảng viên | `teacher@demo.example` |
| Sinh viên | `student1@demo.example`, `student2@demo.example` |

## Có sẵn những gì

- 4 câu hỏi (3 câu hoàn chỉnh, 1 câu nháp).
- 4 đề thi: đề nháp, đề đang mở, đề chờ chấm, đề đã công bố điểm.
- Bài làm mẫu: sinh viên một được 6/6, sinh viên hai được 2/6.

Chạy lại lệnh nhiều lần cũng không bị trùng dữ liệu.
