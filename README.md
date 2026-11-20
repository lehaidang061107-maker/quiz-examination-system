# Quiz Examination System

<!-- toc -->

**Mục lục**

- [Chạy website](#chạy-website)
  - [Cách 1: chạy toàn bộ bằng Docker](#cách-1-chạy-toàn-bộ-bằng-docker)
  - [Cách 2: chạy Python trên máy (khi viết code)](#cách-2-chạy-python-trên-máy-khi-viết-code)
- [Kiểm thử](#kiểm-thử)
  - [Unit test](#unit-test)
  - [Chạy thử trên trình duyệt](#chạy-thử-trên-trình-duyệt)
- [Muốn làm gì thì đọc đâu](#muốn-làm-gì-thì-đọc-đâu)
- [Các thư mục](#các-thư-mục)

<!-- /toc -->

Hệ thống thi trắc nghiệm của nhóm 04, môn Công nghệ phần mềm. Admin quản lý tài khoản,
giảng viên tạo câu hỏi và đề thi, sinh viên làm bài và xem kết quả.

**Hiện có:** tài liệu đặc tả và thiết kế; database 9 bảng kèm dữ liệu mẫu; chạy cả hệ thống bằng Docker; các lớp theo sơ đồ lớp kèm phương thức nghiệp vụ và unit test; khung website Django. Kiến trúc: **MVC** (xem [TECH_STACK.md](TECH_STACK.md)).
**Chưa có:** các chức năng của website. Công nghệ: Python + Django + PostgreSQL.

## Chạy website

Có hai cách. Muốn **xem/demo** thì dùng cách 1 (chỉ cần Docker Desktop). Muốn **viết code** thì dùng cách 2.

### Cách 1: chạy toàn bộ bằng Docker

Chỉ cần cài **Docker Desktop** và mở nó lên. Ở thư mục dự án:

1. Tạo file `.env`: `cp .env.example .env` (Windows: `copy .env.example .env`), mở ra điền
   `POSTGRES_PASSWORD`, `DEMO_PASSWORD`, `SECRET_KEY` như bảng ở bước 3 của
   [database/README.md](database/README.md#lần-đầu-làm-1-lần). Chưa có Python để tạo `SECRET_KEY`
   thì gõ tạm một chuỗi ngẫu nhiên dài khoảng 50 ký tự.
2. Chạy website và database (lần đầu mất vài phút để tải và build):

   ```bash
   docker compose up -d --build --wait
   ```

   Website tự tạo bảng (`migrate`) mỗi lần khởi động.
3. Tạo dữ liệu mẫu (chạy lại nhiều lần không bị trùng):

   ```bash
   docker compose exec web python manage.py seed_demo
   ```

Mở http://127.0.0.1:8000/health/ — thấy `{"status": "ok", "database": "ok"}` là chạy đúng.
Tài khoản mẫu xem ở [database/seeds/README.md](database/seeds/README.md); đăng nhập tạm xem mục
[Chạy thử trên trình duyệt](#chạy-thử-trên-trình-duyệt), thêm `docker compose exec web` trước lệnh `python manage.py ...`.

| Muốn | Lệnh |
| --- | --- |
| Xem log website | `docker compose logs -f web` |
| Sửa code xong, chạy lại bản mới | `docker compose up -d --build --wait` |
| Tắt (giữ dữ liệu) | `docker compose stop` |
| Xóa hết dữ liệu, làm lại từ đầu | `docker compose down -v`, rồi làm lại bước 2, 3 |
| Cổng 8000 đang bận | Thêm `WEB_PORT=8001` vào `.env`, mở http://127.0.0.1:8001 |

Website trong Docker chạy bằng `runserver` của Django, chỉ dùng cho máy cá nhân và buổi demo.

### Cách 2: chạy Python trên máy (khi viết code)

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
Đang chạy website bằng Docker (cách 1) thì tắt trước: `docker compose stop web`.

## Kiểm thử

### Unit test

Trong thư mục `src` (PostgreSQL phải đang chạy), chạy `python manage.py test`; cuối kết quả có `OK` là đạt.
Chạy riêng một app: `python manage.py test accounts`.

### Chạy thử trên trình duyệt

Website đang chạy (`python manage.py runserver`, mục trên). Mở `http://127.0.0.1:8000/accounts/login/` và đăng nhập
bằng tài khoản demo (bảng trong [`docs/testcases/README.md`](docs/testcases/README.md#dữ-liệu-dùng-khi-kiểm-thử)).
Muốn tạo Student mới thì bấm **Đăng ký ngay** ở trang Đăng nhập. Đổi tài khoản: bấm **Đăng xuất** trên thanh menu.

Đổi vai trò nhanh mà không gõ mật khẩu (chỉ khi `DEBUG=True`): mở terminal thứ hai, vào `src`, bật `.venv`, chạy

```bash
python manage.py dev_login teacher@demo.example     # hoặc admin@..., teacher2@..., student1@... đến student3@...
```

Lệnh in ra `sessionid = ...`. Trong Chrome: **F12 → Application → Cookies → `http://127.0.0.1:8000`**,
sửa (hoặc thêm) dòng tên `sessionid`, dán giá trị vừa in, rồi **F5**.

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

```text
quiz-examination-system/
├── src/                      Mã nguồn website (chạy lệnh manage.py ở đây)
│   ├── config/               Cấu hình Django, URL gốc, menu theo vai trò, test chung
│   ├── accounts/             Tài khoản, phân quyền; lệnh seed_demo, dev_login
│   ├── questions/            Ngân hàng câu hỏi
│   ├── exams/                Đề thi
│   ├── attempts/             Lượt làm bài
│   ├── results/              Kết quả, điểm
│   ├── templates/            Giao diện HTML: base.html, trang lỗi 403/404
│   └── static/css/           CSS chung (app.css)
├── database/                 Hướng dẫn cài và xem database, kết quả kiểm tra (VERIFICATION.md)
├── docs/                     Đặc tả (Word), sơ đồ dữ liệu / lớp / use case (.drawio), thiết kế Figma
│   └── testcases/            Test case từng task: S3-xx.csv
├── tests/                    Kiểm thử tích hợp và hệ thống (giai đoạn 4)
├── scripts/                  Script hỗ trợ: tạo file test case, cập nhật mục lục
├── Dockerfile                Đóng gói website Django (Python 3.12)
├── compose.yaml              Chạy website (web) và PostgreSQL (db) bằng Docker
├── requirements.txt          Thư viện Python
└── .env.example              Mẫu file .env
```

Mỗi app trong `src/` có `models.py`, `migrations/` và `tests/` riêng.

Cấu trúc bảng theo mục 6 tài liệu đặc tả và `docs/DataModel-Reviewed.drawio`.
Mật khẩu và thông tin kết nối riêng của mỗi máy để trong `.env`; chỉ đưa `.env.example` lên GitHub.
