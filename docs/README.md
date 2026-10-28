# Hướng dẫn tổ chức tài liệu

Các file phân tích, thiết kế và kiểm thử chủ yếu là khung để điền nội dung. Bộ công nghệ đã được thống nhất trong [TECH_STACK.md](../TECH_STACK.md); ứng dụng chưa được triển khai.

## Nơi làm việc của từng thành viên ở giai đoạn 1

| Thành viên | File nội dung | Sơ đồ / giao diện |
| --- | --- | --- |
| TV1 | [Tổng quan](01-analysis/01-overview.md), [Functional Requirements](01-analysis/02-functional-requirements.md) | — |
| TV2 | [Non-Functional Requirements](01-analysis/03-non-functional-requirements.md) | `diagrams/dfd/` |
| TV3 | Danh sách Use Case trong [đặc tả Use Case](01-analysis/04-use-case-specifications.md), [Interface Design Description](02-design/03-interface-design.md) | `diagrams/use-case/`, `02-design/ui/` |
| TV4 | Phần đặc tả chi tiết trong [đặc tả Use Case](01-analysis/04-use-case-specifications.md) | Đối chiếu với sơ đồ của TV3. |
| TV5 | [Data Model](02-design/02-data-model.md), bản Word tổng hợp trong `deliverables/stage-1/` | `diagrams/class/`, `diagrams/data-model/` |

TV3 phụ trách danh sách Use Case, TV4 phụ trách đặc tả chi tiết trong cùng file; thống nhất trước khi chỉnh sửa đồng thời. Mô tả lớp nằm cùng file nguồn Class Diagram và được đưa vào bản Word tổng hợp.

Giao diện và mô hình dữ liệu sơ bộ được lưu ngay trong `02-design/`, sau đó tiếp tục hoàn thiện ở giai đoạn 2 để tránh tạo nhiều bản nội dung khác nhau. [Kiến trúc](02-design/01-architecture.md) được thực hiện ở giai đoạn 2.

## Lưu nguồn và bản xuất

- `diagrams/<loai-so-do>/source/`: file nguồn `.drawio` hoặc định dạng chỉnh sửa thực tế.
- `diagrams/<loai-so-do>/exports/`: ảnh hoặc PDF xuất từ sơ đồ tương ứng.
- `02-design/ui/source/`: nguồn wireframe / mockup; nếu dùng Figma, ghi liên kết trong Interface Design Description.
- `02-design/ui/exports/`: ảnh hoặc PDF giao diện.
- `deliverables/stage-1/`: các file Word thành viên bàn giao và bản tổng hợp giai đoạn 1.
- `deliverables/final/`: bản Word / PDF hoàn chỉnh cuối dự án.

Tên file nên dùng chữ thường, không dấu, phân tách bằng dấu gạch ngang, ví dụ `tv1-functional-requirements.docx`, `use-case-overview.drawio`, `stage-1-report.docx`. File nguồn và bản xuất cùng sơ đồ nên có cùng tên gốc.

Chỉ thêm file `.docx`, `.drawio`, ảnh hoặc PDF khi đã tạo bằng công cụ tương ứng; không dùng file rỗng mang các đuôi này. File `.gitkeep` chỉ giúp Git lưu thư mục đang trống, có thể xóa khi thư mục đã có nội dung.

## Thứ tự ghép tài liệu

Đặt phần giới thiệu ở đầu, sau đó ghép đủ bảy phần theo [GUIDELINES.md](../GUIDELINES.md):

1. Functional Requirements.
2. Non-Functional Requirements.
3. Data Flow Diagram.
4. Use Case Diagram, kèm đặc tả Use Case chi tiết.
5. Class Diagram.
6. Data Model.
7. Interface Design Description.

Mô tả kiến trúc được bổ sung ở phần thiết kế hoặc phụ lục liên quan theo guidelines.

## Triển khai và kiểm thử

- [Hướng dẫn thiết lập và chạy](03-implementation/setup.md): cập nhật theo bộ công nghệ đã chốt khi có ứng dụng chạy được.
- [Kế hoạch kiểm thử](04-testing/test-plan.md), [test case](04-testing/test-cases.csv), [danh sách lỗi](04-testing/defect-log.csv), [báo cáo kiểm thử](04-testing/test-report.md).
- `04-testing/results/`: kết quả và bằng chứng kiểm thử.
- `../src/`: mã nguồn ứng dụng; tổ chức các thành phần sau khi chốt kiến trúc.
- `../tests/unit/`, `../tests/integration/`, `../tests/system/`: mã kiểm thử đơn vị, tích hợp và toàn hệ thống.
- `../database/schema/`, `../database/migrations/`, `../database/seeds/`: định nghĩa cấu trúc dữ liệu, thay đổi cấu trúc và dữ liệu mẫu khi lựa chọn lưu trữ phù hợp.

Chi tiết công việc và tiêu chí hoàn thành nằm trong [PROJECT_PLAN.md](../PROJECT_PLAN.md).
