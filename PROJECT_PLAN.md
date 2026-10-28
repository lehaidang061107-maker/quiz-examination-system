# Kế hoạch thực hiện Quiz Examination System

Kế hoạch này dành cho **nhóm 5 người**, triển khai bốn giai đoạn theo [GUIDELINES.md](GUIDELINES.md). Tiến độ được theo dõi theo công việc, sản phẩm bàn giao và tiêu chí hoàn thành của từng giai đoạn.

## 1. Thông tin cần chốt khi khởi động

| Hạng mục | Trạng thái / thông tin |
| --- | --- |
| Số lượng thành viên | 5 người |
| Tên thành viên | Điền tên tương ứng TV1–TV5 ở mục 3; phân công giai đoạn 1 theo nội dung nhóm đã soạn |
| Phạm vi chức năng và vai trò người dùng | Chốt trong giai đoạn 1 |
| Ngôn ngữ, framework, giao diện | Đã chốt Python + Django + Django Templates + Bootstrap; xem [TECH_STACK.md](TECH_STACK.md) |
| Cơ sở dữ liệu và kiểm thử | SQLite cho bản đầu / demo nhỏ; Django ORM, Django TestCase và test client |
| Phiên bản công nghệ và triển khai | Thống nhất khi dựng ứng dụng; môi trường thi đồng thời cần đánh giá database riêng |
| Kiến trúc / mẫu thiết kế đã học sẽ áp dụng | Đã chọn một ứng dụng Django theo MVT; hoàn thiện thiết kế và đối chiếu kiến thức môn học ở giai đoạn 2 |
| Ngưỡng chất lượng và môi trường kiểm thử | Xác định từ yêu cầu phi chức năng, chốt trước triển khai |

## 2. Lộ trình tổng quan

| Giai đoạn | Trọng tâm | Mốc bàn giao |
| --- | --- | --- |
| 1. Phân tích và đặc tả yêu cầu | Chốt phạm vi, yêu cầu và các sơ đồ phân tích | M1: yêu cầu và sơ đồ được nhóm rà soát, thống nhất |
| 2. Thiết kế | Giao diện, kiến trúc, cơ sở dữ liệu | M2: bộ thiết kế đủ rõ để triển khai |
| 3. Triển khai | Xây dựng và tích hợp chức năng | M3: bản chạy được của toàn bộ phạm vi đã chốt |
| 4. Kiểm thử và hoàn thiện | Kiểm thử, sửa lỗi, hoàn tất bàn giao | M4: bản bàn giao kèm báo cáo kiểm thử |

Unit test và kiểm tra chức năng được thực hiện ngay khi có mã nguồn ở giai đoạn 3. Giai đoạn 4 tập trung kiểm thử toàn hệ thống, kiểm thử lại lỗi đã sửa và hoàn tất bằng chứng kiểm thử.

## 3. Vai trò và cách phân công

Phân công **giai đoạn 1** dưới đây dựa trên nội dung nhóm đã soạn, dùng ký hiệu TV1–TV5 để thay bằng tên thực tế. Mỗi task cần có một người chịu trách nhiệm chính và một người khác rà soát.

| Thành viên | Phụ trách giai đoạn 1 | Phối hợp chính |
| --- | --- | --- |
| TV1 — Chưa điền tên | Tổng quan và Functional Requirements | Cung cấp phạm vi, tác nhân và FR làm cơ sở cho các phần còn lại. |
| TV2 — Chưa điền tên | Non-Functional Requirements và DFD | Đối chiếu yêu cầu với TV1, luồng xử lý với TV4 và dữ liệu với TV5. |
| TV3 — Chưa điền tên | Use Case Diagram và Interface Design Description sơ bộ | Thống nhất use case với TV4, màn hình và quyền thao tác với TV1. |
| TV4 — Chưa điền tên | Đặc tả Use Case chi tiết | Đối chiếu sơ đồ với TV3, nghiệp vụ với TV1 và dữ liệu với TV5. |
| TV5 — Chưa điền tên | Class Diagram, mô hình dữ liệu sơ bộ và tổng hợp | Chủ trì kiểm tra tính nhất quán và ghép tài liệu sau khi từng người đã tự rà soát. |

