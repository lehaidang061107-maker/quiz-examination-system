# Kết quả kiểm tra database

**Đạt 8/8 bài kiểm tra.** Thử nhập 37 kiểu dữ liệu sai, database đều chặn đúng.

| Đã kiểm tra | Kết quả |
| --- | --- |
| Tạo bảng từ đầu, xóa rồi tạo lại | Đủ 9 bảng, làm lại được nhiều lần |
| Dữ liệu sai hoặc trùng | Chặn email trùng, vai trò/trạng thái lạ, nội dung rỗng, điểm/thời gian/số câu không hợp lệ |
| Liên kết giữa các bảng | Chặn chọn đáp án của câu khác, câu không có trong đề, xóa dữ liệu đang được dùng |
| Một lượt, một kết quả | Mỗi sinh viên chỉ một lượt làm và một kết quả cho mỗi đề |
| Được phép để trống | Bỏ chọn đáp án, câu nháp chưa có nội dung, đề không giới hạn thời gian |
| Dữ liệu mẫu | Chạy lại không trùng; mật khẩu được mã hóa; điểm mẫu tính đúng |
| Tự cập nhật thời gian, chỉ mục | `updated_at` tự đổi khi sửa; có đủ chỉ mục để tra cứu nhanh |

**Tự kiểm tra lại:** bật Docker, chạy `python -m unittest discover -s tests/integration -v`;
cuối màn hình có `Ran 8 tests` và `OK` là đạt. Bài kiểm tra chạy trong vùng tạm riêng rồi tự dọn,
không đụng dữ liệu bạn đang dùng.

**Chưa kiểm tra:** website, phân quyền, phát hành đề, nộp và chấm bài, công bố điểm, 500 sinh viên thi cùng lúc.
