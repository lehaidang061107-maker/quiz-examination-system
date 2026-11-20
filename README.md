# Quiz Examination System

<!-- toc -->

**Mục lục**

- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Project Structure](#project-structure)

<!-- /toc -->

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.
Công nghệ: Python + Django + PostgreSQL, kiến trúc MVC.

## Quick Start

Cần **Docker Desktop** đang mở. Ở thư mục dự án:

```bash
cp .env.example .env                                   # mở .env điền mật khẩu, xem bảng trong hướng dẫn cài đặt
docker compose up -d --build --wait
docker compose exec web python manage.py seed_demo
```

Mở http://127.0.0.1:8000/accounts/login/, đăng nhập bằng `student1@demo.example` hoặc `teacher@demo.example`
(mật khẩu là `DEMO_PASSWORD` trong `.env`). Chi tiết và cách chạy khi viết code: [database/README.md](database/README.md).

## Documentation

**Developer guides** (đọc theo thứ tự):

| # | File | Đọc khi |
| --- | --- | --- |
| 1 | [Getting Started](database/README.md) | Lần đầu cài; chạy bằng Docker hoặc Python; xem database; gặp lỗi khi chạy |
|  | [Seed Data](database/seeds/README.md) | Tài khoản mẫu và dữ liệu demo có sẵn |
| 2 | [Git Workflow](MEMBER_WORKFLOW.md) | Nhận task Jira → branch → PR → merge |
| 3 | [Coding Guidelines](TECH_STACK.md) | Công nghệ, MVC, cách viết một trang, sơ đồ lớp, quy tắc bắt buộc |
| 4 | [Testing](docs/testcases/README.md) | Unit test, thử trên trình duyệt, viết test case CSV |

**Project management:**

| File | Nội dung |
| --- | --- |
| [Project Plan](PROJECT_PLAN.md) | 4 giai đoạn, mốc M1–M4, rủi ro, sản phẩm nộp cuối |
| [Course Requirements](GUIDELINES.md) | Guidelines của môn, 7 phần tài liệu, công cụ gợi ý |
| [Database Verification](database/VERIFICATION.md) | Kết quả kiểm tra database |

Đặc tả (Word), sơ đồ `.drawio` và thiết kế Figma nằm trong [`docs/`](docs/).

## Project Structure

```text
quiz-examination-system/
├── src/                      Mã nguồn website (chạy lệnh manage.py ở đây)
│   ├── config/               Cấu hình Django, URL gốc, Trang chủ, menu theo vai trò
│   ├── accounts/             Tài khoản, đăng ký, đăng nhập, phân quyền; lệnh seed_demo, dev_login
│   ├── questions/            Ngân hàng câu hỏi
│   ├── exams/                Đề thi
│   ├── attempts/             Lượt làm bài
│   ├── results/              Kết quả, điểm
│   ├── templates/            Giao diện HTML: base.html, trang lỗi 403/404
│   └── static/css/           CSS chung (app.css)
├── database/                 Cài và xem database (README), dữ liệu mẫu (seeds/), kết quả kiểm tra (VERIFICATION.md)
├── docs/                     Đặc tả (Word), sơ đồ (.drawio), thiết kế Figma
│   └── testcases/            Hướng dẫn kiểm thử (README) và test case từng task: S3-xx.csv
├── tests/                    Kiểm thử tích hợp và hệ thống (giai đoạn 4)
├── scripts/                  Script hỗ trợ: gộp test case, cập nhật mục lục
├── Dockerfile, compose.yaml  Chạy website (web) và PostgreSQL (db) bằng Docker
├── requirements.txt          Thư viện Python
└── .env.example              Mẫu file .env (file .env thật không đưa lên GitHub)
```
