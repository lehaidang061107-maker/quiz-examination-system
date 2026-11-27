# Vấn đáp theo thành viên và việc cần làm trước buổi báo cáo

Bổ sung cho [bao-cao-lap-trinh-kiem-thu.md](bao-cao-lap-trinh-kiem-thu.md) (kịch bản) và
[07-on-van-dap.md](../guides/07-on-van-dap.md) (câu hỏi chung) và [06](../guides/06-tra-cuu-ky-thuat.md) (tra cứu kỹ thuật).
Mỗi người đọc phần của mình, mở sẵn file và test được nêu, tự bấm thử một lần.

## 1. Phần của từng người

| Người | Task | Lớp / file chính | Test | Câu hay bị hỏi (gợi ý trả lời) |
| --- | --- | --- | --- | --- |
| Nguyễn Duy Thái | S3-01..05 | `accounts/models.py` (`User.login`, `Admin.*`), `decorators.py`, `services.py`, `settings.py` | `accounts/tests/test_auth_security.py`, `test_views.py`, `test_admin_views.py` | Khóa tạm thế nào? (5 lần sai → 15 phút, đếm ở `User.login`). Phân quyền ở đâu? (`@role_required` ở server, trả 403). Chống open redirect? (`_is_safe_next_url`). Đổi/khóa mật khẩu thì phiên cũ sao? (`revoke_user_sessions`). Vì sao Admin/Teacher/Student là proxy model? (cùng bảng `users`, một vai trò mỗi người). **Tên task S3-01 ghi "Flask" nhưng dự án dùng Django**: nói rõ nhóm chọn Django ở giai đoạn thiết kế kiến trúc. |
| Nguyễn Quý | S3-06..10 | `questions/models.py` (`Question`, `AnswerOption`), `importer.py`, `scripts/loadtest/` | `questions/tests/`, báo cáo đo tải | Vòng đời câu hỏi DRAFT → ACTIVE → ARCHIVED? Sửa câu đã nằm trong đề đã phát hành? (khóa, `create_revision()` tạo bản nháp). Quy tắc câu hợp lệ? (≥ 2 phương án, đúng 1 đáp án đúng). Đo tải làm thế nào, số liệu p95, tỷ lệ lỗi? (`compose.loadtest.yaml` dùng DB riêng `quiz_load`). |
| Võ Bùi Quốc Nam | S3-11..15 | `exams/models.py` (`Exam`, `ExamQuestion`, `ExamParticipant`), `exams/views.py` | `exams/tests/test_views_*.py`, `config/tests/test_integration_flow.py` | Điều kiện phát hành? (≥ 1 câu ACTIVE hợp lệ, lịch hợp lệ). Vì sao đề đã phát hành không sửa được? (BR-14, kết quả cũ luôn đúng). Khi nào công bố điểm được? (đề CLOSED, mọi bài đã GRADED). Thu hồi quyền dự thi khi sinh viên đang làm? (bài bị chốt). |
| Phạm Công Chánh | S3-16..20 | `attempts/models.py` (`Submission`, `SubmissionAnswer`), `attempts/services.py`, `take_exam.html` | `attempts/tests/test_attempts_flow.py`, `test_reliability.py` | Hạn nộp tính ở đâu? (server, `min(bắt đầu + thời lượng, closes_at)`; đồng hồ JS chỉ hiển thị). Hai tab cùng làm? (`version`, tab cũ nhận 409). Nộp 2 lần? (`_finalize` kiểm trạng thái, chỉ ghi nhận một lần). Mất mạng giữa chừng? (đáp án đã lưu từng lần chọn, worker tự nộp khi hết giờ). |
| Lê Hải Đăng | S3-21..25 | `*/migrations/0002_db_rules.py`, `Result.calculate`/`can_view`, `attempts/worker.py`, `compose.yaml`, `scripts/*.sh` | `results/tests/`, `attempts/tests/test_worker.py`, `config/tests/test_database.py` | Vì sao thêm CHECK/trigger SQL ngoài Django? (toàn vẹn dù ghi thẳng DB). Chấm điểm thế nào? (cộng `points` câu đúng; thang 10 chỉ để hiển thị). Vì sao cần worker, hai worker chạy chung? (`select_for_update(skip_locked=True)`). Sao lưu/phục hồi? (`backup_db.sh`, giữ 7 bản, `check_backup.sh`). |

## 2. Lời dẫn gợi ý (người đại diện)