Phân công này không cố định vai trò cho toàn dự án. Các vai trò thiết kế, lập trình, kiểm thử và người điều phối / PM ở các giai đoạn tiếp theo sẽ được nhóm thống nhất riêng. Khi triển khai, cả 5 thành viên cùng nhận module hoặc chức năng phù hợp; người triển khai chịu trách nhiệm unit test và sửa lỗi phần mình, còn kiểm thử chéo do thành viên khác thực hiện.

Thực hiện luồng task, branch và Pull Request theo [MEMBER_WORKFLOW.md](MEMBER_WORKFLOW.md). Chia các đầu việc dưới đây thành Jira task nhỏ, có người phụ trách, người rà soát, phụ thuộc và tiêu chí nghiệm thu cụ thể.

File khởi đầu và vị trí lưu sản phẩm của từng thành viên được liệt kê trong [hướng dẫn tổ chức tài liệu](docs/README.md).

## 4. Giai đoạn 1 — Phân tích và đặc tả yêu cầu

**Tên giai đoạn:** Analysis and Requirements Specification.

**Đề tài:** Quiz Examination System — Hệ thống thi trắc nghiệm.

**Điều kiện bắt đầu:** nhóm đã đọc guidelines và thống nhất cách phối hợp.

Trong giai đoạn này, mô tả giao diện và mô hình dữ liệu được chuẩn bị ở mức sơ bộ để hỗ trợ phân tích. Thiết kế GUI, cơ sở dữ liệu và kiến trúc sẽ được hoàn thiện ở giai đoạn 2 theo guidelines.

### 4.1. Thành viên 1 — Tổng quan và Functional Requirements

- Mô tả hệ thống Quiz Examination System, bài toán cần giải quyết và mục tiêu của hệ thống.
- Xác định phạm vi, phần không thuộc phạm vi và trách nhiệm của ba tác nhân **Admin, Teacher, Student**.
- Liệt kê yêu cầu chức năng bằng ngôn ngữ tự nhiên, gán mã `FR-01`, `FR-02`, … để đối chiếu với sơ đồ và kiểm thử sau này.
- Với mỗi chức năng, nêu tác nhân thực hiện, điều kiện thực hiện, hành vi mong đợi và kết quả đầu ra / tiêu chí nghiệm thu.
- Thống nhất quy tắc nghiệp vụ với TV4, đặc biệt cách tạo đề, làm bài, nộp bài và tính điểm.

**Bàn giao:** file Word (`.docx`) gồm phần giới thiệu, mục tiêu, phạm vi, tác nhân và Functional Requirements.

### 4.2. Thành viên 2 — Non-Functional Requirements và DFD

- Mô tả yêu cầu về bảo mật, hiệu năng, độ tin cậy, tính dễ sử dụng và khả năng bảo trì bằng ngôn ngữ tự nhiên.
- Gán mã `NFR-01`, `NFR-02`, …; nêu điều kiện đánh giá, cách kiểm chứng và ngưỡng đo được khi phù hợp. Các ngưỡng cần được nhóm thống nhất.
- Xác nhận mức DFD cần vẽ theo yêu cầu giảng viên; ghi lại để cả nhóm dùng thống nhất.
- Xác định tác nhân ngoài, tiến trình xử lý, kho dữ liệu và luồng dữ liệu; giữ luồng dữ liệu nhất quán giữa các mức nếu có phân rã.
- Thể hiện hợp lý dữ liệu đăng nhập, câu trả lời, bài nộp và kết quả theo phạm vi đã chốt.
- Đối chiếu DFD với FR của TV1, luồng use case của TV4 và mô hình dữ liệu của TV5.

**Bàn giao:** file Word phần NFR, file nguồn `.drawio` và bản xuất ảnh / PDF DFD.

### 4.3. Thành viên 3 — Use Case Diagram và Interface Design Description sơ bộ

- Xác định chức năng của từng Actor: Admin, Teacher, Student; đối chiếu với phạm vi và FR của TV1.
- Vẽ Use Case Diagram tổng quan, thể hiện ranh giới hệ thống và quan hệ giữa Actor với các Use Case.
- Rà soát các chức năng đăng nhập, quản lý câu hỏi, quản lý đề thi, làm bài, nộp bài và xem kết quả theo phạm vi đã thống nhất.
- Kiểm tra quan hệ giữa các Use Case; chỉ dùng `include` hoặc `extend` khi phù hợp.
- Lập danh sách Use Case, gán mã `UC-01`, `UC-02`, … và thống nhất mã với TV4.
- Chuẩn bị danh sách màn hình và wireframe sơ bộ cho các luồng chính; mô tả mục đích màn hình, Actor sử dụng, trường nhập, thao tác và kết quả hiển thị.
- Liên kết màn hình với Use Case tương ứng; chuyển bản sơ bộ sang giai đoạn 2 để hoàn thiện thiết kế giao diện.

