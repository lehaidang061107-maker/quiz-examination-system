# Hướng dẫn chạy database

Database là nơi lưu tài khoản, câu hỏi, đề thi, bài làm và điểm. Nó chạy trong
Docker (phần mềm giúp chạy database trên máy mà không phải cài đặt phức tạp).

> Sắp tới database sẽ chuyển sang Django. Khi đó chỉ đổi lệnh; Docker và Beekeeper giữ nguyên.

## Lần đầu cài

Cần cài sẵn **Python** và **Docker Desktop** (mở Docker Desktop trước khi chạy).
Mở Terminal tại thư mục dự án, chạy lần lượt:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Mở file `.env`, điền 2 mật khẩu tự đặt: `POSTGRES_PASSWORD` (mật khẩu database) và
`DEMO_PASSWORD` (mật khẩu tài khoản demo). Lưu file, rồi chạy:

```bash
docker compose up -d --wait db
alembic upgrade head
python database/seeds/seed_demo.py
```

Thấy báo "Đã tạo dữ liệu demo" là xong.

## Những lần sau

```bash
source .venv/bin/activate
docker compose up -d --wait db
```

Tắt database: `docker compose stop db`. **Đừng chạy `docker compose down -v`** vì sẽ mất hết dữ liệu.

## Xem dữ liệu bằng Beekeeper hoặc DBeaver

Tạo kết nối loại **PostgreSQL**, nhập:

| Ô | Giá trị |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `55433` |
| User | `quiz_app` |
| Database | `quiz_examination` |
| Password | `POSTGRES_PASSWORD` trong `.env` |

## Kiểm tra

```bash
python -m unittest discover -s tests/integration -v
```

Cuối kết quả có chữ `OK` là database hoạt động đúng.

## Gặp lỗi

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` hoặc `alembic` | Chạy lại lệnh `activate` ở trên |
| Không kết nối được | Mở Docker Desktop, chạy `docker compose up -d --wait db` |
| Sai mật khẩu | Kiểm tra `POSTGRES_PASSWORD` trong `.env` |
| Báo "demo đã tồn tại" | Bình thường, không cần làm gì |
