# Quiz Examination System

Dự án hệ thống thi trắc nghiệm của nhóm 04 trong môn Công nghệ phần mềm.
Giảng viên chuẩn bị đề, sinh viên làm bài và xem kết quả, quản trị viên quản lý tài khoản.

## Hiện tại đã có gì?

- Tài liệu đặc tả, sơ đồ dữ liệu và bản thiết kế giao diện.
- PostgreSQL với migration tạo đủ 9 bảng và dữ liệu mẫu cho task **S3-21**.
- Kiểm thử database và hướng dẫn chạy, xem dữ liệu, quay lui khi cần.

Website đăng nhập và làm bài chưa được triển khai. Theo tổng quan giai đoạn 3,
định hướng là **Python + Flask + PostgreSQL**. Một số tài liệu kế hoạch cũ vẫn ghi
Django + SQLite; khi triển khai tiếp cần đối chiếu với tài liệu giai đoạn 3.

## Bắt đầu từ đâu?

| Bạn muốn làm gì? | Đọc ở đâu? |
| --- | --- |
| Cài và chạy database, xem bằng Beekeeper/DBeaver | [Hướng dẫn database cho người mới](database/README.md) |
| Biết tài khoản và dữ liệu demo | [Dữ liệu mẫu](database/seeds/README.md) |
| Xem phần database đã được kiểm tra ra sao | [Kết quả kiểm thử](database/VERIFICATION.md) |
| Biết cách làm việc qua Git và Jira | [Quy trình thành viên](MEMBER_WORKFLOW.md) |
| Đọc yêu cầu môn học | [Guidelines](GUIDELINES.md) |
| Xem kế hoạch nhóm | [Kế hoạch dự án](PROJECT_PLAN.md) |

## Các thư mục chính

| Thư mục | Nội dung |
| --- | --- |
| `docs/` | Đặc tả Word, mô hình dữ liệu, sơ đồ lớp, thiết kế giao diện |
| `database/migrations/` | Các phiên bản tạo/cập nhật bảng |
| `database/seeds/` | Lệnh tạo dữ liệu mẫu |
| `tests/integration/` | Kiểm thử trực tiếp với PostgreSQL |
| `src/` | Nơi triển khai mã nguồn ứng dụng tiếp theo |

Cấu trúc bảng bám mục 6 trong tài liệu đặc tả và `docs/DataModel-Reviewed.drawio`.
Thông tin kết nối riêng của mỗi máy nằm trong `.env`; chỉ đưa `.env.example`
lên Git, không đưa mật khẩu thật lên repository.