**Bàn giao:** file `.drawio` và ảnh / PDF Use Case Diagram; danh sách Use Case; file Word phần Interface Design Description sơ bộ và wireframe kèm nguồn chỉnh sửa.

### 4.4. Thành viên 4 — Đặc tả Use Case chi tiết

- Viết đặc tả cho các Use Case quan trọng, dùng cùng mã và tên với sơ đồ của TV3.
- Mỗi Use Case có: tên, tác nhân, mục tiêu, tiền điều kiện, luồng chính, luồng thay thế / ngoại lệ và hậu điều kiện.
- Ưu tiên đăng nhập, tạo đề thi, bắt đầu làm bài, nộp bài, chấm điểm và xem kết quả theo phạm vi đã chốt. Làm rõ chấm điểm tự động thuộc luồng nào nếu hệ thống thực hiện tự động.
- Mô tả các tình huống như thông tin đăng nhập sai, chưa đủ điều kiện thi, hết giờ hoặc nộp bài không hợp lệ nếu có trong phạm vi.
- Đối chiếu từng đặc tả với FR của TV1, Use Case Diagram của TV3 và luồng dữ liệu của TV2.

**Bàn giao:** file Word phần đặc tả Use Case chi tiết, có mã FR liên quan cho từng Use Case.

### 4.5. Thành viên 5 — Class Diagram, mô hình dữ liệu sơ bộ và tổng hợp

- Xác định các lớp ứng viên như `User`, `Admin`, `Teacher`, `Student`, `Exam`, `Question`, `AnswerOption`, `Submission` và `Result`; điều chỉnh theo yêu cầu đã chốt.
- Xác định thuộc tính, phương thức, quan hệ và bội số giữa các lớp. Làm rõ cách biểu diễn vai trò người dùng trước khi quyết định tách lớp hay dùng kế thừa.
- Xây dựng mô hình dữ liệu tham khảo, xác định thực thể / bảng dự kiến, khóa chính và khóa ngoại; hoàn thiện thiết kế cơ sở dữ liệu ở giai đoạn 2.
- Chủ trì đối chiếu FR, NFR, DFD, Use Case, Class Diagram và mô hình dữ liệu; ghi nhận điểm chưa thống nhất để người phụ trách phần đó sửa.
- Thống nhất mẫu Word, cách đặt tên và mã tài liệu với nhóm từ đầu; ghép các phần đã được rà soát thành một file Word chung.
- Sắp xếp các phần đã có theo cấu trúc bảy phần trong [GUIDELINES.md](GUIDELINES.md); đặt đặc tả Use Case chi tiết sau sơ đồ Use Case và đánh dấu phần giao diện / dữ liệu còn sơ bộ.

**Bàn giao:** file `.drawio` và ảnh / PDF Class Diagram, mô hình dữ liệu sơ bộ kèm nguồn chỉnh sửa, file Word tổng hợp và danh sách vấn đề cần hoàn thiện ở giai đoạn 2.

### 4.6. Phối hợp và rà soát

- TV1 chia sẻ bản phạm vi, tác nhân và FR ban đầu để các thành viên có cơ sở làm song song; cùng cập nhật khi nhóm chốt thay đổi.
- TV3 và TV4 thống nhất danh sách, mã và tên Use Case trước khi hoàn thiện sơ đồ / đặc tả.
- Mỗi người tự rà soát nội dung và định dạng trước khi gửi TV5. TV5 tổng hợp và phát hiện chỗ chưa nhất quán; người phụ trách từng phần chịu trách nhiệm chỉnh sửa.
- Rà soát chéo: TV4 kiểm tra phần TV1; TV5 kiểm tra phần TV2; TV1 kiểm tra phần TV3; TV3 kiểm tra phần TV4; TV2 kiểm tra phần TV5.
- Cả nhóm xác nhận bản tổng hợp, chốt mức ưu tiên và chia backlog. Việc bàn giao tài liệu giai đoạn 1 không đồng nghĩa đã hoàn thành thiết kế chi tiết của giai đoạn 2.

**Các điểm cần làm rõ cho hệ thống thi trắc nghiệm:**

