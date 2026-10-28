# Công nghệ và công cụ đã thống nhất

Tài liệu này ghi lại lựa chọn công nghệ của nhóm 5 người cho Quiz Examination System. Đây là quyết định để triển khai; ứng dụng hiện chưa được xây dựng.

## 1. Bộ công nghệ đã chốt

| Hạng mục | Lựa chọn | Sử dụng trong dự án |
| --- | --- | --- |
| Loại ứng dụng | Web | Người dùng truy cập bằng trình duyệt. |
| Ngôn ngữ backend | Python | Viết xử lý nghiệp vụ. |
| Framework | Django | Xử lý request, dữ liệu, form và các luồng chức năng. |
| Giao diện | Django Templates + HTML/CSS + Bootstrap | Dựng các trang giao diện trong cùng ứng dụng Django. |
| Tương tác trên trình duyệt | JavaScript cơ bản | Hỗ trợ tương tác như đồng hồ đếm ngược và xác nhận nộp bài khi chức năng đó thuộc phạm vi. |
| Đăng nhập | Django Authentication, dùng session | Tận dụng cơ chế tài khoản, đăng nhập và đăng xuất của Django. |
| Phân quyền | Django Groups / Permissions và kiểm tra quyền phía server | Thiết lập quyền Admin, Teacher, Student theo yêu cầu đã thống nhất. |
| Truy cập dữ liệu | Django ORM và migrations | Định nghĩa model, truy vấn và quản lý thay đổi cấu trúc dữ liệu. |
| Cơ sở dữ liệu bản đầu | SQLite | Phát triển cục bộ và demo nhỏ. |
| Kiểm thử tự động | Django TestCase và test client | Kiểm tra nghiệp vụ, truy cập dữ liệu và các luồng request / response. |

**Cách tổ chức đã chọn:** một ứng dụng Django, giao diện và backend trong cùng dự án. Thiết kế chi tiết sẽ dựa trên cấu trúc Model–View–Template (MVT) của Django và được mô tả ở giai đoạn 2.

Các phần dự kiến để chia công việc:

| Phần | Trách nhiệm dự kiến |
| --- | --- |
| `accounts` | Tài khoản và phân quyền. |
| `questions` | Ngân hàng câu hỏi và đáp án. |
| `exams` | Tạo và quản lý đề thi. |
| `submissions` | Làm bài, nộp bài, chấm điểm và kết quả. |

Đây là định hướng chia module; tên app, model và giao tiếp cụ thể sẽ được hoàn thiện trong [thiết kế kiến trúc](docs/02-design/01-architecture.md).

## 2. Công cụ làm việc theo tài liệu nhóm hiện có

| Công việc | Công cụ / định dạng |
| --- | --- |
| Quản lý phiên bản | Git; làm việc qua branch và Pull Request theo [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md). |
| Theo dõi công việc và lỗi | Jira. |
| Vẽ DFD, Use Case, Class Diagram và mô hình dữ liệu | diagrams.net / draw.io; giữ file nguồn `.drawio` và xuất ảnh / PDF. |
| Soạn và tổng hợp báo cáo | Microsoft Word (`.docx`); xuất PDF khi cần bàn giao. |
| Lưu nội dung làm việc trong repo | Markdown (`.md`). |
| Danh sách test case và lỗi | Mẫu CSV trong `docs/04-testing/`, có thể mở bằng Excel. |

Nơi lưu từng phần và trách nhiệm TV1–TV5 nằm trong [hướng dẫn tổ chức tài liệu](docs/README.md) và [kế hoạch dự án](PROJECT_PLAN.md).

## 3. Những điểm chưa chốt

- **Phiên bản:** chọn bộ Python, Django, Bootstrap và các thư viện tương thích khi dựng ứng dụng; ghi cố định phiên bản để các máy dùng thống nhất.
- **Phạm vi nghiệp vụ:** chức năng, quy tắc thi, cách tính điểm, số lần thi và thời điểm công bố kết quả vẫn cần hoàn thiện trong giai đoạn 1. Chốt công nghệ không thay thế việc chốt yêu cầu.
- **Cơ sở dữ liệu khi triển khai thi đồng thời:** SQLite được chọn cho bản đầu / demo nhỏ. Nếu mục tiêu có nhiều thí sinh thi đồng thời, nhóm sẽ đánh giá PostgreSQL và chốt môi trường kiểm thử tương ứng trước khi triển khai phần đó.
- **Bàn giao / triển khai:** chưa chốt hosting, tên miền hoặc Docker.
- **Thiết kế giao diện:** chưa chốt công cụ wireframe / mockup; có thể chọn khi TV3 bắt đầu phần này.
- **Kiến trúc trong báo cáo môn học:** đối chiếu cách tổ chức Django với kiến trúc / mẫu thiết kế đã học, hoàn thiện lý do lựa chọn ở giai đoạn 2.

## 4. Cách triển khai với AI hỗ trợ

- Làm theo từng chức năng và FR / Use Case đã chốt, hoàn thành một luồng có giao diện, xử lý và lưu dữ liệu trước khi chuyển việc tiếp theo.
- Nêu rõ Django Templates, Bootstrap, model liên quan và tiêu chí nghiệm thu trong yêu cầu gửi AI.
- Người nhận task đọc lại mã nguồn, chạy thử, viết / chạy kiểm thử phù hợp và gửi Pull Request để thành viên khác rà soát.
- Với phân quyền, chấm điểm, nộp bài và giới hạn giờ, kiểm tra kết quả ở phía server; giao diện chỉ hỗ trợ thao tác và hiển thị.
