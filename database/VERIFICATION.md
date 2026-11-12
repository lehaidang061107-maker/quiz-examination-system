# Kết quả kiểm tra task S3-21

**Kết quả: 8/8 bài kiểm thử đạt.** Một bài có thêm 37 tình huống nhập dữ liệu sai;
tất cả đều bị database từ chối đúng như mong đợi.

Ghi nhận ngày **12/11/2026** trên macOS, Python 3.14.2 và PostgreSQL 17.11 qua Docker.
Phiên bản database: `0001 (head)`. Lần chạy đã ghi nhận mất 1.335 giây.

## Đã kiểm tra những gì?

| Nội dung | Kết quả |
| --- | --- |
| Tạo database từ đầu bằng migration | Đủ 9 bảng nghiệp vụ và bảng theo dõi phiên bản |
| Quay lui rồi tạo lại | Xóa được bảng/hàm tự cập nhật thời gian, sau đó tạo và nạp mẫu lại được |
| Dữ liệu sai hoặc trùng | Chặn email trùng/chưa chuẩn hóa, trạng thái/vai trò sai, nội dung rỗng, điểm/thời gian/số câu không hợp lệ |
| Liên kết giữa các bảng | Chặn tham chiếu không tồn tại, sai đề/câu/phương án và xóa dữ liệu đang được tham chiếu |
| Một lượt và một kết quả | Chặn lượt, câu trả lời và kết quả bị trùng |
| Trường được để trống | Cho phép bỏ chọn đáp án, câu nháp chưa có nội dung và đề không giới hạn thời lượng/lịch |
| Chạy lại dữ liệu mẫu | Không thêm dòng hoặc đổi dữ liệu/mật khẩu đã có |
| Mật khẩu và điểm demo | Mật khẩu băm kiểm tra được; điểm, tổng điểm và số câu khớp phép tính từ đáp án |
| Thời gian cập nhật và chỉ mục | Tự cập nhật `updated_at` trên 3 bảng; có các chỉ mục hỗ trợ tra cứu |

Ngoài ra, đã kiểm tra xuất SQL để xem trước migration/rollback, định dạng thay đổi
Git và việc Git bỏ qua `.env`/`.venv`.

## Tự chạy lại

Mở Docker Desktop. Tại thư mục gốc dự án, chạy:

```bash
source .venv/bin/activate
docker compose up -d --wait db
python -m unittest discover -s tests/integration -v
```

Cuối màn hình phải có `Ran 8 tests` và `OK`. Chi tiết nằm ở
`tests/integration/test_database.py`.

Test chạy trong khu vực tạm, không xóa bảng ứng dụng trong `public`. Sau lần kiểm
tra đã ghi nhận, khu vực tạm được dọn và dữ liệu demo vẫn đủ như bảng số lượng
trong [hướng dẫn dữ liệu mẫu](seeds/README.md).

Báo cáo này xác nhận phần database. Website, phân quyền, phát hành đề, nộp/chấm bài,
công bố điểm và tải 500 sinh viên cần được kiểm tra ở các task ứng dụng tiếp theo.
Xem [hướng dẫn chạy và phạm vi bàn giao](README.md).
