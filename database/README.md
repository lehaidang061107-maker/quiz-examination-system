# Chạy và xem database của dự án

Database là nơi lưu dữ liệu của hệ thống thi trắc nghiệm. Task **S3-21** đã có
9 bảng, dữ liệu mẫu, lệnh tạo/quay lui bảng và kiểm thử. Website đăng nhập, làm bài
sẽ được xây dựng ở các task khác.

**Các tên gọi:** PostgreSQL quản lý dữ liệu; Docker chạy PostgreSQL trên máy;
Alembic chạy **migration** (tạo/cập nhật bảng theo phiên bản); **seed** thêm dữ liệu mẫu;
`.env` lưu thông tin kết nối và mật khẩu riêng của máy.

## 1. Cài lần đầu

Cần Python 3.11 trở lên và Docker Desktop. Mở Docker Desktop, chờ chạy xong.
Mở Terminal trong thư mục dự án `quiz-examination-system`, chạy từng dòng:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Chỉ khi **chưa có `.env`**, chạy `cp .env.example .env`. Mở `.env`, điền cấu hình
bên dưới rồi lưu bằng **Command + S** trên Mac. Không chép đè `.env` đang dùng.

| Biến | Giá trị |
| --- | --- |
| `POSTGRES_DB` | `quiz_examination` — tên database |
| `POSTGRES_USER` | `quiz_app` — tài khoản kết nối |
| `POSTGRES_PASSWORD` | Mật khẩu PostgreSQL do bạn đặt |
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `55433` — cổng kết nối |
| `DEMO_PASSWORD` | Mật khẩu tài khoản demo, ít nhất 6 ký tự; chỉ dùng thử cục bộ |

Mật khẩu có ký tự như `@` được hỗ trợ. Biến đã đặt trong môi trường Terminal
được ưu tiên hơn `.env`. Không đưa `.env` hoặc mật khẩu lên Git.

```bash
docker compose up -d --wait db
alembic upgrade head
python database/seeds/seed_demo.py
```

Thành công khi Docker báo `Healthy`, Alembic không lỗi và seed báo đã tạo demo.
Mỗi máy có database riêng; nhóm chia sẻ migration/seed qua Git. Dùng một server
chung cho nhiều máy cần cấu hình triển khai riêng.

## 2. Mỗi lần sử dụng

Mở Docker Desktop. Tại thư mục dự án, chạy:

```bash
source .venv/bin/activate
docker compose up -d --wait db
alembic upgrade head
```

Đầu dòng có `(.venv)` là đã bật môi trường Python. Migration không tạo bảng trùng;
không cần chạy seed mỗi lần. Dùng xong chạy `docker compose stop db` để dừng và giữ dữ liệu.

## 3. Xem dữ liệu bằng Beekeeper hoặc DBeaver

Tạo kết nối **PostgreSQL**, nhập các ô sau; để SSL và SSH Tunnel tắt cho kết nối cục bộ này:

| Ô | Giá trị |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `55433` |
| User / Username | `quiz_app` |
| Database / Default Database | `quiz_examination` |
| Password | `POSTGRES_PASSWORD` trong `.env`, không phải mật khẩu demo |

Nhấn **Test** → **Connect**. Mở `public`, chọn bảng để xem; DBeaver có thêm
mục `Schemas` và `Tables`. MySQL Workbench không kết nối được PostgreSQL này.

| Bảng | Lưu thông tin gì? |
| --- | --- |
| `users` | Tài khoản, vai trò |
| `questions` | Câu hỏi |
| `answer_options` | Các lựa chọn và đáp án đúng |
| `exams` | Đề thi, lịch, thời lượng |
| `exam_questions` | Câu trong đề, thứ tự, điểm |
| `exam_participants` | Sinh viên được giao đề |
| `submissions` | Lượt làm bài |
| `submission_answers` | Đáp án sinh viên chọn |
| `results` | Điểm, số câu đúng |

`alembic_version` là bảng phụ ghi phiên bản, không tính trong 9 bảng nghiệp vụ.
Xem [tài khoản và dữ liệu mẫu](seeds/README.md).

## 4. Lỗi thường gặp và mật khẩu

