# Quiz Examination System

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.

**Hiện có:** tài liệu đặc tả và thiết kế; database 9 bảng kèm dữ liệu mẫu và kiểm thử.
**Chưa có:** website. Công nghệ: Python + Django + PostgreSQL.

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
| `src/` | Mã nguồn website |

Cấu trúc bảng theo mục 6 tài liệu đặc tả và `docs/DataModel-Reviewed.drawio`.
Mật khẩu và thông tin kết nối riêng của mỗi máy để trong `.env`; chỉ đưa `.env.example` lên GitHub.
