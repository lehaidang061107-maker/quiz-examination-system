# S3-10 · Báo cáo đo tải và tối ưu

Đo theo NFR-PER-01 đến NFR-PER-03 và NFR-PER-06 của đặc tả. Số liệu thô nằm cạnh file này (`*.json`), chạy lại được bằng lệnh ở cuối.

## Cấu hình đo

| Mục | Giá trị |
| --- | --- |
| Máy | MacBook, Docker Desktop: 8 CPU, 8 GB RAM; máy tạo tải, website và PostgreSQL **dùng chung một máy** |
| Database | PostgreSQL 17 (container), `max_connections` mặc định 100, database riêng `quiz_load` |
| Dữ liệu | 1 đề 50 câu x 4 lựa chọn, 500 Student được giao đề, 1 Teacher, 1 Admin |
| Kịch bản mỗi Student | đăng nhập → danh sách → bắt đầu bài → tải câu hỏi → lưu 1 đáp án mỗi 10 giây → nộp |
| Đợt nộp | 500 bài nộp rải trong 10 giây |
| Thời gian | 120 giây làm bài (đặc tả: 30 phút) |
| Đo | thời gian phía máy khách, từ lúc gửi đến lúc nhận đủ phản hồi (cao hơn thời gian xử lý của máy chủ) |
| Chấm điểm | tính bằng SQL: `results.graded_at - submissions.submitted_at` |

## Công cụ đã dùng

| Việc | Công cụ | Ở đâu |
| --- | --- | --- |
| Tạo tải (sinh viên ảo) | Script Python tự viết, chỉ dùng thư viện chuẩn (`urllib`, `threading`, `http.cookiejar`), mỗi sinh viên là một luồng với cookie và CSRF riêng. Không dùng JMeter hay Locust. | `scripts/loadtest/run_load.py` |
| Tạo dữ liệu | Django shell (`manage.py shell`), tạo đề 50 câu và 500 tài khoản | `scripts/loadtest/seed.py` |
| Dựng lại dữ liệu mỗi lượt | Shell script + `psql` trong container | `scripts/loadtest/reset.sh` |
| Đo thời gian chấm | Truy vấn SQL trên PostgreSQL bằng `psql` | `scripts/loadtest/grading.sql` |
| Đếm truy vấn (N+1) | `CaptureQueriesContext` và `Client` của Django | chạy bằng `manage.py shell`, không lưu file |
| Tìm nguyên nhân lỗi | `docker compose logs` và `show max_connections` của PostgreSQL | |
| Máy chủ web thử | `runserver` (trước), gunicorn 23.0.0 (sau) | `compose.loadtest.yaml` |
| Môi trường | Docker Compose, PostgreSQL 17, Python 3.12 (trong container) | |

Phần trăm p50/p95 do script tự tính từ thời gian từng yêu cầu; p95 lấy phần tử thứ 95% của danh sách đã sắp xếp.

## Kết quả

| Lần | Máy chủ | Tăng tải | Lỗi | p95 đăng nhập | p95 danh sách | p95 lấy câu hỏi | p95 lưu đáp án | Chấm ≤ 5 giây |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Trước | `runserver`, kết nối đóng sau mỗi yêu cầu | 500 đăng nhập / 30 giây | **260 lỗi đăng nhập, 53 lỗi danh sách, 25 lỗi tải đề**; chỉ 132/500 nộp được | 15,3 giây | 30,2 giây | 39,1 giây | 0,08 giây | 132 bài, đều trong 0,02 giây |
| Sau (1) | gunicorn 4 tiến trình x 8 luồng, giữ kết nối 60 giây | 500 / 30 giây | 0 lỗi | 6,1 giây | 4,8 giây | 4,9 giây | 0,28 giây | 500/500 |
| Sau (2) | gunicorn 8 x 4 | 500 / 30 giây | 0 lỗi | 3,5 giây | 2,2 giây | 2,2 giây | 0,41 giây | 500/500 |
| Sau (3) | gunicorn 8 x 4 | 500 / 60 giây | 0 lỗi | **0,44 giây** | 0,03 giây | 0,08 giây | 0,02 giây | 500/500, chậm nhất 0,16 giây |

