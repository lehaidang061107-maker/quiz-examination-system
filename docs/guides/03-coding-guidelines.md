# 03 · Coding Guidelines

<!-- toc -->

**Mục lục**

- [1. Tech Stack](#1-tech-stack)
- [2. Project Modules](#2-project-modules)
  - [Architecture: MVC](#architecture-mvc)
  - [Building a Page](#building-a-page)
  - [Class Diagram Mapping](#class-diagram-mapping)
- [3. Coding Rules](#3-coding-rules)
- [4. Deployment, Load Testing & Backup](#4-deployment-load-testing--backup)

<!-- /toc -->

Website viết bằng **Python + Django**, dữ liệu lưu trong **PostgreSQL**.
Cả nhóm dùng chung bộ này; không tự chọn công nghệ khác (ví dụ Flask, SQLite).

## 1. Tech Stack

| Việc | Dùng | Ghi chú |
| --- | --- | --- |
| Ngôn ngữ | Python 3.12 – 3.14 | Các bản Django 5.2 hỗ trợ |
| Khung website | Django 5.2 (bản hỗ trợ dài hạn, tới 4/2028) | Ghi bản cụ thể trong `requirements.txt`, hiện là `Django==5.2.19` |
| Giao diện | Django Templates + Bootstrap 5 | Làm theo bản Figma trong `docs/` |
| Lưu dữ liệu | PostgreSQL 17, chạy bằng Docker | [Cách cài](01-getting-started.md). Không dùng SQLite, kể cả khi test |
| Tạo/sửa bảng | Django migrations | Chạy `makemigrations`, đọc lại file sinh ra; không sửa migration đã merge |
| Tài khoản | Model `accounts.User` riêng, đăng nhập bằng email, lưu ở bảng `users` | Phải có trước lần `migrate` đầu tiên |
| Đăng nhập, phiên | Có sẵn của Django, phiên lưu trong database | Tự đăng xuất sau 30 phút không hoạt động; tài khoản bị khóa mất phiên ngay |
| Khóa tạm khi nhập sai | Tự viết | Sai 5 lần liên tiếp thì khóa 15 phút; khác với Admin khóa tài khoản |
| Mật khẩu | Mã hóa có sẵn của Django | Ít nhất 8 ký tự, có cả chữ và số |
| Chống giả mạo form (CSRF) | Có sẵn của Django | Mọi form gửi đi có `{% csrf_token %}` |
| Tự nộp bài khi hết giờ | Lệnh chạy nền `python manage.py run_worker` (service `worker` trong Docker), kiểm tra mỗi 5 giây | Khóa từng bài khi xử lý để không nộp/chấm trùng; chấm lại bài chấm lỗi |
| Kiểm thử | `python manage.py test` | Django tự tạo database thử riêng, không đụng dữ liệu thật |
| Cấu hình bí mật | File `.env` trên máy mình (mẫu: `.env.example`) | `SECRET_KEY`, mật khẩu không viết trong code, không đưa lên GitHub |

## 2. Project Modules

| Phần (app) | Lo việc gì |
| --- | --- |
| `config` | Cấu hình chung, Trang chủ theo vai trò, menu (`navigation.py`), trang `/health` kiểm tra website còn chạy |
| `accounts` | Đăng ký Student, đăng nhập/đăng xuất, khóa tạm, Admin quản lý tài khoản |
| `questions` | Ngân hàng câu hỏi và phương án |
| `exams` | Tạo đề, phát hành đề, giao đề cho sinh viên |
| `attempts` | Làm bài, tự lưu đáp án, nộp bài, tự nộp khi hết giờ |
| `results` | Chấm điểm, công bố và xem kết quả |

Mỗi phần có `urls.py` riêng và phải được khai báo trong `config/urls.py`, nếu không trang sẽ báo 404.

### Architecture: MVC

Nhóm chọn mẫu kiến trúc **MVC (Model – View – Controller)**. Django gọi là MVT nhưng vai trò giống nhau:

| MVC | Trong code | Làm gì | Không được làm |
| --- | --- | --- | --- |
| **Model** | `models.py` | Lớp theo sơ đồ lớp, lưu dữ liệu, **mọi quy tắc nghiệp vụ** (phát hành đề, chấm điểm, khóa tài khoản…) | Đọc `request`, trả HTML |
| **View** | `templates/<app>/*.html` | Hiển thị giao diện theo Figma | Truy vấn database, tính toán nghiệp vụ |
| **Controller** | `views.py` + `urls.py` | Nhận yêu cầu, kiểm tra đăng nhập/vai trò, đọc form, **gọi phương thức của Model**, chọn template | Tự viết lại quy tắc đã có trong Model |

Phương thức Model báo lỗi nghiệp vụ bằng `ValidationError` (thông báo tiếng Việt, hiển thị thẳng cho
người dùng) và lỗi sai quyền bằng `PermissionDenied`.

### Building a Page

Một trang gồm 3 phần.

**1. `views.py` (Controller):** kiểm tra quyền, gọi phương thức Model, báo kết quả bằng `messages`.

```python
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from accounts.models import Role


@role_required(Role.TEACHER)                   # BẮT BUỘC: sai vai trò -> 403, chưa đăng nhập -> trang Đăng nhập
def publish_exam(request, exam_id):
    teacher = request.user.as_role()            # lớp Teacher theo sơ đồ lớp
    exam = teacher.manage_exam(exam_id)         # đề của người khác -> 403 tự động
    if request.method == "POST":
        try:
            exam.publish()                      # quy tắc nghiệp vụ nằm trong Model
            messages.success(request, "Đã phát hành đề thi.")
            return redirect("exams:list")
        except ValidationError as error:
            for text in error.messages:         # thông báo tiếng Việt có sẵn trong Model
                messages.error(request, text)
    return render(request, "exams/publish.html", {"exam": exam})
```

**2. `templates/<app>/<trang>.html` (View):** kế thừa layout chung, chỉ điền các block.

```html
{% extends "base.html" %}
{% block title %}Phát hành đề{% endblock %}
{% block page_title %}Phát hành đề thi{% endblock %}
{% block page_subtitle %}{{ exam.title }}{% endblock %}
{% block page_actions %}<a class="btn btn-outline-secondary" href="{% url 'exams:list' %}">Quay lại</a>{% endblock %}
{% block content %}
  <form method="post">{% csrf_token %}
    <button class="btn btn-primary">Phát hành</button>
  </form>
{% endblock %}
```

Trang chưa đăng nhập (Đăng nhập, Đăng ký) dùng các block `auth_title`, `auth_subtitle`, `auth_content`.
Thông báo `messages`, thanh trên, menu trái đã có sẵn trong `base.html`, không viết lại.

**3. `urls.py`:** đặt `name=` đúng như menu trong `src/config/navigation.py` (ví dụ `questions:list`, `exams:list`).
Đúng tên thì menu tự hiện link; chưa có thì hiện mờ "Sắp có".

### Class Diagram Mapping

Tên phương thức theo sơ đồ lớp (mục 5.2 tài liệu đặc tả), viết kiểu Python: `viewAvailableExams()` → `view_available_exams()`.
Admin/Teacher/Student là proxy model của `User` (cùng bảng `users`); lấy từ phiên bằng `request.user.as_role()`.

| Lớp | File | Phương thức |
| --- | --- | --- |
| User | `accounts/models.py` | `login(request, email, password)`, `logout(request)`, `is_active` |
| Admin | `accounts/models.py` | `create_user`, `update_user`, `lock_user`, `delete_user` (+ `unlock_user`) |
| Teacher | `accounts/models.py` | `manage_questions`, `create_exam`, `manage_exam`, `assign_students`, `view_results` |
| Student | `accounts/models.py` | `view_available_exams`, `start_exam`, `save_answer`, `submit_exam`, `view_result` |
| Question | `questions/models.py` | `add_option`, `validate_options`, `create_revision`, `archive` (+ `activate`, `option_errors`, `is_locked`) |
| AnswerOption | `questions/models.py` | `update_content`, `set_correct` |
| Exam | `exams/models.py` | `add_question`, `publish`, `can_start`, `publish_results` (+ `apply_settings`, `remove_question`, `close`, `archive`, `cannot_start_reason`) |
| ExamQuestion | `exams/models.py` | `set_position`, `set_points` |
| ExamParticipant | `exams/models.py` | `grant_access`, `revoke_access`, `can_participate` |
| Submission | `attempts/models.py` | `save_answer`, `submit`, `auto_submit`, `grade`, `is_editable` (+ `start`) |
| SubmissionAnswer | `attempts/models.py` | `select_option`, `clear_selection` |
| Result | `results/models.py` | `calculate`, `can_view` (+ `answered_count`, `wrong_count`, `blank_count`, `completion_time`) |

Phương thức trong ngoặc `(+ …)` là phần thêm để giao diện dùng, không có trong sơ đồ. Muốn thêm phương thức
mới vào lớp nào thì báo PM để cập nhật sơ đồ lớp cho khớp.

## 3. Coding Rules

- Tên bảng, cột đúng như mô hình dữ liệu đã duyệt (ví dụ `users.user_id`, `full_name`, `password_hash`).
- Trạng thái viết HOA: `ADMIN`/`TEACHER`/`STUDENT`; `ACTIVE`/`LOCKED`/`DELETED`; `DRAFT`/`PUBLISHED`/`CLOSED`/`ARCHIVED`; `IN_PROGRESS`/`SUBMITTED`/`GRADED`.
- Không cho xóa dữ liệu đang được bài thi dùng (khóa ngoại `PROTECT`), để giữ lịch sử.
- Lưu giờ chuẩn quốc tế (UTC), hiển thị giờ Việt Nam.
- Email bỏ khoảng trắng, đổi chữ thường trước khi lưu.
- Kiểm tra quyền ở phía máy chủ; ẩn nút trên giao diện là chưa đủ.
- Không chèn dữ liệu người dùng nhập vào JavaScript trong HTML (`onclick="...{{ }}..."`), tránh bị chèn mã độc.
- Mọi view cần đăng nhập đều có `@role_required(...)` (hoặc `@login_required_any_role`).
- Không tính toán nghiệp vụ trong view hay template; thiếu phương thức thì thêm vào Model (báo PM để cập nhật sơ đồ lớp).
- Form gửi dữ liệu dùng `method="post"` và `{% csrf_token %}`.
- Thêm thư viện: **thêm dòng** vào `requirements.txt` với phiên bản cố định (ví dụ `Django==5.2.19`).
  Không chạy `pip freeze > requirements.txt` (ghi đè thư viện của người khác, trên Windows còn lưu thành UTF-16).
- Đổi model: `python manage.py makemigrations <app>` rồi đọc lại file vừa sinh, commit migration cùng model.
  Không sửa migration đã merge, không `CREATE TABLE` trong code.
- Sửa hay thêm tiêu đề `##`/`###` trong file `.md`: chạy `python scripts/update_toc.py` để cập nhật mục lục.
- Ràng buộc Django không viết được (khóa ngoại nhiều cột, chặn `NaN`, trigger `updated_at`) để trong file `0002_db_rules.py` của từng app.
- Database đã tự chặn dữ liệu trùng, liên kết sai, giá trị không hợp lệ. Code website **phải tự kiểm tra** thêm:
  không khóa Admin cuối cùng; Admin không tự khóa/xóa chính mình; câu hỏi kích hoạt phải có ≥ 2 phương án và
  đúng 1 đáp án đúng; không sửa đề đã phát hành; hạn nộp và tự nộp; chấm đúng điểm; chỉ công bố điểm khi đủ điều kiện.

## 4. Deployment, Load Testing & Backup

| Việc | Đã quyết định | Ai làm |
| --- | --- | --- |
| Đưa website lên mạng | Chỉ demo trên máy cá nhân bằng Docker (`http://127.0.0.1:8000`), không thuê máy chủ. Vì không đưa lên Internet nên chưa bật HTTPS (NFR-SEC-08); ghi rõ hạn chế này trong báo cáo | S3-30 |
| Thử tải (NFR-PER-01 → 06) | Dùng **Locust** giả lập sinh viên: đăng nhập → xem danh sách → làm bài, lưu đáp án mỗi 10 giây → nộp bài. Chạy website bằng Docker + gunicorn (không đo trên `runserver`), tăng dần 50 → 100 → 200 → 500 người. Ghi cấu hình máy, p95 thời gian phản hồi, tỉ lệ lỗi, thời gian chấm; chưa đạt 500 thì ghi đúng mức đạt được, không ghi "Đã đạt" | S3-10, làm sau khi có trang đăng nhập, làm bài, nộp bài |
| Sao lưu (NFR-REL-04) | `pg_dump` chép database ra file `backups/quiz_<ngày>.sql.gz`, giữ 7 bản mới nhất; có lệnh khôi phục. Demo: sao lưu → xóa dữ liệu → khôi phục → dữ liệu quay lại. Chạy hằng ngày bằng lịch (cron) trên máy demo | S3-25 |
