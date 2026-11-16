# Hướng dẫn chạy database

Database lưu tài khoản, câu hỏi, đề thi, bài làm và điểm. Nó chạy trong Docker
(phần mềm giúp chạy database trên máy mà không phải cài đặt phức tạp). Mỗi máy có database riêng;
nhóm chỉ chia sẻ cách tạo bảng và dữ liệu mẫu qua GitHub.

> Sắp tới database sẽ chuyển sang Django. Khi đó chỉ đổi lệnh; Docker, `.env` và Beekeeper giữ nguyên.

## Lần đầu cài

Cần cài sẵn **Python 3.11+** và **Docker Desktop** (mở Docker Desktop trước). Mở Terminal tại thư mục dự án:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # chỉ chạy khi chưa có .env, nếu không sẽ ghi đè
```

Mở `.env`, điền 2 mật khẩu tự đặt: `POSTGRES_PASSWORD` (mật khẩu database) và `DEMO_PASSWORD`
(mật khẩu tài khoản demo, ít nhất 6 ký tự). Lưu file, rồi chạy:

```bash
docker compose up -d --wait db     # bật database, chờ báo Healthy
alembic upgrade head               # tạo 9 bảng
python database/seeds/seed_demo.py # tạo dữ liệu mẫu
```

## Những lần sau

```bash
source .venv/bin/activate
docker compose up -d --wait db
alembic upgrade head               # an toàn, không tạo trùng bảng
```

Tắt: `docker compose stop db` (giữ dữ liệu). **Không chạy `docker compose down -v`**: lệnh này xóa hết dữ liệu.

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
| `users` | Tài khoản, vai trò |
| `questions`, `answer_options` | Câu hỏi, các lựa chọn và đáp án đúng |
| `exams`, `exam_questions` | Đề thi (lịch, thời lượng); câu nào trong đề, thứ tự, điểm |
| `exam_participants` | Sinh viên được giao đề |
| `submissions`, `submission_answers` | Lượt làm bài; đáp án sinh viên chọn |
| `results` | Điểm, số câu đúng |

## Kiểm tra và làm lại từ đầu

```bash
python -m unittest discover -s tests/integration -v   # cuối kết quả có OK là đạt
```

Muốn xóa hết bảng rồi tạo lại (chỉ làm khi chấp nhận mất dữ liệu):

```bash
alembic downgrade base
alembic upgrade head
python database/seeds/seed_demo.py
```

## Gặp lỗi

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` hoặc `alembic` | Chạy lại lệnh `activate` |
| Không kết nối được | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| `password authentication failed` | Mật khẩu trong `.env` không khớp database (xem bên dưới) |
| Báo mật khẩu demo quá ngắn | Đặt `DEMO_PASSWORD` ít nhất 6 ký tự |
| Báo "demo đã tồn tại" | Bình thường, dữ liệu cũ được giữ |

**Sửa `.env` không tự đổi mật khẩu database.** Muốn đổi: chạy
`docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'`, gõ `\password quiz_app`,
nhập mật khẩu mới hai lần, gõ `\q`, rồi sửa `POSTGRES_PASSWORD` trong `.env` cho khớp.

## Dành cho người viết code

Database đã tự chặn: dữ liệu trùng, liên kết sai, trạng thái/điểm/thời gian không hợp lệ; tự cập nhật
`updated_at`; lưu giờ kèm múi giờ. Code website **phải tự kiểm tra** thêm: quyền và chủ sở hữu; không khóa
Admin cuối cùng; câu hỏi kích hoạt phải có ≥ 2 phương án và đúng 1 đáp án đúng; điều kiện phát hành, đóng đề;
không sửa đề đã phát hành; hạn nộp, tự nộp; chấm đúng điểm; chỉ công bố điểm khi đủ điều kiện.