| Lỗi | Cách xử lý |
| --- | --- |
| Không tìm thấy `python` / `alembic` | Chạy `source .venv/bin/activate` ở thư mục dự án |
| Không kết nối được | Mở Docker; chạy `docker compose up -d --wait db`; kiểm tra cổng `55433` |
| `password authentication failed` | Kiểm tra mật khẩu trong `.env` và mật khẩu thật của PostgreSQL |
| Seed báo mật khẩu quá ngắn | Điền `DEMO_PASSWORD` ít nhất 6 ký tự, lưu file |
| Seed báo demo đã tồn tại | Bình thường; dữ liệu cũ được giữ nguyên |

**Đổi `.env` không tự đổi mật khẩu trong database.** Muốn đổi mật khẩu PostgreSQL:

```bash
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Trong màn hình `quiz_examination=#`, nhập `\password quiz_app`, nhập mật khẩu mới
hai lần khi được hỏi, rồi `\q` để thoát. Sửa `POSTGRES_PASSWORD` trong `.env` cho khớp.
Thay `quiz_app` nếu dùng tài khoản khác. Đổi mật khẩu demo cần cập nhật bản băm
trong `users`; seed chạy lại không đổi mật khẩu tài khoản đã tạo.

## 5. Kiểm thử và quay lui

```bash
python -m unittest discover -s tests/integration -v
```

Cuối kết quả có `OK` là đạt. Test tạo khu vực tạm (schema ngẫu nhiên), thử tạo →
xóa → tạo lại rồi dọn khu vực đó; giữ nguyên bảng ứng dụng trong `public`.
Tài khoản kiểm thử cần quyền tạo schema. Xem [báo cáo kiểm thử](VERIFICATION.md).

**Rollback là quay lui migration. Lệnh sau xóa cả 9 bảng và dữ liệu:** chỉ dùng
trên database có thể xóa hoặc đã sao lưu, không phải bước chạy hằng ngày.

```bash
alembic downgrade base
# Muốn tạo lại bảng trống và dữ liệu mẫu:
alembic upgrade head
python database/seeds/seed_demo.py
```

`alembic current` xem phiên bản; `alembic history` xem lịch sử. Chỉ xem SQL mà
không thực thi: `alembic upgrade head --sql` hoặc `alembic downgrade 0001:base --sql`.
**Không chạy `docker compose down -v` khi cần giữ dữ liệu:** lệnh này xóa ổ lưu database.

## 6. Bàn giao và phần việc tiếp theo

Đưa lên Git: cấu hình mẫu, Compose, requirements, Alembic, migration, seed, test,
hướng dẫn. Bỏ qua `.env`, `.venv`, cache và mật khẩu. Commit → push → tạo Pull Request.
Người phát triển tạo phiên bản mới bằng `alembic revision -m "mo ta thay doi"`,
viết cả cập nhật và quay lui; không sửa migration đã được nhóm áp dụng hoặc chạy
lại `alembic init`. Hiện chưa dùng `--autogenerate`.

Database đã chặn dữ liệu trùng, liên kết sai, trạng thái/điểm/thời gian không hợp lệ;
giữ tham chiếu lịch sử, tự cập nhật `updated_at` cho tài khoản/câu hỏi/đề.
Email phải bỏ khoảng trắng đầu/cuối và đổi sang chữ thường trước khi lưu.
Thời điểm có múi giờ; giao diện sau này hiển thị giờ Việt Nam.

Theo mục 6.5 của đặc tả, tầng xử lý ứng dụng còn phải kiểm tra: vai trò/chủ sở hữu,
Admin cuối cùng; câu ACTIVE có ≥2 phương án và đúng 1 đáp án đúng; điều kiện phát
hành/đóng/lưu trữ, giữ nguyên đề đã phát hành; cấp/thu hồi quyền; tính hạn, lưu theo
version, khóa sửa và tự nộp; chấm đúng điểm/số câu và tạo Result cùng lúc chuyển
GRADED; điều kiện công bố và bảo vệ phiên/điểm/đáp án. Schema chưa tự bảo đảm các
quy tắc liên bảng này. Chưa đo tải 500 sinh viên đồng thời.