- Vai trò nào được tạo câu hỏi, tạo đề, tham gia thi và xem kết quả?
- Hỗ trợ loại câu hỏi nào? Quy tắc đáp án và chấm điểm là gì?
- Có giới hạn thời gian, số lần làm bài, lưu bài đang làm hay tự động nộp bài không?
- Kết quả được hiển thị khi nào và cho ai?

Các câu hỏi trên dùng để khảo sát, không mặc định tất cả chức năng đều thuộc phạm vi.

**Tiêu chí hoàn thành M1:**

- [ ] Phạm vi và vai trò người dùng đã được thống nhất.
- [ ] FR và NFR được mô tả bằng ngôn ngữ tự nhiên, có mã và cách nghiệm thu.
- [ ] Có đủ DFD, Use Case Diagram và Class Diagram; nội dung nhất quán với yêu cầu.
- [ ] DFD đúng mức giảng viên yêu cầu; các sơ đồ có file nguồn và bản xuất để xem.
- [ ] Các Use Case quan trọng có đặc tả chi tiết, dùng cùng mã và tên với sơ đồ.
- [ ] Có mô tả giao diện và mô hình dữ liệu sơ bộ; các điểm cần hoàn thiện ở giai đoạn 2 được ghi rõ.
- [ ] File Word tổng hợp đã được từng người rà soát và cả nhóm thống nhất.
- [ ] Các điểm chưa rõ ảnh hưởng thiết kế đã được giải quyết hoặc có quyết định xử lý rõ ràng.
- [ ] Backlog ban đầu có mức ưu tiên và người phụ trách.

## 5. Giai đoạn 2 — Thiết kế

**Điều kiện bắt đầu:** đạt M1; thay đổi yêu cầu tiếp theo phải được ghi nhận và đánh giá ảnh hưởng.

| Mã | Công việc | Sản phẩm bàn giao | Vai trò chính |
| --- | --- | --- | --- |
| P2-01 | Thiết kế danh sách màn hình và luồng thao tác theo các use case đã chốt. | Sơ đồ điều hướng và wireframe / mockup GUI. | Thiết kế |
| P2-02 | Mô tả trạng thái giao diện: dữ liệu trống, nhập sai, tải dữ liệu, thành công và lỗi khi phù hợp. | Interface Design Description. | Thiết kế |
| P2-03 | Chọn kiến trúc hoặc mẫu thiết kế phù hợp đã học; nêu lý do và trách nhiệm từng thành phần. | Sơ đồ và mô tả kiến trúc. | Thiết kế + lập trình |
| P2-04 | Thiết kế mô hình dữ liệu; xác định bảng, thuộc tính, kiểu dữ liệu, khóa chính, khóa ngoại, ràng buộc và quan hệ khi áp dụng. | Data Model, sơ đồ quan hệ và mô tả dữ liệu. | Thiết kế |
| P2-05 | Cụ thể hóa [bộ công nghệ đã chốt](TECH_STACK.md): phiên bản, cấu trúc Django, giao tiếp giữa các thành phần và môi trường chạy. | Phiên bản thống nhất, cấu trúc dự kiến và đặc tả giao tiếp phù hợp kiến trúc. | Lập trình + thiết kế |
| P2-06 | Cập nhật Class Diagram theo thiết kế; kiểm tra khả năng truy vết từ yêu cầu tới màn hình và dữ liệu. | Bộ sơ đồ cập nhật và bảng liên kết yêu cầu – thiết kế. | Phân tích nghiệp vụ + thiết kế |
| P2-07 | Hoàn thiện tài liệu đủ bảy phần theo [GUIDELINES.md](GUIDELINES.md); rà soát và chia task triển khai. | Bộ tài liệu M2 và backlog triển khai. | Cả nhóm, PM điều phối |

**Tiêu chí hoàn thành M2:**

- [ ] Tài liệu có đủ bảy phần, đúng thứ tự theo guidelines.
- [ ] Các luồng chức năng đã chốt đều có thiết kế giao diện phù hợp.
- [ ] Kiến trúc / mẫu thiết kế đã học được chọn và mô tả cách áp dụng.
- [ ] Mô hình dữ liệu thể hiện đủ thuộc tính, khóa, quan hệ và ràng buộc khi áp dụng.
- [ ] Công nghệ, giao tiếp giữa các thành phần và cấu trúc mã nguồn đã rõ.
- [ ] Task triển khai có tiêu chí nghiệm thu và phụ thuộc cụ thể.

