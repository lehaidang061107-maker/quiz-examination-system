# Test case

<!-- toc -->

**Mục lục**

- [Việc của mỗi thành viên](#việc-của-mỗi-thành-viên)
- [Mỗi chức năng cần những test case nào](#mỗi-chức-năng-cần-những-test-case-nào)
- [Dữ liệu dùng khi kiểm thử](#dữ-liệu-dùng-khi-kiểm-thử)
- [Sửa file CSV bằng gì](#sửa-file-csv-bằng-gì)
- [Gộp thành file nộp (PM làm)](#gộp-thành-file-nộp-pm-làm)

<!-- /toc -->

Test case nộp cho cô phải theo đúng file **Testing Document Template.xlsx** (sai template là 0 điểm phần này).
Cả nhóm không sửa chung một file Excel qua Git (sẽ conflict, mất bài). Mỗi task viết vào **một file CSV riêng**;
cuối kỳ PM chạy script gộp tất cả vào template.

## Việc của mỗi thành viên

Làm xong chức năng của task nào thì viết test case cho task đó, **commit trong cùng PR với code**.

1. Copy `_TEMPLATE.csv` thành `S3-xx.csv` (đúng mã task, ví dụ `S3-07.csv`).
2. Viết mỗi test case một dòng, 5 cột:

| Cột | Ghi gì | Ví dụ |
| --- | --- | --- |
| Test Case ID | `S3-xx-01`, `S3-xx-02`… (script tự đổi thành TC01, TC02… khi gộp) | `S3-07-01` |
| Function | Tên chức năng + mã FR/NFR | `Manage Questions (FR-05)` |
| Test Steps | Các bước đánh số, mỗi bước một dòng | `1. Mở trang Ngân hàng câu hỏi` ↵ `2. Bấm 'Thêm câu hỏi'` |
| Input Data | Dữ liệu cụ thể đã nhập, mỗi trường một dòng | `Nội dung: 1 + 1 bằng mấy?` |
| Expected Result | Kết quả mong đợi, **ghi đúng nguyên văn câu thông báo** trên giao diện | `Hiện thông báo 'Đã lưu câu hỏi.'` |

3. Kiểm tra trước khi tạo PR (ở thư mục gốc dự án):

```bash
python scripts/build_testcases.py --check
```

Thấy `hợp lệ` là được; có lỗi thì script chỉ rõ file, dòng, ô nào cần sửa.

Xem file mẫu đầy đủ: [`_VI_DU_S3-03.csv`](_VI_DU_S3-03.csv) (Đăng nhập, 7 test case).

## Mỗi chức năng cần những test case nào

- Ít nhất 1 ca **thành công** (luồng chính của Use Case).
- Mỗi **luồng lỗi / luồng thay thế** trong đặc tả Use Case một ca (nhập thiếu, sai định dạng, trùng, sai quyền, hết giờ…).
- Các **quy tắc BR** liên quan (ví dụ BR-14 đề đã phát hành không sửa được).
- Ca **sai quyền**: vai trò khác mở thẳng đường dẫn thì bị chặn.

Tự làm lại đúng từng bước trên giao diện trước khi ghi Expected Result; đừng chép từ đặc tả mà chưa chạy thử.

## Dữ liệu dùng khi kiểm thử

Dùng tài khoản demo (`python manage.py seed_demo`), đặt `DEMO_PASSWORD=Kiemthu2026` trong `.env` **trước khi** seed
để mọi người ghi cùng một mật khẩu:

| Email | Vai trò |
| --- | --- |
| `admin@demo.example` | Admin |
| `teacher@demo.example`, `teacher2@demo.example` | Teacher |
| `student1@demo.example`, `student2@demo.example`, `student3@demo.example` | Student |

## Sửa file CSV bằng gì

- **Nên dùng VS Code** (cài extension *Rainbow CSV* cho dễ nhìn). Ô có dấu phẩy hoặc xuống dòng phải nằm trong ngoặc kép `"..."`.
- Dùng Excel cũng được nhưng khi lưu phải chọn **"CSV UTF-8 (Comma delimited)"**; chọn "CSV" thường sẽ hỏng tiếng Việt.
  Trong ô Excel, xuống dòng bằng `Alt + Enter` (Mac: `Option + Enter`).
- Không đổi dòng tiêu đề, không thêm cột.

## Gộp thành file nộp (PM làm)

```bash
pip install -r requirements.txt
python scripts/build_testcases.py
```

Kết quả: `docs/Testing Document - Group04.xlsx`, đúng template của cô (1 sheet `Test Cases`, 5 cột, giữ định dạng),
test case xếp theo thứ tự task, mã TC01, TC02… liên tục. File bắt đầu bằng `_` là mẫu, không được gộp vào.