File: `truoc-500.json`, `sau-500.json`, `sau-500-w8t4.json`, `sau-500-ramp60.json`.

## Kết luận theo yêu cầu

| Yêu cầu | Kết quả |
| --- | --- |
| NFR-PER-01: 500 Student đồng thời | Đạt về số lượng: 500/500 hoàn tất luồng, không lỗi (từ lần Sau (1)). Chưa đo đủ 30 phút. |
| NFR-PER-02: p95 ≤ 3 giây, lỗi < 1% | Đạt ở lần Sau (3). Ở lần Sau (2), p95 đăng nhập là 3,5 giây, **chưa đạt** khi 500 người đăng nhập dồn trong 30 giây. |
| NFR-PER-03: chấm ≤ 5 giây | Đạt: 500/500 bài chấm trong 0,16 giây, mỗi bài một Result. |
| NFR-PER-04: lưu trữ 10.000 TK, 50.000 câu, 500.000 bài nộp | **Chưa đo.** Với 500 sinh viên, database nặng 12 MB. |
| NFR-PER-05: phân trang | Đã có (danh sách đề 20 dòng/trang, tài khoản 10 dòng/trang). |

## Nguyên nhân và việc đã tối ưu

1. **Hết kết nối database.** `runserver` mở một kết nối PostgreSQL cho mỗi yêu cầu đang chạy; khi hàng trăm yêu cầu đồng thời thì vượt `max_connections = 100`, log báo `sorry, too many clients already` (550 lần) và trả lỗi 500. Đây là nguyên nhân gần như toàn bộ lỗi ở lần "Trước".
2. **Một tiến trình duy nhất.** Đăng nhập băm mật khẩu bằng PBKDF2 (tốn CPU), `runserver` chỉ có một tiến trình nên các yêu cầu xếp hàng, p95 lên tới 15 đến 39 giây.
3. **Việc đã làm:**
   - Thêm `gunicorn` (nhiều tiến trình x luồng; tổng số kết nối database bị chặn bởi 8 x 4 = 32) trong `compose.loadtest.yaml`.
   - Thêm cấu hình `DB_CONN_MAX_AGE` (mặc định 0, giữ nguyên hành vi cũ) để tái sử dụng kết nối.
4. **Truy vấn:** đếm thử bằng `CaptureQueriesContext`: danh sách bài thi 10 truy vấn, trang làm bài đề 50 câu 11 truy vấn (không tăng theo số câu nhờ `select_related`/`prefetch_related` có sẵn). Không thấy N+1 hay truy vấn chậm, nên **không thêm index hay migration**. Lưu đáp án và nộp bài luôn dưới 0,5 giây.

## Giới hạn của lần đo

- Máy tạo tải chạy cùng máy với website và database nên số liệu **thấp hơn** thực tế một chút (tranh CPU).
- Thời gian làm bài 120 giây, không phải 30 phút; rò rỉ tài nguyên hoặc suy giảm lâu dài chưa được kiểm.
- Thời gian đo phía máy khách, không phải từ lúc máy chủ nhận yêu cầu như đặc tả.
- Chưa đo trên máy chủ thật hay qua mạng; chưa đo NFR-PER-04.
- Bản demo `docker compose up` vẫn chạy `runserver`. Muốn chịu tải gần 500 người thì dùng gunicorn như trên.
- Kết quả "trước" và "sau" chỉ đo một lần mỗi cấu hình, chưa lặp nhiều lần.

## Chạy lại

```bash
export LOAD_SERVER=gunicorn LOAD_CONN_MAX_AGE=60 GUNICORN_WORKERS=8 GUNICORN_THREADS=4
docker compose -f compose.yaml -f compose.loadtest.yaml up -d --build --wait web-load
scripts/loadtest/reset.sh 500          # mỗi Student chỉ nộp một lần nên mỗi lượt đo cần dữ liệu mới
python3 scripts/loadtest/run_load.py --users 500 --ramp 60 --duration 120 --out docs/loadtest/ket-qua.json
docker compose -f compose.yaml -f compose.loadtest.yaml exec -T db sh -c 'psql -U "$POSTGRES_USER" -d quiz_load' < scripts/loadtest/grading.sql
```

Bản "Trước": bỏ các biến `export` ở trên (mặc định là `runserver`).