## 6. Giai đoạn 3 — Triển khai

**Điều kiện bắt đầu:** đạt M2 và chốt công nghệ.

| Mã | Công việc | Sản phẩm bàn giao | Vai trò chính |
| --- | --- | --- | --- |
| P3-01 | Thiết lập môi trường, cấu trúc mã nguồn và cấu hình mẫu theo kiến trúc đã chọn. | Bộ khung chạy được và hướng dẫn thiết lập. | Lập trình |
| P3-02 | Xây dựng dữ liệu lưu trữ, khởi tạo cấu trúc và dữ liệu mẫu theo thiết kế. | Cơ sở dữ liệu / lớp lưu trữ và cách khởi tạo tái lập được. | Lập trình |
| P3-03 | Triển khai chức năng theo mức ưu tiên và phụ thuộc; hoàn thành từng luồng từ giao diện đến xử lý và lưu dữ liệu. | Các chức năng trong phạm vi, gắn với FR / use case tương ứng. | Lập trình |
| P3-04 | Viết và chạy unit test cho quy tắc nghiệp vụ, trường hợp biên và xử lý lỗi. | Unit test và kết quả chạy. | Lập trình |
| P3-05 | Review Pull Request, tích hợp thường xuyên, xử lý lỗi tích hợp và cập nhật tài liệu khi có thay đổi. | Mã nguồn tích hợp, lịch sử Git và tài liệu khớp với ứng dụng. | Lập trình + người review |
| P3-06 | Chạy thử các luồng chính, chuẩn bị dữ liệu kiểm thử và bản ứng dụng cho giai đoạn 4. | Bản M3, hướng dẫn chạy và danh sách lỗi còn mở. | Lập trình + kiểm thử |

Với chức năng chấm điểm hoặc giới hạn thời gian, nếu thuộc phạm vi, ưu tiên kiểm thử quy tắc tính điểm và các tình huống nộp bài / hết giờ ngay trong giai đoạn này.

**Tiêu chí hoàn thành M3:**

- [ ] Toàn bộ chức năng trong phạm vi đã được triển khai và tích hợp.
- [ ] Kiến trúc đã chọn được thể hiện trong tổ chức và trách nhiệm của mã nguồn.
- [ ] Mã nguồn được quản lý bằng Git và được review theo quy trình nhóm.
- [ ] Unit test đã được thực thi; lỗi làm thất bại kiểm thử được ghi nhận và xử lý.
- [ ] Thành viên khác có thể chạy ứng dụng theo hướng dẫn với dữ liệu mẫu.
- [ ] Các lỗi còn mở có mức độ ảnh hưởng và người phụ trách.

## 7. Giai đoạn 4 — Kiểm thử và hoàn thiện

**Điều kiện bắt đầu:** có bản M3 chạy được, bộ yêu cầu và môi trường kiểm thử thống nhất.

| Mã | Công việc | Sản phẩm bàn giao | Vai trò chính |
| --- | --- | --- | --- |
| P4-01 | Hoàn thiện test case từ FR, NFR và use case; xác định dữ liệu và kết quả mong đợi. | Bộ test case và bảng truy vết yêu cầu – test case. | Kiểm thử |
| P4-02 | Thực thi kiểm thử chức năng, tích hợp, luồng người dùng và NFR theo tiêu chí đã chốt. | Kết quả Pass / Fail / Blocked, môi trường và bằng chứng kiểm thử. | Kiểm thử |
| P4-03 | Chạy bộ unit test; tổng hợp kết quả và xác định các trường hợp cần bổ sung. | Báo cáo unit test. | Lập trình + kiểm thử |
| P4-04 | Ghi nhận lỗi, phân loại ảnh hưởng, giao người xử lý và gỡ lỗi. | Danh sách lỗi, bản sửa và liên kết task / PR liên quan. | Kiểm thử + lập trình |
| P4-05 | Kiểm thử lại lỗi đã sửa và chạy hồi quy các luồng bị ảnh hưởng. | Kết quả retest và regression test. | Kiểm thử |
| P4-06 | Đối chiếu yêu cầu, mã nguồn và tài liệu; chuẩn bị hướng dẫn chạy và kịch bản demo. | Bộ bàn giao M4 và báo cáo kiểm thử cuối. | Cả nhóm |

