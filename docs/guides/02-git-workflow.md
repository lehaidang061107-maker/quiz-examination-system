# 02 · Git Workflow

<!-- toc -->

**Mục lục**

- [1. Pick a Jira Ticket](#1-pick-a-jira-ticket)
- [2. Create a Branch](#2-create-a-branch)
- [3. Code & Commit](#3-code--commit)
- [4. Test Before Push](#4-test-before-push)
- [5. Push & Open a Pull Request](#5-push--open-a-pull-request)
- [6. Code Review](#6-code-review)
- [Merge Strategy (PM)](#merge-strategy-pm)

<!-- /toc -->

Áp dụng cho mọi task giai đoạn 3. Chỉ cần nhớ:

```text
1 Jira task = 1 branch = 1 PR vào develop
```

## 1. Pick a Jira Ticket

Vào Jira (dự án `CNPM`), xem task được assign. Tên task có mã, ví dụ `CNPM-3 · S3-02 Đăng ký tài khoản Student`.

- Task phụ thuộc chưa merge vào `develop` thì báo PM trước khi bắt đầu.
- Chuyển task `To Do → In Progress`.

## 2. Create a Branch

```bash
git checkout develop
git pull
git checkout -b feature/S3-02-register-student
```

| Loại | Tên branch |
| --- | --- |
| Chức năng mới | `feature/S3-xx-<mo-ta-ngan>` |
| Sửa lỗi | `fix/S3-xx-<mo-ta-ngan>` |
| Chỉ sửa tài liệu | `docs/<mo-ta-ngan>` |

Dùng mã `S3-xx` (không dùng `CNPM-x`). Mô tả viết thường, không dấu, nối bằng `-`.

## 3. Code & Commit

Làm đúng phạm vi task, không gộp code của task khác. Cách viết code xem [03-coding-guidelines.md](03-coding-guidelines.md).

```bash
git status                           # luôn xem trước mình sắp commit gì
git add <file cần commit>            # không dùng "git add ." khi chưa xem git status
git commit -m "feat(S3-02): add student registration"
```

Không commit: `.env`, mật khẩu, API key; file `*.db`, `*.sqlite3`; `__pycache__/`, `.venv/`.

## 4. Test Before Push

Chạy unit test, thử trên trình duyệt và viết test case CSV theo [04-testing.md](04-testing.md).
Test case CSV commit **cùng PR với code**.

## 5. Push & Open a Pull Request

```bash
git push -u origin feature/S3-02-register-student
```

Trên GitHub tạo PR **vào `develop`**. Không tạo PR vào `main`: `main` chỉ nhận merge từ `develop` khi nhóm chốt một bản.

Tên PR: `[S3-02] Đăng ký tài khoản Student`. Nội dung ghi ngắn:

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

Chuyển Jira `In Progress → In Review`.

## 6. Code Review

- Người review yêu cầu sửa: sửa, commit, push lên **cùng branch**, PR tự cập nhật.
- PR còn lỗi chặn merge thì task được chuyển lại `In Progress`.
- PR báo **merge conflict**: không cần tự xử lý, nhắn PM "S3-02 đang conflict, nhờ PM xử lý giúp."
- PR được merge thì chuyển Jira sang `Done`.

## Merge Strategy (PM)

Merge PR luôn chọn **Create a merge commit** (bấm mũi tên ▾ cạnh nút xanh nếu nút đang ghi "Squash and merge"),
để giữ commit riêng của từng thành viên.

PR của thành viên còn lỗi mà thành viên không tự sửa được:

1. Đổi base của PR đó sang `develop` (nút **Edit** cạnh tiêu đề PR), **chưa merge**.
2. Tạo branch `fix/S3-xx-...` từ `develop`, merge branch của thành viên vào, sửa lỗi, tạo PR vào `develop`.
3. Merge PR fix bằng **Create a merge commit**. Commit của thành viên vào `develop` theo, PR gốc tự chuyển sang **Merged**.
