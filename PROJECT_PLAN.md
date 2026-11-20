# Project Plan

<!-- toc -->

**Mục lục**

- [Phase 1 — Requirements Analysis (M1)](#phase-1--requirements-analysis-m1)
- [Phase 2 — Design (M2)](#phase-2--design-m2)
- [Phase 3 — Implementation (M3)](#phase-3--implementation-m3)
- [Phase 4 — Testing (M4)](#phase-4--testing-m4)
- [Tracking & Change Management](#tracking--change-management)
- [Final Deliverables](#final-deliverables)

<!-- /toc -->

Dự án làm theo 4 giai đoạn của môn học ([GUIDELINES.md](GUIDELINES.md)). Xong giai đoạn trước
(đạt mốc M1–M4) mới chuyển sang giai đoạn sau. Mỗi việc có một người làm chính và một người khác
rà soát. Công nghệ và cách viết code xem [TECH_STACK.md](TECH_STACK.md); quy trình Git/Jira xem
[MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md). Tài liệu đặc tả, sơ đồ nằm trong [`docs/`](docs/).

## Phase 1 — Requirements Analysis (M1)

| Phần việc | Nội dung | Nộp |
| --- | --- | --- |
| Tổng quan + yêu cầu chức năng (FR) | Mục tiêu, phạm vi, 3 vai trò Admin/Teacher/Student; mỗi chức năng có mã `FR-xx`, ai làm, điều kiện, kết quả mong đợi | Word |
| Yêu cầu chất lượng (NFR) + DFD | Bảo mật, hiệu năng, độ tin cậy, dễ dùng, dễ bảo trì; mã `NFR-xx` kèm cách đo. DFD đúng mức giảng viên yêu cầu | Word, `.drawio` + ảnh |
| Use Case + giao diện sơ bộ | Sơ đồ và danh sách Use Case (`UC-xx`); danh sách màn hình, wireframe gắn với Use Case | `.drawio` + ảnh, Word |
| Đặc tả Use Case | Mỗi Use Case: tác nhân, tiền điều kiện, luồng chính, luồng lỗi, kết quả; ưu tiên đăng nhập, tạo đề, làm bài, nộp bài, chấm điểm | Word |
| Class Diagram + dữ liệu sơ bộ + tổng hợp | Lớp, thuộc tính, quan hệ; bảng và khóa dự kiến; đối chiếu mọi phần cho khớp, ghép thành một file | `.drawio` + ảnh, Word tổng hợp |

Cần làm rõ trong giai đoạn này: ai được tạo câu hỏi/đề/thi/xem kết quả; loại câu hỏi và cách chấm;
giới hạn thời gian, số lần làm, tự lưu, tự nộp; khi nào và ai được xem kết quả.

**M1 đạt khi:** phạm vi và vai trò đã thống nhất; FR/NFR có mã và cách nghiệm thu; đủ DFD, Use Case,
Class Diagram và khớp với yêu cầu; có file nguồn sơ đồ; cả nhóm đã rà soát file tổng hợp; có danh sách việc
ưu tiên.

## Phase 2 — Design (M2)

- Thiết kế màn hình và luồng thao tác theo Use Case, gồm cả trạng thái trống, nhập sai, đang tải, lỗi.
- Chọn kiến trúc đã học, giải thích lý do và vai trò từng phần.
- Thiết kế bảng dữ liệu: cột, kiểu, khóa, ràng buộc, quan hệ.
- Chốt công nghệ, phiên bản, cấu trúc code; cập nhật Class Diagram; liên kết được yêu cầu → màn hình → dữ liệu.

**M2 đạt khi:** tài liệu đủ 7 phần theo guidelines; mọi chức năng có giao diện; kiến trúc, dữ liệu,
công nghệ đã rõ; việc triển khai đã chia thành task có tiêu chí nghiệm thu.

## Phase 3 — Implementation (M3)

Thứ tự: dựng khung website → chuyển database sang Django → làm chức năng
(tài khoản → câu hỏi, đề thi → làm bài → chấm điểm, kết quả).

- Làm trọn từng chức năng: giao diện, xử lý, lưu dữ liệu; gắn với mã FR/Use Case.
- Người làm viết test cho phần của mình; chấm điểm, nộp bài, hết giờ phải test sớm.
- Mỗi thay đổi đi qua Pull Request có người review; tích hợp thường xuyên; sửa tài liệu cùng lúc với code.

**M3 đạt khi:** đủ chức năng trong phạm vi và đã ghép chạy chung; code theo đúng kiến trúc; test đã chạy,
lỗi được ghi lại; người khác cài và chạy được theo hướng dẫn với dữ liệu mẫu; lỗi còn mở có người phụ trách.

## Phase 4 — Testing (M4)

- Viết ca kiểm thử từ FR, NFR, Use Case; có bảng nối yêu cầu ↔ ca kiểm thử.
- Chạy kiểm thử chức năng, tích hợp, luồng người dùng, NFR và unit test; ghi Đạt / Không đạt / Bị chặn kèm bằng chứng.
- **Ca kiểm thử** ghi: mã, yêu cầu liên quan, điều kiện trước, dữ liệu, các bước, kết quả mong đợi và thực tế, trạng thái.
- **Lỗi** ghi: các bước gặp lại lỗi, mong đợi và thực tế, bằng chứng, mức độ, người sửa; theo luồng `Open → In Progress → Ready for Retest → Closed`.
- Lỗi đã sửa phải kiểm tra lại, kèm các chức năng liên quan (kiểm thử hồi quy).

**M4 đạt khi:** mỗi FR/NFR có kiểm thử và kết quả; không còn lỗi chặn luồng chính hay làm sai điểm;
hạn chế còn lại được ghi rõ; tài liệu, code, dữ liệu mẫu, hướng dẫn và demo khớp nhau.

## Tracking & Change Management

- Cập nhật Jira khi có tiến triển hoặc vướng mắc; cuối mỗi giai đoạn dò lại checklist mốc.
- Muốn đổi yêu cầu: ghi lý do và ảnh hưởng (thiết kế, code, kiểm thử, khối lượng), nhóm đồng ý rồi mới làm.
- Thiếu thời gian: ưu tiên chức năng cốt lõi, vẫn nộp đủ sản phẩm bắt buộc.

| Rủi ro | Cách xử lý |
| --- | --- |
| Phạm vi lớn hoặc đổi liên tục | Chốt ưu tiên từ M1, đánh giá từng thay đổi |
| Phần phụ thuộc chưa xong | Dùng dữ liệu mẫu, ghép code sớm |
| Mất thời gian cài môi trường | Có hướng dẫn chạy, thử trên máy người khác |
| Dồn kiểm thử về cuối | Viết test ngay khi làm chức năng |
| Tài liệu lệch với code | Sửa tài liệu trong cùng PR với code |

## Final Deliverables

- Tài liệu đặc tả và thiết kế đủ 7 phần; DFD, Use Case, Class Diagram, Data Model kèm file gốc.
- Thiết kế giao diện và mô tả kiến trúc.
- Mã nguồn trên GitHub, hướng dẫn cài đặt và chạy, dữ liệu mẫu, kịch bản demo.
- Ca kiểm thử, kết quả unit test và kiểm thử, danh sách lỗi kèm tình trạng.
