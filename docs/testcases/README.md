# Testing

<!-- toc -->

**Mục lục**

- [Unit test](#unit-test)
- [Manual Testing (Browser)](#manual-testing-browser)
- [Test Cases (CSV)](#test-cases-csv)
- [Export Test Report (PM)](#export-test-report-pm)

<!-- /toc -->

Mỗi task cần 3 thứ trước khi tạo PR: **unit test pass**, **đã tự bấm thử trên trình duyệt**, **file test case CSV**.

## Unit test

Viết test cho phần mình làm trong `src/<app>/tests/`. Chạy (database phải đang bật: `docker compose up -d --wait db`):

```bash
cd src
python manage.py test              # cả dự án; cuối kết quả có OK là đạt
python manage.py test accounts     # chỉ một app
```

Test chạy trên database tạm riêng rồi tự xóa, không đụng dữ liệu đang dùng.

- Test quyền: vai trò khác mở thẳng URL phải nhận 403 (mẫu: `src/config/tests/test_layout.py`).
- Đăng nhập sẵn trong test: `self.client.force_login(user)`.

## Manual Testing (Browser)

Chạy website (xem [database/README.md](../../database/README.md)), mở http://127.0.0.1:8000/accounts/login/
và đăng nhập bằng [tài khoản mẫu](../../database/seeds/README.md). Đổi tài khoản: bấm **Đăng xuất** trên thanh menu.

Cần thử thêm:

- **Sai quyền:** đăng nhập vai trò khác rồi gõ thẳng URL trang không phải của mình, phải ra trang 403.
- **Điện thoại:** F12 → biểu tượng điện thoại (Toggle device toolbar) → khung **390 × 844** (NFR-USA-02).
- **Trang lỗi 403/404 tiếng Việt** chỉ hiện khi tắt DEBUG: `DEBUG=False python manage.py runserver --insecure`
  (`--insecure` để vẫn tải được CSS). Thử xong chạy lại bình thường.

Đổi vai trò nhanh không cần gõ mật khẩu (chỉ khi `DEBUG=True`): ở terminal thứ hai, trong `src`, chạy
`python manage.py dev_login teacher@demo.example`. Lệnh in ra `sessionid = ...`; trong Chrome mở
**F12 → Application → Cookies → `http://127.0.0.1:8000`**, sửa dòng `sessionid` thành giá trị vừa in, rồi **F5**.

## Test Cases (CSV)

Test case nộp phải đúng file **Testing Document Template.xlsx** (sai template là 0 điểm phần này).
Không sửa chung file Excel qua Git; mỗi task viết **một file CSV riêng** trong `docs/testcases/`, cuối kỳ PM gộp lại.

1. Copy `docs/testcases/_TEMPLATE.csv` thành `S3-xx.csv` (đúng mã task, ví dụ `S3-07.csv`).
2. Mỗi test case một dòng, 5 cột:

| Cột | Ghi gì | Ví dụ |
| --- | --- | --- |
| Test Case ID | `S3-xx-01`, `S3-xx-02`… (khi gộp script tự đổi thành TC01, TC02…) | `S3-07-01` |
| Function | Tên chức năng + mã FR/NFR | `Manage Questions (FR-05)` |
| Test Steps | Các bước đánh số, mỗi bước một dòng | `1. Mở trang Ngân hàng câu hỏi` ↵ `2. Bấm 'Thêm câu hỏi'` |
| Input Data | Dữ liệu cụ thể đã nhập, mỗi trường một dòng | `Nội dung: 1 + 1 bằng mấy?` |
| Expected Result | Kết quả mong đợi, **ghi đúng nguyên văn câu thông báo** trên giao diện | `Hiện thông báo 'Đã lưu câu hỏi.'` |

3. Kiểm tra ở thư mục gốc dự án, thấy `hợp lệ` là được (sai thì script chỉ rõ file, dòng, ô):

```bash
python scripts/build_testcases.py --check
```

File mẫu đầy đủ: [`_VI_DU_S3-03.csv`](_VI_DU_S3-03.csv). File bắt đầu bằng `_` là mẫu, không được gộp.

**Mỗi chức năng cần:**

- Ít nhất 1 ca **thành công** (luồng chính của Use Case).
- Mỗi **luồng lỗi / luồng thay thế** trong đặc tả Use Case một ca (nhập thiếu, sai định dạng, trùng, sai quyền, hết giờ…).
- Các **quy tắc BR** liên quan (ví dụ BR-14 đề đã phát hành không sửa được).
- Ca **sai quyền**: vai trò khác mở thẳng đường dẫn thì bị chặn.

Tự bấm lại đúng từng bước trên giao diện rồi mới ghi Expected Result; đừng chép từ đặc tả mà chưa chạy thử.
Dữ liệu dùng [tài khoản mẫu](../../database/seeds/README.md) với mật khẩu `Kiemthu2026`.

**Sửa CSV bằng gì:**

- **VS Code** (cài extension *Rainbow CSV*). Ô có dấu phẩy hoặc xuống dòng phải nằm trong ngoặc kép `"..."`.
- Excel cũng được nhưng khi lưu phải chọn **"CSV UTF-8 (Comma delimited)"**, chọn "CSV" thường sẽ hỏng tiếng Việt.
  Xuống dòng trong ô: `Alt + Enter` (Mac: `Option + Enter`).
- Không đổi dòng tiêu đề, không thêm cột.

## Export Test Report (PM)

```bash
pip install -r requirements.txt
python scripts/build_testcases.py
```

Kết quả: `docs/Testing Document - Group04.xlsx`, đúng template của cô (1 sheet `Test Cases`, 5 cột),
test case xếp theo thứ tự task, mã TC01, TC02… liên tục.
