# Demo & Handover

<!-- toc -->

**Mục lục**

- [Chuẩn bị trước buổi demo](#chuẩn-bị-trước-buổi-demo)
- [Kịch bản demo](#kịch-bản-demo)
- [Nếu có sự cố khi demo](#nếu-có-sự-cố-khi-demo)
- [Danh sách bàn giao](#danh-sách-bàn-giao)

<!-- /toc -->

Kịch bản demo theo luồng chính (khoảng 15 phút) và danh sách bàn giao cuối môn. Dữ liệu demo là tài khoản giả
`@demo.example`, không có thông tin thật.

## Chuẩn bị trước buổi demo

Làm trước ít nhất 30 phút, trên máy sẽ dùng để demo:

| # | Việc | Lệnh / cách kiểm tra |
| --- | --- | --- |
| 1 | Lấy code mới nhất | `git switch main && git pull` |
| 2 | Chạy hệ thống | `docker compose up -d --build --wait` (cả `db`, `web`, `worker` đều Healthy) |
| 3 | Dữ liệu mẫu | `docker compose exec web python manage.py seed_demo` |
| 4 | Sao lưu dữ liệu trước demo | `scripts/backup_db.sh`, rồi `scripts/check_backup.sh` phải ra `ĐẠT` |
| 5 | Bộ kiểm tra | `docker compose exec web python manage.py test` cuối kết quả có `OK` |
| 6 | Trình duyệt | Chrome hoặc Edge; mở sẵn 2 cửa sổ: thường (giảng viên) và ẩn danh (sinh viên) |
| 7 | Mật khẩu demo | Biết `DEMO_PASSWORD` trong `.env` (cả nhóm dùng `Kiemthu2026`) |

Trang lỗi 403/404 tiếng Việt chỉ hiện khi `DEBUG=False`. Muốn demo phần này thì đặt `DEBUG=False` trong `.env`
rồi `docker compose up -d --wait`; nhớ đổi lại `True` khi code tiếp.

## Kịch bản demo

Mở http://127.0.0.1:8000/accounts/login/. Cột "Yêu cầu" để trả lời khi thầy cô hỏi chức năng nào ứng với đặc tả.

| Bước | Ai | Thao tác | Thấy gì | Yêu cầu |
| --- | --- | --- | --- | --- |
| 1 | Khách | Bấm **Đăng ký ngay**, tạo tài khoản sinh viên mới | Chuyển về Đăng nhập, không tự đăng nhập | FR-01 |
| 2 | Khách | Đăng nhập sai mật khẩu 5 lần với một tài khoản | Thông báo khóa tạm 15 phút | FR-02, NFR-SEC-07 |
| 3 | Admin | Đăng nhập `admin@demo.example` → **Quản lý tài khoản**; khóa rồi mở khóa tài khoản vừa tạo | Trạng thái đổi, có hộp xác nhận | FR-04, BR-22 |
| 4 | Giảng viên | Đăng nhập `teacher@demo.example` → **Ngân hàng câu hỏi** → tạo 1 câu, 3 phương án, 1 đáp án đúng | Câu hỏi ở trạng thái Đang dùng | FR-05, BR-13 |
| 5 | Giảng viên | **Quản lý kỳ thi** → **Tạo đề thi** (thời lượng 5 phút) → thêm câu hỏi, đặt điểm → **Phân công** `student3` và sinh viên mới → **Phát hành** | Đề chuyển Đã phát hành, không sửa được câu hỏi | FR-06, BR-17, BR-18 |
| 6 | Sinh viên | Cửa sổ ẩn danh, đăng nhập `student3@demo.example` → **Danh sách bài thi** → bắt đầu đề vừa tạo | Đồng hồ đếm ngược, lưới số câu, tiến độ | FR-08, FR-09, NFR-USA-03 |
| 7 | Sinh viên | Chọn đáp án, chờ chữ **Đã lưu**; tải lại trang | Đáp án vẫn còn, đồng hồ không đặt lại | NFR-REL-02, BR-21 |
| 8 | Sinh viên | Bấm **Nộp bài** | Hộp xác nhận ghi số câu đã làm; sau khi nộp không sửa được | FR-10, NFR-SEC-06 |
| 9 | Giảng viên | **Kết quả thi** → mở đề | Bài của `student3` đã chấm điểm tự động | FR-11, FR-12, FR-13 |
| 10 | Giảng viên | Chi tiết đề → **Đóng đề** → **Công bố điểm** | Công bố được khi mọi bài đã chấm; còn bài đang làm hoặc chờ chấm thì hệ thống từ chối | FR-07, BR-19 |
| 11 | Sinh viên | **Lịch sử bài thi** | Thấy điểm, số câu đúng; không thấy đáp án chuẩn | FR-13, BR-19 |
| 12 | Sinh viên | Gõ thẳng `/exams/` (trang của giảng viên) | Trang 403 | NFR-SEC-02 |

Phần thêm nếu còn thời gian:

- **Tự nộp khi hết giờ** (FR-10, NFR-REL-06): tạo đề thời lượng 1 phút, sinh viên bắt đầu làm, chọn vài đáp án
  rồi đóng trình duyệt. Hết giờ, worker tự nộp bằng đáp án đã lưu: `docker compose logs worker | grep AUDIT`.
- **Nhật ký** (NFR-MAI-03): `docker compose logs web worker | grep AUDIT` thấy đăng nhập, khóa tài khoản, nộp bài,
  công bố điểm vừa làm ở trên.
- **Sao lưu và phục hồi** (NFR-REL-04): `scripts/check_backup.sh`; hoặc xóa thử một đề rồi
  `scripts/restore_db.sh backups/quiz-...dump` (bản tạo ở bước chuẩn bị 4) để lấy lại. Xem
  [05-backup-restore.md](../guides/05-backup-restore.md).

Demo xong muốn trả dữ liệu về như lúc chuẩn bị: `scripts/restore_db.sh` với bản sao lưu ở bước chuẩn bị 4.

## Nếu có sự cố khi demo

| Sự cố | Xử lý nhanh |
| --- | --- |
| Trang không mở | `docker compose ps`; service nào không Healthy thì `docker compose up -d --wait` |
| Lỡ xóa hoặc làm hỏng dữ liệu demo | `scripts/restore_db.sh backups/<bản trước demo>.dump` |
| Quên mật khẩu demo | Xem `DEMO_PASSWORD` trong `.env` |
| Tài khoản bị khóa tạm do thử sai | Chờ 15 phút hoặc dùng tài khoản demo khác |

## Danh sách bàn giao

Đối chiếu với [Final Deliverables](project-plan.md#final-deliverables):

| Hạng mục | Ở đâu | Người kiểm |
| --- | --- | --- |
| Mã nguồn | GitHub, nhánh `main` | PM |
| Hướng dẫn cài đặt, chạy, kiểm thử | [README](../../README.md), [01-getting-started](../guides/01-getting-started.md), [04-testing](../guides/04-testing.md) | Một thành viên làm theo trên máy khác |
| Sao lưu, phục hồi | `scripts/*.sh`, [05-backup-restore](../guides/05-backup-restore.md) | PM |
| Dữ liệu mẫu | Lệnh `seed_demo` (`src/accounts/management/commands/seed_demo.py`) | PM |
| Kịch bản demo | File này | Cả nhóm diễn tập một lần |
| Đặc tả và thiết kế | `docs/Requirement Specification & Design Document.docx`, các file `.drawio` | PM |
| Thiết kế giao diện | `docs/Quiz-Examination-System-UI-Figma-Import/` | PM |
| Ca kiểm thử | `docs/testcases/S3-*.csv`, gộp bằng `python scripts/build_testcases.py` | PM |
| Kết quả kiểm thử tải | Báo cáo S3-10 (cấu hình máy, p95, tỷ lệ lỗi) | Người làm S3-10 |
| Hạn chế còn lại | Không có HTTPS (chạy trên máy cá nhân); web chạy `runserver`; sao lưu nằm cùng máy | Ghi trong báo cáo |

Không bàn giao: file `.env`, thư mục `backups/` (chứa dữ liệu và mật khẩu đã băm).
