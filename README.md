# Quiz Examination System

<!-- toc -->

**Mục lục**

- [Chạy website](#chạy-website)
- [Kiểm thử](#kiểm-thử)
  - [Unit test](#unit-test)
  - [Chạy thử trên trình duyệt](#chạy-thử-trên-trình-duyệt)
- [Muốn làm gì thì đọc đâu](#muốn-làm-gì-thì-đọc-đâu)
- [Các thư mục](#các-thư-mục)

<!-- /toc -->

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.

**Hiện có:** tài liệu đặc tả và thiết kế; database 9 bảng kèm dữ liệu mẫu; các lớp theo sơ đồ lớp kèm phương thức nghiệp vụ và unit test; khung website Django. Kiến trúc: **MVC** (xem [TECH_STACK.md](TECH_STACK.md)).
**Chưa có:** các chức năng của website. Công nghệ: Python + Django + PostgreSQL.

## Chạy website

Làm trước phần "Lần đầu cài" trong [database/README.md](database/README.md) (cài thư viện,
điền `.env`, tạo bảng và dữ liệu mẫu). `.env` cần có `SECRET_KEY`, `DEBUG=True`,
`ALLOWED_HOSTS=localhost,127.0.0.1` (xem mẫu ở `.env.example`). Sau đó:

```bash
source .venv/bin/activate          # Windows: .venv\Scripts\activate
docker compose up -d --wait db
cd src
python manage.py runserver
```

Mở http://127.0.0.1:8000/health/ — thấy `{"status": "ok", "database": "ok"}` là chạy đúng.

## Kiểm thử

### Unit test

Trong thư mục `src` (PostgreSQL phải đang chạy), chạy `python manage.py test`; cuối kết quả có `OK` là đạt.
Chạy riêng một app: `python manage.py test accounts`.

### Chạy thử trên trình duyệt

Website đang chạy (`python manage.py runserver`, mục trên). **Đăng nhập tạm** khi chưa có trang Đăng nhập
(S3-03): mở terminal thứ hai, vào `src`, bật `.venv`, chạy

```bash
python manage.py dev_login teacher@demo.example     # hoặc admin@..., student1@..., student2@...
```

Lệnh in ra `sessionid = ...`. Trong Chrome: **F12 → Application → Cookies → `http://127.0.0.1:8000`**,
sửa (hoặc thêm) dòng tên `sessionid`, dán giá trị vừa in, rồi **F5**. Đổi tài khoản thì chạy lại lệnh với email khác.
Lệnh chỉ chạy khi `DEBUG=True`.

Kiểm tra thêm:

- Giao diện điện thoại: F12 → biểu tượng điện thoại (Toggle device toolbar) → khung **390 × 844** (NFR-USA-02).
- Trang lỗi 403/404 tiếng Việt chỉ hiện khi tắt DEBUG: `DEBUG=False python manage.py runserver --insecure`
  (`--insecure` để vẫn tải được CSS). Thử xong chạy lại bình thường.
- Sai quyền: đăng nhập vai trò khác rồi gõ thẳng URL trang không phải của mình, phải ra trang 403.
- Cần kiểm tra những gì: xem test case của từng task trong `docs/testcases/S3-xx.csv`.

## Muốn làm gì thì đọc đâu

| Muốn | Đọc |
| --- | --- |
| Biết công nghệ và quy tắc viết code | [TECH_STACK.md](TECH_STACK.md) |
| Cài và chạy database, xem bằng Beekeeper/DBeaver | [database/README.md](database/README.md) |
| Tài khoản và dữ liệu demo | [database/seeds/README.md](database/seeds/README.md) |
| Kết quả kiểm tra database | [database/VERIFICATION.md](database/VERIFICATION.md) |
| Cách viết test case nộp cho cô | [docs/testcases/README.md](docs/testcases/README.md) |
| Quy trình Git và Jira | [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md) |
| Kế hoạch các giai đoạn | [PROJECT_PLAN.md](PROJECT_PLAN.md) |
| Yêu cầu môn học | [GUIDELINES.md](GUIDELINES.md) |

## Các thư mục

| Thư mục | Chứa gì |
| --- | --- |
| `docs/` | Tài liệu đặc tả (Word), sơ đồ dữ liệu, sơ đồ lớp, thiết kế giao diện |
| `database/` | Hướng dẫn chạy database, dữ liệu mẫu, kết quả kiểm tra |
| `src/` | Mã nguồn website: `config/` (cấu hình, kiểm thử chung) và các app `accounts`, `questions`, `exams`, `attempts`, `results` (mỗi app có bảng và migration riêng) |
| `tests/` | Kiểm thử hệ thống (dùng ở giai đoạn 4) |

Cấu trúc bảng theo mục 6 tài liệu đặc tả và `docs/DataModel-Reviewed.drawio`.
Mật khẩu và thông tin kết nối riêng của mỗi máy để trong `.env`; chỉ đưa `.env.example` lên GitHub.