**Thông tin tối thiểu của test case:** mã test, mã yêu cầu, mục tiêu, tiền điều kiện, dữ liệu, bước thực hiện, kết quả mong đợi, kết quả thực tế, trạng thái và mã lỗi nếu có.

**Thông tin tối thiểu của lỗi:** mã lỗi, tiêu đề, môi trường / phiên bản, bước tái hiện, kết quả mong đợi và thực tế, bằng chứng, mức độ ảnh hưởng, độ ưu tiên, người phụ trách và trạng thái. Có thể theo dõi theo luồng `Open → In Progress → Ready for Retest → Closed`; mở lại nếu kiểm thử lại vẫn lỗi. Đây là trạng thái lỗi đề xuất, phân biệt với luồng Jira task trong hướng dẫn thành viên.

**Tiêu chí hoàn thành M4:**

- [ ] Mỗi FR và NFR đều có cách kiểm chứng, test case tương ứng và kết quả được ghi nhận.
- [ ] Đã thực thi test case và unit test; không còn trường hợp thất bại chưa được giải thích / xử lý.
- [ ] Không còn lỗi chặn luồng chính hoặc làm sai kết quả nghiệp vụ trong phạm vi đã chốt.
- [ ] Lỗi đã sửa được kiểm thử lại; các luồng bị ảnh hưởng được kiểm thử hồi quy.
- [ ] Mọi hạn chế hoặc lỗi còn lại được ghi rõ, có đánh giá ảnh hưởng và được nhóm thống nhất khi bàn giao.
- [ ] Tài liệu, mã nguồn, cách khởi tạo dữ liệu, hướng dẫn chạy và demo nhất quán với bản bàn giao.

## 8. Theo dõi tiến độ và thay đổi

- Trước khi nhận task: thống nhất mục tiêu, người phụ trách, người rà soát và phụ thuộc trên Jira.
- Khi có tiến triển hoặc trở ngại: cập nhật task, sản phẩm thực tế, lỗi và vấn đề cần nhóm hỗ trợ.
- Cuối mỗi giai đoạn: dùng checklist M1–M4 để xác nhận đủ điều kiện chuyển bước.
- Khi đổi yêu cầu: ghi nội dung thay đổi, lý do và ảnh hưởng tới thiết kế, mã nguồn, test case và khối lượng công việc; nhóm thống nhất trước khi triển khai phần phát sinh.
- Khi thiếu thời gian: ưu tiên phạm vi cốt lõi đã thống nhất, điều chỉnh phần mở rộng và giữ đủ sản phẩm bắt buộc theo guidelines.

| Rủi ro | Cách xử lý dự kiến |
| --- | --- |
| Phạm vi quá lớn hoặc thay đổi liên tục | Chốt ưu tiên từ M1, đánh giá tác động của từng thay đổi. |
| Thành phần phụ thuộc chưa sẵn sàng | Chốt giao tiếp từ M2, dùng dữ liệu mẫu và tích hợp sớm. |
| Mất thời gian thiết lập môi trường | Có hướng dẫn chạy và kiểm tra trên máy thành viên khác từ M3. |
| Dồn kiểm thử đến cuối | Viết unit test khi triển khai, chuẩn bị test case từ yêu cầu và thiết kế. |
| Tài liệu không khớp sản phẩm | Cập nhật tài liệu cùng task thay đổi, rà soát lại tại mỗi mốc. |

## 9. Danh mục bàn giao cuối dự án

Danh mục dưới đây tổng hợp sản phẩm cần có theo guidelines và các tài liệu hỗ trợ nhóm đề xuất:

- [ ] Tài liệu đặc tả và thiết kế đủ bảy phần trong [GUIDELINES.md](GUIDELINES.md).
- [ ] DFD, Use Case Diagram, Class Diagram và Data Model, kèm nguồn chỉnh sửa.
- [ ] Thiết kế GUI và mô tả kiến trúc / mẫu thiết kế đã áp dụng.
- [ ] Mã nguồn được tổ chức rõ ràng và quản lý phiên bản.
- [ ] Bộ test case, unit test, kết quả kiểm thử và danh sách lỗi kèm tình trạng xử lý.
- [ ] Hướng dẫn cài đặt, cấu hình, khởi tạo dữ liệu và chạy ứng dụng (đề xuất hỗ trợ bàn giao).
- [ ] Dữ liệu mẫu và kịch bản demo theo phạm vi hoàn thành (đề xuất hỗ trợ trình bày).
