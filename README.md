# Quiz Examination System

Dự án hệ thống thi trắc nghiệm của nhóm 5 thành viên, thực hiện trong môn Công nghệ phần mềm.

## Trạng thái hiện tại

Dự án đang ở bước chuẩn bị tài liệu và kế hoạch thực hiện.

- **Đã có:** guidelines môn học, kế hoạch theo giai đoạn, bộ công nghệ đã thống nhất, quy trình Git/Jira và khung thư mục / file để nhóm bắt đầu làm việc.
- **Chức năng đã triển khai:** chưa có.
- **Mã nguồn ứng dụng, bản demo và hướng dẫn chạy:** chưa có.

## Công nghệ đã chốt

Python + Django, giao diện Django Templates + Bootstrap, JavaScript cơ bản, Django Authentication dùng session, Django ORM và SQLite cho bản đầu / demo nhỏ. Kiểm thử bằng Django TestCase và test client.

Chi tiết lựa chọn, công cụ làm việc và các điểm còn cần thống nhất nằm trong [TECH_STACK.md](TECH_STACK.md).

## Tài liệu dự án

| Tài liệu | Nội dung |
| --- | --- |
| [Guidelines](GUIDELINES.md) | Yêu cầu môn học, bốn giai đoạn thực hiện và cấu trúc tài liệu cần nộp. |
| [Kế hoạch dự án](PROJECT_PLAN.md) | Công việc, phân công đề xuất cho 5 thành viên, sản phẩm bàn giao và tiêu chí hoàn thành. |
| [Công nghệ và công cụ](TECH_STACK.md) | Bộ công nghệ đã chốt, cách tổ chức ứng dụng và các quyết định còn mở. |
| [Quy trình thành viên](MEMBER_WORKFLOW.md) | Cách nhận task trên Jira, làm việc với Git và gửi Pull Request. |
| [Hướng dẫn tổ chức tài liệu](docs/README.md) | Nơi làm việc của từng thành viên, file nội dung, sơ đồ và bản bàn giao. |

## Cấu trúc repository

```text
CNPM-Quiz/
├── README.md
├── GUIDELINES.md
├── PROJECT_PLAN.md
├── TECH_STACK.md
├── MEMBER_WORKFLOW.md
├── docs/
│   ├── README.md
│   ├── 01-analysis/         # Tổng quan, FR, NFR, đặc tả Use Case
│   ├── 02-design/           # Kiến trúc, dữ liệu, giao diện và nguồn UI
│   ├── 03-implementation/   # Hướng dẫn thiết lập và chạy
│   ├── 04-testing/          # Test case, lỗi, báo cáo và kết quả kiểm thử
│   ├── diagrams/            # DFD, Use Case, Class Diagram, Data Model
│   └── deliverables/        # Bản Word / PDF giai đoạn 1 và cuối dự án
├── src/                    # Mã nguồn ứng dụng
├── tests/                  # Unit, integration và system test
└── database/               # Schema, migration và dữ liệu mẫu
```

Các file phân tích, thiết kế và kiểm thử chủ yếu là khung để điền; các thư mục mã nguồn và kiểm thử chưa có triển khai. Cấu trúc bên trong `src/` sẽ được hoàn thiện theo Django khi dựng ứng dụng.
