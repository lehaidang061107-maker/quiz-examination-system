# Non-Functional Requirements

Trạng thái: Chưa soạn. Phụ trách giai đoạn 1: TV2.

<!-- Mỗi NFR cần: mã, mô tả, điều kiện đánh giá, cách kiểm chứng và ngưỡng được nhóm thống nhất khi phù hợp. -->

## Bảo mật
•	NFR01 – Xác thực: Người dùng phải đăng nhập bằng tài khoản hợp lệ mới được sử dụng hệ thống. Phiên đăng nhập tự động hết hạn sau một khoảng thời gian không hoạt động (ví dụ 30 phút) và bị hủy khi người dùng đăng xuất.

•	NFR02 – Phân quyền: Hệ thống kiểm soát truy cập theo vai trò (Admin, Teacher, Student). Student chỉ xem được bài thi được phép tham gia và kết quả của bản thân. Teacher chỉ xem được kết quả thuộc các bài thi mình phụ trách. Chỉ Admin được quản lý tài khoản.

•	NFR03 – Bảo vệ mật khẩu: Mật khẩu phải được lưu dưới dạng giá trị băm bằng thuật toán chuyên dụng và an toàn dành cho mật khẩu; không được lưu dưới dạng văn bản thuần.

•	NFR04 – Bảo vệ đáp án: Đáp án đúng không được gửi xuống phía Student trong lúc làm bài. Việc chấm điểm chỉ thực hiện ở phía máy chủ.

•	NFR05 – Chống tấn công phổ biến: Hệ thống phải tránh các lỗi bảo mật như SQL Injection và XSS. Dữ liệu người dùng nhập vào phải được kiểm tra và xử lý trước khi lưu hoặc hiển thị.

•	NFR06 – Tính toàn vẹn bài làm: Sau khi hệ thống xác nhận nộp bài thành công, bài làm được khóa và không thể sửa hoặc nộp lại. Mỗi Student chỉ có một bài nộp hợp lệ cho mỗi lượt thi.

•	NFR07 – Chống đăng nhập tự động: Hệ thống hạn chế dò mật khẩu bằng phần mềm tự động, ví dụ khóa tạm thời tài khoản sau nhiều lần đăng nhập sai liên tiếp.

## Hiệu năng
•	NFR08 – Khả năng đáp ứng đồng thời: Hệ thống đáp ứng tối thiểu 500 sinh viên truy cập và làm bài cùng lúc mà không giảm chất lượng đáng kể.

•	NFR09 – Thời gian phản hồi: Các thao tác thông thường (đăng nhập, xem danh sách bài thi, chuyển câu hỏi, lưu câu trả lời) phản hồi trong vòng 3 giây.

•	NFR10 – Thời gian chấm điểm: Sau khi nộp bài, kết quả được chấm và lưu trong vòng 5 giây.

•	NFR11 – Dung lượng lưu trữ: Hệ thống lưu trữ được tối thiểu 10.000 tài khoản, 50.000 câu hỏi và 500.000 bài nộp.

•	NFR12 – Phân trang: Các danh sách dài (tài khoản, câu hỏi, bài thi, kết quả) phải được phân trang để đảm bảo hiệu suất.

## Độ tin cậy
•	NFR13 – Tính sẵn sàng: Hệ thống hoạt động ổn định, đạt độ sẵn sàng tối thiểu 99% trong thời gian diễn ra các kỳ thi.

•	NFR14 – Không mất dữ liệu: Câu trả lời của Student được ghi nhận trong quá trình làm bài. Nếu mất kết nối hoặc tải lại trang, Student có thể tiếp tục làm bài mà không mất các câu đã chọn.

•	NFR15 – Nộp bài an toàn: Khi nộp bài, hệ thống phải xác nhận kết quả (thành công hoặc thất bại). Nếu lần nộp trước thất bại hoặc chưa được hệ thống ghi nhận, Student được thông báo và có thể thử nộp lại. Hệ thống phải kiểm tra trạng thái nộp để tránh ghi nhận trùng bài hoặc làm mất bài.

•	NFR16 – Sao lưu và phục hồi: Dữ liệu hệ thống được sao lưu định kỳ (ví dụ mỗi ngày) và có thể phục hồi khi xảy ra sự cố.

•	NFR17 – Nhất quán dữ liệu: Việc chấm điểm và lưu kết quả phải đảm bảo kết quả lưu đúng với bài đã nộp.

## Tính dễ sử dụng
•	NFR18 – Giao diện thân thiện: Giao diện trực quan, dễ hiểu, người dùng thực hiện các thao tác chính mà không cần hướng dẫn phức tạp.

•	NFR19 – Hiển thị tương thích: Giao diện tự điều chỉnh theo kích thước màn hình (responsive) và hoạt động trên các trình duyệt web phổ biến.

•	NFR20 – Giao diện làm bài: Hiển thị rõ số thứ tự câu hỏi, câu đã trả lời và chưa trả lời, và (nếu có giới hạn) thời gian còn lại.

•	NFR21 – Thông báo rõ ràng: Hệ thống đưa ra thông báo dễ hiểu khi có lỗi (sai mật khẩu, thiếu thông tin, nộp bài thất bại) và khi thao tác thành công. Hệ thống yêu cầu xác nhận trước các thao tác quan trọng như xóa dữ liệu hoặc nộp bài.

•	NFR22 – Ngôn ngữ: Giao diện sử dụng tiếng Việt.

## Khả năng bảo trì
•	NFR23 – Thiết kế module: Hệ thống được thiết kế theo từng module (tài khoản, câu hỏi, bài thi, làm bài, chấm điểm, kết quả) để dễ sửa lỗi và mở rộng.

•	NFR24 – Khả năng mở rộng: Hệ thống dễ bổ sung các chức năng trong tương lai (thêm dạng câu hỏi mới, thống kê, báo cáo) mà không ảnh hưởng nhiều đến phần đã có.

•	NFR25 – Ghi nhật ký: Hệ thống ghi lại các sự kiện quan trọng (đăng nhập, thay đổi tài khoản, nộp bài, lỗi hệ thống) để hỗ trợ kiểm tra và xử lý sự cố.

•	NFR26 – Tài liệu: Mã nguồn và tài liệu thiết kế được ghi chú rõ ràng để thành viên khác có thể tiếp tục phát triển và bảo trì.

## Yêu cầu phát triển
•	NFR27 – Nền tảng triển khai: Hệ thống được phát triển và vận hành trên nền tảng Web.

•	NFR28 – Công nghệ phát triển: Giao diện sử dụng HTML5, CSS3 và JavaScript. Công nghệ phía máy chủ và hệ quản trị cơ sở dữ liệu quan hệ được lựa chọn thống nhất theo phương án triển khai của nhóm.

•	NFR29 – Tính nhất quán: Thiết kế hệ thống phải bảo đảm sự nhất quán giữa các chức năng, dữ liệu lưu trữ, phân quyền người dùng và các yêu cầu đã được xác định trong tài liệu Functional Requirements.

## Các điểm cần thống nhất
