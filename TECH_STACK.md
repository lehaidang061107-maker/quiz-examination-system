# Công nghệ sử dụng

Website viết bằng **Python + Django**, dữ liệu lưu trong **PostgreSQL**.
Cả nhóm dùng chung bộ này; không tự chọn công nghệ khác (ví dụ Flask, SQLite).
Mục ghi **(chờ xác nhận)** là đề xuất, nhóm cần đồng ý trước khi áp dụng.

## 1. Dùng gì cho việc gì

| Việc | Dùng | Ghi chú |
| --- | --- | --- |
| Ngôn ngữ | Python 3.12 – 3.14 | Các bản Django 5.2 hỗ trợ |
| Khung website | Django 5.2 (bản hỗ trợ dài hạn, tới 4/2028) | Ghi bản cụ thể trong `requirements.txt`, hiện là `Django==5.2.19` |
| Giao diện | Django Templates + Bootstrap 5 | Làm theo bản Figma trong `docs/` |
| Lưu dữ liệu | PostgreSQL 17, chạy bằng Docker | [Hướng dẫn](database/README.md). Không dùng SQLite, kể cả khi test |
| Tạo/sửa bảng | Django migrations | Chạy `makemigrations`, đọc lại file sinh ra; không sửa migration đã merge |
| Tài khoản | Model `accounts.User` riêng, đăng nhập bằng email, lưu ở bảng `users` | Phải có trước lần `migrate` đầu tiên |
| Đăng nhập, phiên | Có sẵn của Django, phiên lưu trong database | Tự đăng xuất sau 30 phút không hoạt động; tài khoản bị khóa mất phiên ngay |
| Khóa tạm khi nhập sai | Tự viết | Sai 5 lần liên tiếp thì khóa 15 phút; khác với Admin khóa tài khoản |
| Mật khẩu | Mã hóa có sẵn của Django | Ít nhất 8 ký tự, có cả chữ và số |
| Chống giả mạo form (CSRF) | Có sẵn của Django | Mọi form gửi đi có `{% csrf_token %}` |
| Tự nộp bài khi hết giờ | Lệnh chạy nền `python manage.py run_worker`, kiểm tra mỗi 5 giây **(chờ xác nhận)** | Khóa từng bài khi xử lý để không nộp/chấm trùng |
| Kiểm thử | `python manage.py test` | Django tự tạo database thử riêng, không đụng dữ liệu thật |
| Cấu hình bí mật | File `.env` trên máy mình (mẫu: `.env.example`) | `SECRET_KEY`, mật khẩu không viết trong code, không đưa lên GitHub |

## 2. Code chia thành các phần

| Phần (app) | Lo việc gì |
| --- | --- |
| `config` | Cấu hình chung, Trang chủ theo vai trò, menu (`navigation.py`), trang `/health` kiểm tra website còn chạy |
| `accounts` | Đăng ký Student, đăng nhập/đăng xuất, khóa tạm, Admin quản lý tài khoản |
| `questions` | Ngân hàng câu hỏi và phương án |
| `exams` | Tạo đề, phát hành đề, giao đề cho sinh viên |
| `attempts` | Làm bài, tự lưu đáp án, nộp bài, tự nộp khi hết giờ |
| `results` | Chấm điểm, công bố và xem kết quả |

Mỗi phần có `urls.py` riêng và phải được khai báo trong `config/urls.py`, nếu không trang sẽ báo 404.

### Kiến trúc: MVC

Nhóm chọn mẫu kiến trúc **MVC (Model – View – Controller)**. Django gọi là MVT nhưng vai trò giống nhau:

| MVC | Trong code | Làm gì | Không được làm |
| --- | --- | --- | --- |
| **Model** | `models.py` | Lớp theo sơ đồ lớp, lưu dữ liệu, **mọi quy tắc nghiệp vụ** (phát hành đề, chấm điểm, khóa tài khoản…) | Đọc `request`, trả HTML |
| **View** | `templates/<app>/*.html` | Hiển thị giao diện theo Figma | Truy vấn database, tính toán nghiệp vụ |
| **Controller** | `views.py` + `urls.py` | Nhận yêu cầu, kiểm tra đăng nhập/vai trò, đọc form, **gọi phương thức của Model**, chọn template | Tự viết lại quy tắc đã có trong Model |

Ví dụ phát hành đề, trong `exams/views.py`:

