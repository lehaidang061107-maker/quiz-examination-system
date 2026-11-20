# 2. Quy trình làm một task

<!-- toc -->

**Mục lục**

- [1. Nhận task trên Jira](#1-nhận-task-trên-jira)
- [2. Tạo branch từ `develop` mới nhất](#2-tạo-branch-từ-develop-mới-nhất)
- [3. Code và commit](#3-code-và-commit)
- [4. Test trước khi push](#4-test-trước-khi-push)
- [5. Push và tạo Pull Request](#5-push-và-tạo-pull-request)
- [6. Sau khi tạo PR](#6-sau-khi-tạo-pr)
- [Cách PM merge và sửa PR lỗi](#cách-pm-merge-và-sửa-pr-lỗi)

<!-- /toc -->

Áp dụng cho mọi task giai đoạn 3. Chỉ cần nhớ:

```text
1 Jira task = 1 branch = 1 PR vào develop
```

## 1. Nhận task trên Jira

Vào Jira (dự án `CNPM`), xem task được assign. Tên task có mã, ví dụ `CNPM-3 · S3-02 Đăng ký tài khoản Student`.

- Task phụ thuộc chưa merge vào `develop` thì báo PM trước khi bắt đầu.
- Chuyển task `To Do → In Progress`.

## 2. Tạo branch từ `develop` mới nhất

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

## 3. Code và commit

Làm đúng phạm vi task, không gộp code của task khác. Cách viết code xem [3-viet-code.md](3-viet-code.md).

```bash
git status                           # luôn xem trước mình sắp commit gì
git add <file cần commit>            # không dùng "git add ." khi chưa xem git status
git commit -m "feat(S3-02): add student registration"
```

Không commit: `.env`, mật khẩu, API key; file `*.db`, `*.sqlite3`; `__pycache__/`, `.venv/`.

## 4. Test trước khi push

Chạy unit test, thử trên trình duyệt và viết test case CSV theo [4-kiem-thu.md](4-kiem-thu.md).
Test case CSV commit **cùng PR với code**.

## 5. Push và tạo Pull Request

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

## 6. Sau khi tạo PR

- Người review yêu cầu sửa: sửa, commit, push lên **cùng branch**, PR tự cập nhật.
- PR còn lỗi chặn merge thì task được chuyển lại `In Progress`.
- PR báo **merge conflict**: không cần tự xử lý, nhắn PM "S3-02 đang conflict, nhờ PM xử lý giúp."
- PR được merge thì chuyển Jira sang `Done`.

## Cách PM merge và sửa PR lỗi

Merge PR luôn chọn **Create a merge commit** (bấm mũi tên ▾ cạnh nút xanh nếu nút đang ghi "Squash and merge"),
để giữ commit riêng của từng thành viên.

PR của thành viên còn lỗi mà thành viên không tự sửa được:

1. Đổi base của PR đó sang `develop` (nút **Edit** cạnh tiêu đề PR), **chưa merge**.
2. Tạo branch `fix/S3-xx-...` từ `develop`, merge branch của thành viên vào, sửa lỗi, tạo PR vào `develop`.
3. Merge PR fix bằng **Create a merge commit**. Commit của thành viên vào `develop` theo, PR gốc tự chuyển sang **Merged**.