1. **Use case (2 phút)**: 3 actor kế thừa "Người dùng" (đăng nhập, đăng xuất); Khách đăng ký Student; Admin quản lý tài khoản; Teacher quản lý câu hỏi, tạo/quản lý đề, xem kết quả; Student xem danh sách, làm bài, nộp bài (include chấm tự động, lưu kết quả).
2. **Demo**: đi đúng 12 bước ở [demo-and-handover.md](demo-and-handover.md#kịch-bản-demo). Nếu thiếu thời gian giữ các bước 4, 5, 6, 7, 8, 9, 10, 11.
3. **Lớp**: đọc 12 lớp (User, Admin, Teacher, Student, Question, AnswerOption, Exam, ExamQuestion, ExamParticipant, Submission, SubmissionAnswer, Result).
4. **Code**: mở `models.py` từng app, chỉ lớp và vài phương thức trùng tên trên sơ đồ (`publish`, `grade`, `calculate`, `canView`...). Đã đối chiếu: mọi phương thức trên sơ đồ lớp đều có trong code.

## 3. Đã kiểm tra và những việc còn thiếu (làm theo thứ tự)

| # | Việc | Lý do |
| --- | --- | --- |
| 1 | **Chuyển sang `main` mới nhất rồi build lại**: `git switch main && git pull`, `docker compose up -d --build --wait` | Máy đang ở nhánh `feature/S3-10-load-test` cũ, thiếu S3-36 (Admin đặt lại mật khẩu) và cấu hình proxy HTTPS; bản nộp `ProgAndTest_Group04` thì đã có S3-36. `main` và `develop` cục bộ còn thua origin 3 và 5 commit |
| 2 | Tắt web đo tải: `docker compose -f compose.yaml -f compose.loadtest.yaml stop web-load` | Lần chạy test đầu bị lỗi `too many clients` của PostgreSQL khi web-load đang chạy chung DB |
| 3 | Chạy `docker compose exec web python manage.py test` **trước giờ báo cáo**, chụp màn hình dòng `OK` | Bộ test mất khoảng 4 phút (411 test, đã `OK` trên nhánh cũ); không chạy trực tiếp trước thầy cô |
| 4 | ~~Đưa S3-10 lên GitHub~~ **Đã xong**: [PR #90](https://github.com/lehaidang061107-maker/quiz-examination-system/pull/90) vào `develop` (báo cáo `docs/loadtest/README.md`, test case `docs/testcases/S3-10.csv`). Còn: merge PR, đổi Jira CNPM-24 sang Done, gộp S3-10.csv vào xlsx (`scripts/build_testcases.py`), sửa Evidence (S3-10 đang ghi In Progress) | Số liệu: 500/500 hoàn tất, 0 lỗi, p95 đăng nhập 0,44 giây khi dàn 60 giây (3,5 giây nếu dồn 30 giây, chưa đạt 3 giây), chấm xong trong 0,16 giây. Trước tối ưu: `runserver` lỗi `too many clients`, chỉ 132/500 nộp được |
| 5 | Commit/PR các file chưa theo dõi: `Testing Document - Group04.xlsx`, `bao-cao-lap-trinh-kiem-thu.md`, `06-giai-thich-...md`, file này | Yêu cầu "log minh chứng và tài liệu của project trên GitHub" |
| 6 | Cập nhật 3 sơ đồ `.drawio` hoặc chuẩn bị câu trả lời | Code có thêm mà sơ đồ chưa có: `failed_login_count`/`locked_until` (khóa tạm), `unlock_user`, `change_password`, đặt lại mật khẩu, `import_questions` (Excel), `Exam.duplicate`, xem trước đề, `view_statistics`, xuất CSV. Nếu hỏi: "bổ sung sau thiết kế ở S3-30..36". Nhánh `docs/update-diagrams` đã có sẵn |
| 7 | Mở sẵn 3 sơ đồ trên app.diagrams.net và đối chiếu tên lớp | Yêu cầu mở sẵn trước khi báo cáo |
| 8 | Test case: dùng `scripts/build_testcases.py` gộp lại; `docs/testcases/` thiếu CSV cho S3-01, 08, 10, 21 và S3-36 (bản nộp có S3-36) | Để xlsx khớp với test case từng task; nếu cố ý không có thì chuẩn bị lý do (S3-01, S3-21 là hạ tầng) |
| 9 | Danh sách lỗi và trạng thái xử lý (Jira: Open → In Progress → Ready for Retest → Closed) | Là sản phẩm bắt buộc của giai đoạn Testing; mở sẵn bảng Jira lọc loại Bug |
| 10 | Diễn tập một lần cả nhóm, bấm giờ | Demo 8–10 phút, đủ chỗ cho câu hỏi |
