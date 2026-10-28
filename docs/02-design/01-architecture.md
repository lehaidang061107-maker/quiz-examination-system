# Thiết kế kiến trúc

Trạng thái: Đã chốt bộ công nghệ và hướng tổ chức; thiết kế chi tiết sẽ hoàn thiện ở giai đoạn 2.

## Công nghệ được chọn và lý do

Theo [TECH_STACK.md](../../TECH_STACK.md), nhóm dùng Python + Django, Django Templates + Bootstrap, JavaScript cơ bản và SQLite cho bản đầu / demo nhỏ. Đăng nhập bằng Django Authentication dùng session, truy cập dữ liệu bằng Django ORM và kiểm thử bằng Django TestCase / test client.

Lý do lựa chọn: tập trung giao diện và backend trong một dự án; tận dụng các thành phần tài khoản, form, ORM và quản trị của Django; thuận tiện chia nhỏ chức năng để triển khai và rà soát.

## Kiến trúc / mẫu thiết kế đã học được áp dụng

Định hướng một ứng dụng theo cấu trúc Model–View–Template (MVT) của Django. Phần đối chiếu với kiến trúc / mẫu thiết kế đã học và sơ đồ kiến trúc sẽ được bổ sung ở giai đoạn 2.

## Thành phần và trách nhiệm

## Giao tiếp giữa các thành phần

## Cấu trúc mã nguồn

## Các quyết định và vấn đề còn mở

Phiên bản công nghệ, cấu trúc app chi tiết, môi trường triển khai và tiêu chí thi đồng thời cần tiếp tục thống nhất; theo dõi tại [TECH_STACK.md](../../TECH_STACK.md).
