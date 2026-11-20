# Quiz Examination System

<!-- toc -->

**Mục lục**

- [Chạy nhanh](#chạy-nhanh)
- [Tài liệu](#tài-liệu)
- [Các thư mục](#các-thư-mục)

<!-- /toc -->

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.
Công nghệ: Python + Django + PostgreSQL, kiến trúc MVC.

## Chạy nhanh

Cần **Docker Desktop** đang mở. Ở thư mục dự án:

```bash
cp .env.example .env                                   # mở .env điền mật khẩu, xem bảng trong hướng dẫn cài đặt
docker compose up -d --build --wait
docker compose exec web python manage.py seed_demo
```

Mở http://127.0.0.1:8000/accounts/login/, đăng nhập bằng `student1@demo.example` hoặc `teacher@demo.example`
(mật khẩu là `DEMO_PASSWORD` trong `.env`). Chi tiết và cách chạy khi viết code:
[docs/huong-dan/1-cai-dat-va-chay.md](docs/huong-dan/1-cai-dat-va-chay.md).

## Tài liệu

**Thành viên** đọc theo thứ tự:

| # | File | Đọc khi |
| --- | --- | --- |
| 1 | [Cài đặt và chạy](docs/huong-dan/1-cai-dat-va-chay.md) | Lần đầu cài; tài khoản mẫu; xem database; gặp lỗi khi chạy |
| 2 | [Quy trình làm task](docs/huong-dan/2-quy-trinh-lam-task.md) | Nhận task Jira → branch → PR → merge |
| 3 | [Viết code](docs/huong-dan/3-viet-code.md) | Công nghệ, MVC, cách viết một trang, sơ đồ lớp, quy tắc bắt buộc |
| 4 | [Kiểm thử](docs/huong-dan/4-kiem-thu.md) | Unit test, thử trên trình duyệt, viết test case CSV |

**PM / nộp bài:**

| File | Nội dung |
| --- | --- |
| [Kế hoạch](docs/quan-ly/ke-hoach.md) | 4 giai đoạn, mốc M1–M4, rủi ro, sản phẩm nộp cuối |
| [Yêu cầu môn học](docs/quan-ly/yeu-cau-mon-hoc.md) | Guidelines của môn, 7 phần tài liệu, công cụ gợi ý |
| [Kiểm tra database](docs/quan-ly/kiem-tra-database.md) | Kết quả kiểm tra database |

Đặc tả (Word), sơ đồ `.drawio` và thiết kế Figma nằm trong [`docs/`](docs/).

## Các thư mục

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
├── docs/
│   ├── huong-dan/            Hướng dẫn cho thành viên (4 file đánh số)
│   ├── quan-ly/              Kế hoạch, yêu cầu môn học, kết quả kiểm tra
│   ├── testcases/            Test case từng task: S3-xx.csv
│   └── ...                   Đặc tả (Word), sơ đồ (.drawio), thiết kế Figma
├── tests/                    Kiểm thử tích hợp và hệ thống (giai đoạn 4)
├── scripts/                  Script hỗ trợ: gộp test case, cập nhật mục lục
├── Dockerfile, compose.yaml  Chạy website (web) và PostgreSQL (db) bằng Docker
├── requirements.txt          Thư viện Python
└── .env.example              Mẫu file .env (file .env thật không đưa lên GitHub)
```
