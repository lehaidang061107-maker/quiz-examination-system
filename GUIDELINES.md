# Guidelines cho dự án nhóm

Yêu cầu thực hiện dự án theo hướng dẫn môn Công nghệ phần mềm.

## 1. Yêu cầu chung

Theo guidelines của môn học, nhóm cần cùng phân tích, thiết kế, triển khai và kiểm thử một ứng dụng phần mềm qua **bốn giai đoạn** dưới đây.

### Giai đoạn 1 — Phân tích và đặc tả yêu cầu

- Mô tả yêu cầu chức năng (Functional Requirements) bằng ngôn ngữ tự nhiên.
- Mô tả yêu cầu phi chức năng (Non-Functional Requirements) bằng ngôn ngữ tự nhiên.
- Vẽ sơ đồ luồng dữ liệu (Data Flow Diagram — DFD).
- Vẽ sơ đồ ca sử dụng (Use Case Diagram).
- Vẽ sơ đồ lớp (Class Diagram).

**Kết quả cần có:** tài liệu yêu cầu và bộ sơ đồ phản ánh phạm vi hệ thống đã thống nhất.

### Giai đoạn 2 — Thiết kế

- **Thiết kế giao diện (GUI):** thiết kế giao diện đồ họa và các luồng tương tác của người dùng.
- **Thiết kế kiến trúc phần mềm:** áp dụng kiến trúc hoặc mẫu thiết kế phù hợp đã học trong môn.
- **Thiết kế cơ sở dữ liệu:** xác định bảng, thuộc tính, khóa chính, khóa ngoại và các quan hệ khi có áp dụng.

**Kết quả cần có:** thiết kế giao diện, mô tả kiến trúc và mô hình dữ liệu làm cơ sở triển khai.

### Giai đoạn 3 — Triển khai

- Sử dụng ngôn ngữ lập trình, ví dụ Python, C++ hoặc Java.
- Áp dụng kiến trúc phần mềm phù hợp đã học trong môn.
- Tổ chức mã nguồn rõ ràng và sử dụng hệ thống quản lý phiên bản.

**Kết quả cần có:** ứng dụng triển khai theo yêu cầu, mã nguồn được quản lý phiên bản và hướng dẫn chạy.

### Giai đoạn 4 — Kiểm thử

- Xây dựng và thực thi các ca kiểm thử (test case).
- Thực hiện kiểm thử đơn vị (unit testing).
- Gỡ lỗi (debugging), ghi nhận và quản lý các lỗi đã phát hiện.

**Kết quả cần có:** bộ test case, kết quả kiểm thử, unit test và danh sách lỗi kèm tình trạng xử lý.

## 2. Cấu trúc tài liệu đặc tả yêu cầu và thiết kế

Tài liệu cần trình bày đủ **bảy phần theo thứ tự** trong guidelines:

| STT | Phần tài liệu | Nội dung cần trình bày |
| --- | --- | --- |
| 1 | Functional Requirements | Các chức năng, hành vi và quy tắc nghiệp vụ của hệ thống bằng ngôn ngữ tự nhiên. |
| 2 | Non-Functional Requirements | Các yêu cầu chất lượng và ràng buộc của hệ thống bằng ngôn ngữ tự nhiên. |
| 3 | Data Flow Diagram | Luồng dữ liệu giữa tác nhân, tiến trình và kho dữ liệu. |
| 4 | Use Case Diagram | Tác nhân, các ca sử dụng và quan hệ giữa chúng. |
| 5 | Class Diagram | Các lớp, thuộc tính, phương thức và quan hệ giữa các lớp. |
| 6 | Data Model | Mô hình dữ liệu; bảng, thuộc tính, khóa và quan hệ khi sử dụng cơ sở dữ liệu. |
| 7 | Interface Design Description | Mô tả màn hình, thành phần giao diện và luồng tương tác. |

Nhóm nên trình bày mô tả kiến trúc trong phần thiết kế của cùng tài liệu hoặc trong phụ lục/tài liệu liên kết, để đáp ứng yêu cầu thiết kế kiến trúc ở giai đoạn 2.

## 3. Công cụ được gợi ý trong guidelines

| Mục đích | Công cụ gợi ý |
| --- | --- |
| Quản lý tài liệu, mã nguồn và làm việc nhóm | GitHub / GitLab |
| Vẽ DFD, Use Case, Class Diagram và Database Schema | [diagrams.net](https://app.diagrams.net/) |
| Thiết kế giao diện | Figma |
| Môi trường lập trình | VS Code / Visual Studio / PyCharm / Eclipse / … |
| Soạn test case | Excel |
| Kiểm thử đơn vị | pytest (Python) / Google Test (C++) / JUnit (Java) |
| Theo dõi lỗi | Jira / Bugzilla / Mantis Bug Tracker |
| Đóng gói và triển khai | Docker |

Guidelines cho phép sử dụng công cụ khác. Danh sách trên là gợi ý, không phải yêu cầu bắt buộc sử dụng tất cả công cụ.

Kế hoạch áp dụng cho nhóm 5 người được trình bày trong [PROJECT_PLAN.md](PROJECT_PLAN.md).
