# Member Git & Jira Workflow

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

---

## 4. Test

Chạy test trước khi push. Thêm test cho phần mình viết trong `src/<app>/tests/`.

```bash
cd src
python manage.py test
```

PostgreSQL phải đang chạy (`docker compose up -d --wait db`).

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
