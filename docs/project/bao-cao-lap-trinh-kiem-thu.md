# Kịch bản báo cáo giai đoạn Programming & Testing

Một máy duy nhất của nhóm, mở sẵn mọi thứ trước giờ báo cáo.

## 1. Checklist mở sẵn (làm trước 30 phút)

| # | Hạng mục | Cách chuẩn bị |
| --- | --- | --- |
| 1 | Tài liệu đặc tả | `docs/Requirement Specification & Design Document.docx` |
| 2 | Sơ đồ use case, sơ đồ lớp | Mở `docs/Use-Case-Diagram.drawio`, `docs/ClassDiagram-Reviewed.drawio` trên app.diagrams.net (File → Open from device) |
| 3 | GitHub | Tab Commits, Pull requests (đã merge), Insights → Contributors, Projects/Jira; thư mục `docs/` |
| 4 | File test cases | `docs/Testing Document - Group04.xlsx`; CSV từng task ở `docs/testcases/` |
| 5 | Công cụ kiểm thử | Terminal sẵn lệnh `docker compose exec web python manage.py test` |
| 6 | Docker | `docker compose up -d --build --wait` (db, web, worker đều Healthy) |
| 7 | Source code | Editor mở sẵn thư mục `src/` |
| 8 | Chương trình chạy sẵn | `docker compose exec web python manage.py seed_demo`, mở http://127.0.0.1:8000/accounts/login/; 2 cửa sổ: thường (giảng viên), ẩn danh (sinh viên); mật khẩu `DEMO_PASSWORD` trong `.env` |

Chi tiết chuẩn bị, backup dữ liệu và xử lý sự cố: [demo-and-handover.md](demo-and-handover.md).

## 2. Trình tự báo cáo

| Thứ tự | Nội dung | Thời lượng gợi ý | Người |
| --- | --- | --- | --- |
| 1 | Trình bày nhanh sơ đồ use case (3 actor Admin, Giảng viên, Sinh viên) | 2 phút | 1 bạn đại diện |
| 2 | Demo chức năng theo 12 bước ở [demo-and-handover.md](demo-and-handover.md#kịch-bản-demo) | 8–10 phút | cùng bạn đó |
| 3 | Liệt kê các lớp trên sơ đồ lớp | 2 phút | cùng bạn đó |
| 4 | Mở source, chỉ lớp code ứng với lớp thiết kế (bảng mục 3) | 3 phút | cùng bạn đó |
| 5 | Từng thành viên trả lời câu hỏi về phần mình làm | còn lại | từng người |

## 3. Đối chiếu lớp thiết kế với source

| Lớp trên sơ đồ | Lớp trong code | File |
| --- | --- | --- |
| User | `User` | `src/accounts/models.py` |
| Admin | `Admin` | `src/accounts/models.py` |
| Teacher (Giảng viên) | `Teacher` | `src/accounts/models.py` |
| Student (Sinh viên) | `Student` | `src/accounts/models.py` |
| Question | `Question` | `src/questions/models.py` |
| AnswerOption | `AnswerOption` | `src/questions/models.py` |
| Exam | `Exam` | `src/exams/models.py` |
| ExamQuestion | `ExamQuestion` | `src/exams/models.py` |
| ExamParticipant | `ExamParticipant` | `src/exams/models.py` |
| Submission | `Submission` | `src/attempts/models.py` |
| SubmissionAnswer | `SubmissionAnswer` | `src/attempts/models.py` |
| Result | `Result` | `src/results/models.py` |

Lớp phụ trợ (enum, quản lý): `Role`, `UserStatus`, `QuestionType`, `QuestionStatus`, `ExamStatus`, `SubmissionStatus`, `UserManager`, `RoleManager`.
Tầng MVC: model ở `models.py`, nghiệp vụ ở `services.py`, controller ở `views.py`, giao diện ở `src/templates/`.

> Trước buổi báo cáo, đặt sơ đồ lớp cạnh bảng này và kiểm tra tên lớp trong file `.drawio` khớp cột đầu. Chỗ nào lệch thì sửa bảng hoặc chuẩn bị lời giải thích.

## 4. Minh chứng kiểm thử

- Chạy `docker compose exec web python manage.py test`, cuối kết quả phải có `OK`. Test nằm trong `src/<app>/tests/`.
- Mở `Testing Document - Group04.xlsx`: test case theo task S3-xx, kết quả Pass/Fail, bug đã sửa.
- Nói rõ 3 mức: unit (`test_models.py`), tích hợp/luồng (`test_integration_flow.py`, `test_attempts_flow.py`), thử tay trên trình duyệt theo CSV.

## 5. Minh chứng GitHub

Commit và PR của từng thành viên (mỗi task Jira một nhánh `feature/S3-xx-...`, PR vào `develop`), tab Contributors, thư mục `docs/`.

## 6. Câu hỏi thầy cô có thể hỏi

Xem [07-on-van-dap.md](../guides/07-on-van-dap.md) (câu hỏi và trả lời ngắn) và [van-dap-theo-thanh-vien.md](van-dap-theo-thanh-vien.md) (theo từng người). Mỗi người nắm chắc: phần mình làm ứng với lớp/FR nào, file nào, test nào, PR nào.
