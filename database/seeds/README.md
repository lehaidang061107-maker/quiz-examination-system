# Seed Data

<!-- toc -->

**Mục lục**

- [Demo Accounts](#demo-accounts)
- [Fixtures](#fixtures)
- [Re-running `seed_demo`](#re-running-seed_demo)

<!-- /toc -->

Dữ liệu mẫu để xem và thử, không phải tự nhập. Chỉ dùng trên database của máy mình hoặc máy demo.
Tạo bằng `python manage.py seed_demo` (trong `src`) hoặc `docker compose exec web python manage.py seed_demo`
(cài đặt xem [Getting Started](../README.md)).

## Demo Accounts

Lệnh `seed_demo` tạo 6 tài khoản, mật khẩu đều là `DEMO_PASSWORD` trong `.env`:

| Vai trò | Email |
| --- | --- |
| Admin | `admin@demo.example` |
| Teacher | `teacher@demo.example` (có đề thi, bài làm), `teacher2@demo.example` (chỉ có câu hỏi) |
| Student | `student1@demo.example`, `student2@demo.example`, `student3@demo.example` |

## Fixtures

- Câu hỏi: `teacher@` có 3 câu hoàn chỉnh, `teacher2@` có 2 câu (mỗi câu 3 lựa chọn, 1 đáp án đúng); mỗi giảng viên thêm 1 câu nháp.
- 4 đề của `teacher@`: nháp, đang mở (mở 30 ngày), đã đóng chờ chấm, đã công bố điểm.
  `student1`, `student2` được giao cả 4 đề; `student3` được giao đề nháp và đề đang mở, chưa làm bài nào.
- 4 lượt làm: 1 đang làm (hạn 30 phút), 1 chờ chấm, 2 đã chấm; đủ trường hợp đáp án đúng, sai, bỏ trống.
- Điểm: `student1` 6/6, `student2` 2/6.

## Re-running `seed_demo`

Chạy lại `seed_demo` **không** thêm trùng, không đổi mật khẩu hay dữ liệu đã có (kể cả khi đổi `DEMO_PASSWORD`),
chỉ tạo phần còn thiếu. Nếu dữ liệu mẫu bị xóa dở hoặc email mẫu đang thuộc vai trò khác, lệnh dừng lại để không ghi đè.
Code của lệnh: `src/accounts/management/commands/seed_demo.py`.
