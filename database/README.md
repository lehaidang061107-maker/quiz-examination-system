# Hướng dẫn chạy database

Database lưu tài khoản, câu hỏi, đề thi, bài làm và điểm. Nó chạy trong Docker
(phần mềm giúp chạy database trên máy mà không phải cài đặt phức tạp). Mỗi máy có database riêng;
nhóm chỉ chia sẻ cách tạo bảng (Django migrations trong `src/<app>/migrations/`) và dữ liệu mẫu qua GitHub.

## Lần đầu cài

Cần cài sẵn **Python 3.12–3.14** và **Docker Desktop** (mở Docker Desktop trước). Mở Terminal tại thư mục dự án:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # chỉ chạy khi chưa có .env, nếu không sẽ ghi đè
```

Mở `.env`, điền theo hướng dẫn trong file: `POSTGRES_PASSWORD` (mật khẩu database), `DEMO_PASSWORD`
(mật khẩu tài khoản demo, ít nhất 8 ký tự, có cả chữ và số) và `SECRET_KEY`. Lưu file, rồi chạy:

```bash
docker compose up -d --wait db     # bật database, chờ báo Healthy
cd src
python manage.py migrate           # tạo bảng
python manage.py seed_demo         # tạo dữ liệu mẫu
```

Thấy báo "Đã tạo dữ liệu demo" là xong.

## Đã cài database bản cũ (Alembic)

Bảng cũ tạo bằng Alembic không dùng chung được với Django. Làm **một lần** để xóa database cũ
(chỉ mất dữ liệu demo) rồi tạo lại:

```bash
docker compose down -v
docker compose up -d --wait db
cd src
python manage.py migrate
python manage.py seed_demo
```

Kết nối Beekeeper giữ nguyên, chỉ cần bấm Refresh.

## Những lần sau

```bash
source .venv/bin/activate
docker compose up -d --wait db
cd src
python manage.py migrate           # an toàn, chỉ áp dụng thay đổi mới
```

Tắt: `docker compose stop db` (giữ dữ liệu). **Không chạy `docker compose down -v`** trừ khi muốn xóa hết dữ liệu.

## Xem dữ liệu bằng Beekeeper hoặc DBeaver

Tạo kết nối **PostgreSQL** (tắt SSL và SSH). MySQL Workbench không dùng được.

| Ô | Giá trị |
| --- | --- |
| Host / Port | `127.0.0.1` / `55433` |
| User | `quiz_app` |
| Database | `quiz_examination` |
| Password | `POSTGRES_PASSWORD` trong `.env` (không phải mật khẩu demo) |

| Bảng | Lưu gì |
| --- | --- |
| `users` | Tài khoản, vai trò, số lần đăng nhập sai |
| `questions`, `answer_options` | Câu hỏi, các lựa chọn và đáp án đúng |
| `exams`, `exam_questions` | Đề thi (lịch, thời lượng); câu nào trong đề, thứ tự, điểm |
| `exam_participants` | Sinh viên được giao đề |
| `submissions`, `submission_answers` | Lượt làm bài; đáp án sinh viên chọn |
| `results` | Điểm, số câu đúng |

Các bảng bắt đầu bằng `django_` hoặc `auth_` là của Django (phiên đăng nhập, lịch sử migration…).

## Kiểm tra và làm lại từ đầu

```bash
cd src
python manage.py test              # cuối kết quả có OK là đạt
```

Kiểm thử chạy trên database tạm riêng, không đụng dữ liệu bạn đang dùng.
Muốn xóa hết rồi tạo lại (mất toàn bộ dữ liệu): làm như mục "Đã cài database bản cũ".

## Gặp lỗi

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` hoặc `django` | Chạy lại lệnh `activate` và `pip install -r requirements.txt` |
| Không kết nối được | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| `password authentication failed` | Mật khẩu trong `.env` không khớp database (xem bên dưới) |
| `relation "users" already exists` | Đang còn bảng bản cũ: làm mục "Đã cài database bản cũ" |
| Báo `DEMO_PASSWORD chưa hợp lệ` | Đặt mật khẩu ít nhất 8 ký tự, có cả chữ và số, không quá phổ biến |
| Báo "demo đã tồn tại" | Bình thường, dữ liệu cũ được giữ |

**Sửa `.env` không tự đổi mật khẩu database.** Muốn đổi: chạy
`docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`, gõ `\password quiz_app`,
nhập mật khẩu mới hai lần, gõ `\q`, rồi sửa `POSTGRES_PASSWORD` trong `.env` cho khớp.

## Dành cho người viết code

- Sửa model xong chạy `python manage.py makemigrations`, đọc lại file sinh ra rồi commit cùng model.
  Không sửa migration đã merge.
- Ràng buộc Django không viết được (khóa ngoại nhiều cột, chặn `NaN`, `btrim`) và trigger tự cập nhật
  `updated_at` nằm trong các file `0002_db_rules.py`.
- Database đã tự chặn: dữ liệu trùng, liên kết sai, trạng thái/điểm/thời gian không hợp lệ. Code website
  **phải tự kiểm tra** thêm: quyền và chủ sở hữu; không khóa Admin cuối cùng; câu hỏi kích hoạt phải có
  ≥ 2 phương án và đúng 1 đáp án đúng; điều kiện phát hành, đóng đề; không sửa đề đã phát hành; hạn nộp,
  tự nộp; chấm đúng điểm; chỉ công bố điểm khi đủ điều kiện.
