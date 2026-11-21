# Database Verification Report

Kết quả kiểm tra phần database (giai đoạn 3, trước khi làm chức năng website).

**Lần kiểm tra database đạt toàn bộ 19 bài kiểm tra.** Thử nhập 37 kiểu dữ liệu sai,
database đều chặn đúng, và mỗi kiểu bị chặn bởi đúng ràng buộc dành cho nó.

**Hiện tại (22/11/2026):** cả dự án có 213 bài kiểm tra (database + chức năng website), chạy `python manage.py test` đều đạt.

| Đã kiểm tra | Kết quả |
| --- | --- |
| Tạo bảng từ đầu, xóa rồi tạo lại | Đủ 9 bảng, quay lui toàn bộ migration rồi tạo lại được |
| Dữ liệu sai hoặc trùng | Chặn email trùng/chưa chuẩn hóa, vai trò/trạng thái lạ, nội dung rỗng, điểm/thời gian/số câu không hợp lệ |
| Liên kết giữa các bảng | Chặn chọn đáp án của câu khác, câu không có trong đề, sai đề, xóa dữ liệu đang được dùng |
| Một lượt, một kết quả | Mỗi sinh viên chỉ một lượt làm và một kết quả cho mỗi đề |
| Được phép để trống | Bỏ chọn đáp án, câu nháp chưa có nội dung, đề không giới hạn thời gian |
| Dữ liệu mẫu | Đúng số dòng từng bảng; chạy lại không trùng; mật khẩu được mã hóa; mật khẩu yếu bị từ chối; điểm mẫu tính đúng |
| Tài khoản | Email được chuẩn hóa khi lưu; chỉ tài khoản `ACTIVE` mới đăng nhập được; chỉ Admin vào được trang quản trị |
| Tự cập nhật thời gian, chỉ mục | `updated_at` tự đổi khi sửa; có đủ chỉ mục để tra cứu nhanh |
| Cấu hình website | Trang `/health/`, phiên 30 phút, mật khẩu ≥ 8 ký tự, giờ Việt Nam |

**Tự kiểm tra lại:** bật Docker, vào thư mục `src`, chạy `python manage.py test`;
cuối màn hình có `OK` là đạt. Kiểm thử chạy trên database tạm riêng rồi tự xóa, không đụng dữ liệu bạn đang dùng.

Code kiểm thử database: `src/config/tests/`. Kiểm thử chức năng nằm trong `src/<app>/tests/` của từng phần
(đăng nhập, khóa tạm, phân quyền, quản lý tài khoản, ngân hàng câu hỏi, làm bài, tự lưu, nộp bài, tự nộp khi hết giờ,
chấm điểm, xem kết quả).

**Chưa kiểm tra:** trang quản lý đề thi của giảng viên (tạo, phát hành, giao đề, đóng đề, công bố điểm) vì chưa có
giao diện, hiện chỉ có test ở mức Model; 500 sinh viên thi cùng lúc (S3-10); sao lưu và khôi phục (S3-25).