```python
def publish_exam(request, exam_id):
    teacher = request.user.as_role()           # Teacher
    exam = teacher.manage_exam(exam_id)        # sai giảng viên -> PermissionDenied (403)
    try:
        exam.publish()                         # quy tắc nằm trong Model
        messages.success(request, "Đã phát hành đề.")
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
    return redirect("exams:detail", exam_id)
```

Phương thức Model báo lỗi nghiệp vụ bằng `ValidationError` (thông báo tiếng Việt, hiển thị thẳng cho
người dùng) và lỗi sai quyền bằng `PermissionDenied`.

### Sơ đồ lớp trong code

Tên phương thức theo sơ đồ lớp (mục 5.2 tài liệu đặc tả), viết kiểu Python: `viewAvailableExams()` → `view_available_exams()`.
Admin/Teacher/Student là proxy model của `User` (cùng bảng `users`); lấy từ phiên bằng `request.user.as_role()`.

| Lớp | File | Phương thức |
| --- | --- | --- |
| User | `accounts/models.py` | `login(request, email, password)`, `logout(request)`, `is_active` |
| Admin | `accounts/models.py` | `create_user`, `update_user`, `lock_user`, `delete_user` |
| Teacher | `accounts/models.py` | `manage_questions`, `create_exam`, `manage_exam`, `assign_students`, `view_results` |
| Student | `accounts/models.py` | `view_available_exams`, `start_exam`, `save_answer`, `submit_exam`, `view_result` |
| Question | `questions/models.py` | `add_option`, `validate_options`, `create_revision`, `archive` (+ `activate`, `option_errors`, `is_locked`) |
| AnswerOption | `questions/models.py` | `update_content`, `set_correct` |
| Exam | `exams/models.py` | `add_question`, `publish`, `can_start`, `publish_results` (+ `apply_settings`, `close`, `cannot_start_reason`) |
| ExamQuestion | `exams/models.py` | `set_position`, `set_points` |
| ExamParticipant | `exams/models.py` | `grant_access`, `revoke_access`, `can_participate` |
| Submission | `attempts/models.py` | `save_answer`, `submit`, `auto_submit`, `grade`, `is_editable` |
| SubmissionAnswer | `attempts/models.py` | `select_option`, `clear_selection` |
| Result | `results/models.py` | `calculate`, `can_view` |

Phương thức trong ngoặc `(+ …)` là phần thêm để giao diện dùng, không có trong sơ đồ. Muốn thêm phương thức
mới vào lớp nào thì báo PM để cập nhật sơ đồ lớp cho khớp.

## 3. Quy tắc bắt buộc khi viết code

- Tên bảng, cột đúng như mô hình dữ liệu đã duyệt (ví dụ `users.user_id`, `full_name`, `password_hash`).
- Trạng thái viết HOA: `ADMIN`/`TEACHER`/`STUDENT`; `ACTIVE`/`LOCKED`/`DELETED`; `DRAFT`/`PUBLISHED`/`CLOSED`/`ARCHIVED`; `IN_PROGRESS`/`SUBMITTED`/`GRADED`.
- Không cho xóa dữ liệu đang được bài thi dùng (khóa ngoại `PROTECT`), để giữ lịch sử.
- Lưu giờ chuẩn quốc tế (UTC), hiển thị giờ Việt Nam.
- Email bỏ khoảng trắng, đổi chữ thường trước khi lưu.
- Kiểm tra quyền ở phía máy chủ; ẩn nút trên giao diện là chưa đủ.
- Không chèn dữ liệu người dùng nhập vào JavaScript trong HTML (`onclick="...{{ }}..."`), tránh bị chèn mã độc.
- Ràng buộc Django không viết được (khóa ngoại nhiều cột, chặn `NaN`, trigger `updated_at`) để trong file `0002_db_rules.py` của từng app.
- Database đã tự chặn dữ liệu trùng, liên kết sai, giá trị không hợp lệ. Code website **phải tự kiểm tra** thêm:
  không khóa Admin cuối cùng; câu hỏi kích hoạt phải có ≥ 2 phương án và đúng 1 đáp án đúng; không sửa đề đã
  phát hành; hạn nộp và tự nộp; chấm đúng điểm; chỉ công bố điểm khi đủ điều kiện.

## 4. Việc chưa quyết định

| Việc | Cần quyết định gì |
| --- | --- |
| Đưa website lên mạng | Chỉ demo trên máy cá nhân, hay thuê máy chủ để truy cập qua Internet |
| Thử tải | Cách kiểm tra website chịu được 500 sinh viên thi cùng lúc như đặc tả yêu cầu |
| Sao lưu | Cách sao lưu dữ liệu hằng ngày và khôi phục khi có sự cố |
