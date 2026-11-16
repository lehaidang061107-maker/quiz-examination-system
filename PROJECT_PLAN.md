# Kế hoạch thực hiện

Dự án làm theo 4 giai đoạn của môn học ([GUIDELINES.md](GUIDELINES.md)).
Mỗi giai đoạn có sản phẩm phải nộp; xong giai đoạn trước mới chuyển sang giai đoạn sau.

## Các giai đoạn

| Giai đoạn | Cần làm gì | Xong khi |
| --- | --- | --- |
| 1. Phân tích yêu cầu | Viết hệ thống cần làm gì (FR), cần đạt chất lượng gì (NFR); vẽ sơ đồ DFD, Use Case, Class | Cả nhóm đọc lại và đồng ý |
| 2. Thiết kế | Thiết kế giao diện, cách tổ chức phần mềm, các bảng dữ liệu | Tài liệu đủ 7 phần theo guidelines |
| 3. Làm phần mềm | Viết code từng chức năng, kèm test | Chạy được đủ chức năng; người khác cài và chạy được theo hướng dẫn |
| 4. Kiểm thử | Viết các ca kiểm thử, chạy thử, ghi và sửa lỗi | Mỗi yêu cầu đều có kiểm thử; không còn lỗi làm hỏng luồng chính |

Tài liệu giai đoạn 1–2 nằm trong thư mục [`docs/`](docs/).

## Giai đoạn 3: làm theo thứ tự

1. Dựng khung website (Django).
2. Chuyển database hiện có sang Django.
3. Làm chức năng: tài khoản → câu hỏi, đề thi → làm bài → chấm điểm, xem kết quả.

Mỗi chức năng là một task trên Jira, làm theo [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md).
Công nghệ phải dùng xem [TECH_STACK.md](TECH_STACK.md).

## Giai đoạn 4: ghi kiểm thử và lỗi thế nào

- **Mỗi ca kiểm thử** ghi: kiểm tra yêu cầu nào, các bước làm, kết quả mong đợi, kết quả thực tế, đạt hay không.
- **Mỗi lỗi** ghi: các bước để gặp lại lỗi, đúng ra phải thế nào, thực tế ra sao, ai sửa.
- Lỗi sửa xong phải kiểm tra lại, kể cả các chức năng liên quan.

## Nộp cuối dự án

- Tài liệu đặc tả và thiết kế đủ 7 phần, kèm file gốc các sơ đồ.
- Mã nguồn trên GitHub, hướng dẫn cài và chạy, dữ liệu mẫu để demo.
- Danh sách ca kiểm thử, kết quả kiểm thử, danh sách lỗi.
