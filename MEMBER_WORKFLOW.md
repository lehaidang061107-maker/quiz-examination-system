# Member Git & Jira Workflow

<!-- toc -->

**Mục lục**

- [1. Nhận Task](#1-nhận-task)
- [2. Tạo Branch](#2-tạo-branch)
- [3. Code](#3-code)
  - [Viết một trang (MVC)](#viết-một-trang-mvc)
- [4. Test](#4-test)
  - [Chạy thử trên trình duyệt](#chạy-thử-trên-trình-duyệt)
  - [Test case (nộp cho cô)](#test-case-nộp-cho-cô)
- [5. Push](#5-push)
- [6. Tạo Pull Request](#6-tạo-pull-request)
- [7. Sau Khi Tạo PR](#7-sau-khi-tạo-pr)
- [8. Nếu Có Merge Conflict](#8-nếu-có-merge-conflict)
- [9. Member Checklist](#9-member-checklist)
  - [Chỉ cần nhớ](#chỉ-cần-nhớ)

<!-- /toc -->

Quy trình này áp dụng cho mọi task trong giai đoạn 3. Công nghệ phải dùng xem ở
[TECH_STACK.md](TECH_STACK.md).

## 1. Nhận Task

Vào Jira (dự án `CNPM`) và xem task được assign. Tên task có mã giai đoạn, ví dụ:

```text
CNPM-3 · S3-02 Đăng ký tài khoản Student
```

Nếu task phụ thuộc chưa merge vào `develop`, báo PM trước khi bắt đầu.

Chuyển task:

```text
To Do → In Progress
```

---

## 2. Tạo Branch

Luôn tạo branch từ `develop` mới nhất.

```bash
git checkout develop
git pull
git checkout -b feature/S3-02-register-student
```

Format:

```text
feature/S3-xx-<mo-ta-ngan>     # chức năng mới
fix/S3-xx-<mo-ta-ngan>         # sửa lỗi
docs/<mo-ta-ngan>              # chỉ sửa tài liệu
```

Dùng mã `S3-xx` (không dùng `CNPM-x`) để nhìn tên nhánh là biết task. Mô tả viết thường, không dấu, nối bằng `-`.

---

## 3. Code

Làm đúng phạm vi của Jira task. Một PR chỉ cho một task; không gộp code của task khác.

Trước khi commit, luôn xem mình sắp commit những gì:

```bash
git status
git add <file cần commit>
git commit -m "feat(S3-02): add student registration"
```

Không dùng `git add .` khi chưa kiểm tra `git status`. Không commit:

```text
.env, mật khẩu, API key, secret
file database: *.db, *.sqlite3
__pycache__/, .venv/
```

Khi thêm thư viện, **thêm dòng** vào `requirements.txt` với phiên bản cố định (ví dụ `Django==5.2.19`).
Không chạy `pip freeze > requirements.txt` vì lệnh này ghi đè thư viện của người khác;
trên Windows PowerShell còn lưu file thành UTF-16.

Khi đổi model, tạo migration rồi đọc lại file vừa sinh:

```bash
cd src
python manage.py makemigrations <app>
python manage.py migrate
```

Commit file migration cùng với model. Không sửa migration đã merge, không `CREATE TABLE` trong code.

Sửa hay thêm tiêu đề `##`/`###` trong file `.md` thì chạy `python scripts/update_toc.py` để cập nhật mục lục ở đầu file.

### Viết một trang (MVC)

Kiến trúc MVC xem [TECH_STACK.md](TECH_STACK.md). Một trang gồm 3 phần:

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

**3. `urls.py`:** đặt `name=` đúng như menu trong `src/config/navigation.py` (ví dụ `questions:list`,
`exams:list`, `accounts:login`, `accounts:logout`). Đúng tên thì menu tự hiện link; chưa có thì hiện mờ "Sắp có".

Quy tắc:

- Mọi view cần đăng nhập đều có `@role_required(...)`. Ẩn nút trên giao diện là chưa đủ.
- Không tính toán nghiệp vụ trong view hay template; thiếu phương thức thì thêm vào Model (báo PM để cập nhật sơ đồ lớp).
- Form gửi dữ liệu dùng `method="post"` và `{% csrf_token %}`.
- Test quyền: vai trò khác mở thẳng URL phải nhận 403 (xem mẫu `src/config/tests/test_layout.py`).
- Trước khi có trang Đăng nhập (S3-03), thử giao diện bằng unit test với `self.client.force_login(user)`.

---

## 4. Test

Chạy test trước khi push. Thêm test cho phần mình viết trong `src/<app>/tests/`.

```bash
cd src
python manage.py test
```

PostgreSQL phải đang chạy (`docker compose up -d --wait db`).

### Chạy thử trên trình duyệt

```bash
cd src
python manage.py runserver          # mở http://127.0.0.1:8000/
```

**Đăng nhập tạm** (dùng tới khi có trang Đăng nhập của S3-03): mở terminal thứ hai trong `src`, chạy

```bash
python manage.py dev_login teacher@demo.example     # hoặc admin@..., student1@..., student2@...
```

Lệnh in ra `sessionid = ...`. Trong Chrome: **F12 → Application → Cookies → `http://127.0.0.1:8000`**,
sửa (hoặc thêm) dòng tên `sessionid`, dán giá trị vừa in, rồi **F5**. Đổi tài khoản thì chạy lại lệnh với email khác.
Lệnh chỉ chạy khi `DEBUG=True`.

**Kiểm tra thêm:**

- Giao diện điện thoại: F12 → biểu tượng điện thoại (Toggle device toolbar) → khung **390 × 844** (NFR-USA-02).
- Trang lỗi 403/404 tiếng Việt chỉ hiện khi tắt DEBUG: `DEBUG=False python manage.py runserver --insecure`
  (`--insecure` để vẫn tải được CSS). Thử xong chạy lại bình thường.
- Sai quyền: đăng nhập vai trò khác rồi gõ thẳng URL trang của mình, phải ra trang 403.
- Cần kiểm tra những gì thì xem test case của task trong `docs/testcases/S3-xx.csv`.

### Test case (nộp cho cô)

Viết test case của task vào `docs/testcases/S3-xx.csv` và commit **cùng PR với code**.
Cách viết xem [docs/testcases/README.md](docs/testcases/README.md). Kiểm tra trước khi push:

```bash
python scripts/build_testcases.py --check
```

---

## 5. Push

```bash
git push -u origin feature/S3-02-register-student
```

---

## 6. Tạo Pull Request

Tạo PR:

```text
feature/S3-02-register-student → develop
```

Không tạo PR vào `main`. `main` chỉ nhận merge từ `develop` khi nhóm chốt một bản.

Tên PR:

```text
[S3-02] Đăng ký tài khoản Student
```

Trong PR ghi ngắn gọn:

```text
## Thay đổi
- Thêm trang và route đăng ký Student
- Kiểm tra mật khẩu ≥ 8 ký tự, có chữ và số

## Cách test
- python manage.py test accounts → OK
- Test case: docs/testcases/S3-02.csv (5 ca), build_testcases.py --check → hợp lệ
- Chạy thử: đăng ký email mới, email trùng, mật khẩu không khớp

## Jira
CNPM-3
```

---

## 7. Sau Khi Tạo PR

Chuyển Jira:

```text
In Progress → In Review
```

Sau đó chờ review và merge.

Nếu người review yêu cầu sửa:

```text
Sửa code
↓
commit
↓
push lên cùng branch
↓
PR tự update
```

Nếu PR còn lỗi chặn merge, task được chuyển lại `In Progress`.

---

## 8. Nếu Có Merge Conflict

**Không cần tự xử lý.**

Báo PM:

```text
"S3-02 đang conflict, nhờ PM xử lý giúp."
```

---

## 9. Member Checklist

```text
Jira task (kiểm tra phụ thuộc)
   ↓
In Progress
   ↓
Branch feature/S3-xx-... từ develop
   ↓
Code + unit test + test case CSV
   ↓
git status → commit
   ↓
Push
   ↓
PR vào develop
   ↓
In Review
   ↓
Sửa nếu cần
   ↓
Done
```

### Chỉ cần nhớ

```text
1 Jira task = 1 branch = 1 PR vào develop
```
