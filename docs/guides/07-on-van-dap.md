# 07 · Ôn vấn đáp

<!-- toc -->

<!-- /toc -->

Bản này viết cho sinh viên năm 2, ít thuật ngữ, dùng ví dụ đời thường. Mỗi mục có **"Trả lời ngắn"** để nói với cô.
Muốn đào sâu (sơ đồ, từng file, cơ sở dữ liệu) thì đọc [06](06-tra-cuu-ky-thuat.md).

## 1. Giới thiệu dự án (30 giây)

> "Nhóm em làm website thi trắc nghiệm online. Có 3 loại người dùng: **Admin** quản lý tài khoản, **Giảng viên** soạn câu hỏi và tạo đề,
> **Sinh viên** làm bài có đồng hồ đếm ngược, nộp bài và xem điểm. Hệ thống tự chấm điểm."

Công nghệ: ngôn ngữ **Python**, khung web **Django**, nơi lưu dữ liệu **PostgreSQL**, đóng gói chạy bằng **Docker**.

## 2. Cô hỏi: "Nhóm dùng mô hình (kiến trúc) gì?"

**Trả lời ngắn:** "Nhóm em dùng **MVC** (Model – View – Controller), một mẫu ở chương 3."

### Giải thích bằng nhà hàng

| Nhà hàng | Trong dự án | Nằm ở đâu |
| --- | --- | --- |
| Khách gọi món | Người dùng bấm trên trình duyệt | Chrome |
| **Phục vụ** nhận order, điều phối | **Controller**: nhận yêu cầu, kiểm tra quyền, gọi Model, chọn trang trả về | `views.py` |
| **Bếp + kho** có công thức nấu | **Model**: dữ liệu và luật (ví dụ đề đã phát hành thì không sửa được) | `models.py` |
| **Đĩa món ăn** bày ra | **View**: giao diện HTML người dùng thấy | `templates/*.html` |

Ba phần tách riêng nên sửa giao diện không làm hỏng luật chấm điểm, và ngược lại.

### Điểm dễ bị hỏi (Django đặt tên lệch)

Django gọi controller là "view" và gọi view là "template". Nên trong code thấy `views.py` nhưng nó **đóng vai Controller**.
Cô hỏi "vậy Django có phải MVC không?" thì trả lời: "Django gọi là MTV (Model – Template – View), nhưng chức năng tương ứng với MVC: Model = Model, Template = View, View = Controller."

### Ví dụ một lần sinh viên bấm "Nộp bài"

1. Trình duyệt gửi yêu cầu lên server.
2. Controller (`attempts/views.py`) kiểm tra: đã đăng nhập chưa, có đúng là sinh viên không.
3. Controller nhờ Model (`Submission.submit()` rồi `grade()`) nộp và chấm điểm.
4. Model lưu kết quả vào database.
5. Controller chọn trang HTML trả về, trình duyệt hiện "Đã nộp bài".

### Câu hỏi thêm có thể gặp

- **Vì sao chọn MVC?** Tách phần dữ liệu, giao diện, xử lý nên 4 người làm song song ít đụng nhau, dễ test và dễ sửa.
- **Luật nghiệp vụ nằm ở đâu?** Ở Model (`models.py`) và `services.py`, không viết trong controller.
- **Có phải kiến trúc client–server không?** Có: trình duyệt là client, Django là server, database nói chuyện với server. MVC là cách tổ chức **bên trong** server.

## 3. Cô hỏi: "Docker là gì? Dùng để làm gì?"

**Trả lời ngắn:** "Docker giúp đóng gói website cùng môi trường chạy của nó vào các 'hộp' (container). Máy nào có Docker chỉ cần vài lệnh là chạy được giống hệt nhau, khỏi cài Python, PostgreSQL thủ công."

### Giải thích bằng cái hộp cơm

- **Image** = công thức + nguyên liệu đã đóng gói sẵn (như hộp cơm chưa mở).
- **Container** = hộp cơm đang được ăn, tức là chương trình đang chạy từ image.
- **Dockerfile** = giấy ghi cách làm một image.
- **Docker Compose / `compose.yaml`** = một tờ thực đơn gọi nhiều hộp chạy cùng lúc và nối với nhau.

### Dự án có 3 container

| Container | Làm gì |
| --- | --- |
| `db` | PostgreSQL 17, nơi lưu mọi dữ liệu. Dữ liệu để ở "volume" `postgres_data` nên tắt Docker không mất |
| `web` | Website Django, chạy ở http://127.0.0.1:8000 |
| `worker` | Tiến trình chạy nền, mỗi 5 giây quét database để **tự nộp bài khi hết giờ**, tự đóng đề hết hạn, chấm lại bài bị lỗi |

Thứ tự khởi động: `db` sẵn sàng → `web` chạy (tự tạo bảng) → `worker` chạy.

**Vì sao cần worker?** Sinh viên có thể đóng trình duyệt giữa chừng, web không còn ai gọi nữa, nên cần một "bảo vệ" chạy nền lo việc hết giờ.

### Dockerfile làm gì (đọc từng dòng)

1. Lấy sẵn Python 3.12 làm nền.
2. Cài các thư viện trong `requirements.txt`.
3. Chép thư mục `src/` (code) vào.
4. Chạy bằng user thường, không dùng quyền cao nhất (an toàn hơn).
5. Khi khởi động: tạo/cập nhật bảng (`migrate`) rồi mở website.

### Lệnh hay dùng

```bash
cp .env.example .env                                    # tạo file cấu hình, mở ra điền mật khẩu
docker compose up -d --build --wait                     # dựng và chạy 3 container
docker compose exec web python manage.py seed_demo      # tạo tài khoản và dữ liệu mẫu
docker compose ps                                       # xem 3 container có Healthy không
docker compose logs worker                              # xem nhật ký worker
docker compose down                                     # tắt (dữ liệu vẫn còn)
```

Mở http://127.0.0.1:8000/accounts/login/ . Tài khoản mẫu: `admin@demo.example`, `teacher@demo.example`, `student1@demo.example`…
Mật khẩu là `DEMO_PASSWORD` trong `.env` (cả nhóm dùng `Kiemthu2026`).

### Câu hỏi thêm có thể gặp

- **Vì sao dùng Docker?** Mọi thành viên và máy báo cáo chạy giống nhau, không bị "máy em chạy được mà máy bạn không".
- **Tắt Docker thì mất dữ liệu không?** Không, nhờ volume. Muốn chắc: có `scripts/backup_db.sh` sao lưu và `restore_db.sh` phục hồi (giữ 7 bản mới nhất).
- **`healthcheck` là gì?** Docker tự hỏi "còn sống không": web gọi `/health/` (kiểm tra cả database), db dùng `pg_isready`.
- **File `.env` là gì? Có đưa lên GitHub không?** Chứa mật khẩu và cấu hình; **không** đưa lên GitHub (nằm trong `.gitignore`), chỉ đưa `.env.example` làm mẫu.
- **Có chạy thật cho nhiều người dùng không?** Bản demo dùng máy cá nhân. Nhóm có đo tải 500 sinh viên bằng Locust và gunicorn, báo cáo ở `docs/loadtest/README.md`.

## 4. Cô hỏi: "Hướng dẫn chạy test"

**Trả lời ngắn:** "Có 2 loại test: **test tự động** chạy bằng một lệnh, và **test case thủ công** theo file Excel template."

### 4.1 Test tự động (unit test)

Là các đoạn code kiểm tra code (khoảng 425 hàm test, nằm trong `src/<app>/tests/`). Chạy bằng Docker:

```bash
docker compose up -d --build --wait
docker compose exec web python manage.py test
```

- Cuối kết quả có chữ **`OK`** nghĩa là tất cả đạt. Có `FAILED` là có test sai.
- Mất khoảng 2–4 phút, **nên chạy trước giờ báo cáo và chụp màn hình dòng `OK`**.
- Chạy riêng một phần: `docker compose exec web python manage.py test accounts` (đổi `accounts` thành `questions`, `exams`, `attempts`, `results`).
- Test chạy trên database **tạm** rồi tự xóa, không làm mất dữ liệu demo.
- Nếu gặp lỗi `too many clients`: tắt web đo tải `docker compose -f compose.yaml -f compose.loadtest.yaml stop web-load` rồi chạy lại.

Ba mức test, nói được với cô:

| Mức | Là gì | Ví dụ file |
| --- | --- | --- |
| **Unit** | Thử từng hàm nhỏ | `test_models.py` (đăng nhập sai 5 lần thì khóa) |
| **Tích hợp** | Thử cả luồng nhiều phần ghép lại | `test_integration_flow.py`, `test_attempts_flow.py` |
| **Thủ công trên trình duyệt** | Tự bấm theo từng bước | Các file `docs/testcases/S3-xx.csv` |

### 4.2 Test case thủ công theo template

- File nộp: `docs/Testing Document - Group04.xlsx`, **đúng template của cô**: 1 sheet "Test Cases", 5 cột
  **Test Case ID – Function – Test Steps – Input Data – Expected Result**. Không thêm cột khác (sai template là 0 điểm).
- Mỗi task Jira viết 1 file CSV (`docs/testcases/S3-xx.csv`), cuối kỳ gộp lại thành một file Excel bằng `scripts/build_testcases.py`.
- Kiểm tra CSV đúng mẫu: `python scripts/build_testcases.py --check` (thấy "hợp lệ" là được).
- Mỗi chức năng có: ca thành công, ca lỗi (nhập thiếu, sai định dạng, sai quyền, hết giờ…), ca vi phạm quy tắc.

Ví dụ một test case: **Bước**: mở trang đăng nhập, nhập sai mật khẩu 5 lần. **Kỳ vọng**: hiện thông báo khóa tạm 15 phút.

### 4.3 Công cụ kiểm thử dùng

- Test tự động: bộ test có sẵn của Django (`manage.py test`).
- Kiểm thử thủ công: trình duyệt Chrome/Edge và file Excel template.
- Đo tải: Locust (500 sinh viên cùng làm bài), kết quả ở `docs/loadtest/`.
- Quản lý lỗi: Jira (Bug: Open → In Progress → Ready for Retest → Closed).

## 5. Cô hỏi: "OOP của nhóm khớp sơ đồ lớp thế nào?"

**Trả lời ngắn:** "Mỗi lớp trên sơ đồ lớp có một lớp Python cùng tên trong `models.py`, và các phương thức trên sơ đồ đều có trong code."

| Lớp trên sơ đồ | File code | Việc chính |
| --- | --- | --- |
| User, Admin, Teacher, Student | `src/accounts/models.py` | Đăng nhập; Admin quản lý tài khoản; Teacher tạo đề; Student làm bài |
| Question, AnswerOption | `src/questions/models.py` | Câu hỏi và các phương án |
| Exam, ExamQuestion, ExamParticipant | `src/exams/models.py` | Đề thi, câu trong đề, sinh viên được giao |
| Submission, SubmissionAnswer | `src/attempts/models.py` | Lượt làm bài và đáp án đã chọn |
| Result | `src/results/models.py` | Tính điểm, quyền xem kết quả |

Các khái niệm OOP có trong dự án:

- **Kế thừa**: Admin, Teacher, Student kế thừa từ User (cùng một bảng `users`, khác nhau ở cột `role`).
- **Đóng gói**: luật nằm trong lớp, ví dụ `Exam.publish()` tự kiểm tra điều kiện rồi mới phát hành.
- **Đa hình / phương thức riêng theo vai trò**: `Teacher.create_exam()`, `Student.submit_exam()`.

## 6. Luồng chính của hệ thống (kể lại khi demo)

1. Giảng viên soạn câu hỏi → tạo đề, chọn câu, đặt điểm → giao cho sinh viên → **phát hành**.
2. Sinh viên thấy đề trong danh sách → bắt đầu, đồng hồ đếm ngược, mỗi lần chọn đáp án tự lưu → **nộp bài**.
3. Hệ thống tự chấm điểm.
4. Giảng viên đóng đề → **công bố điểm** → sinh viên xem kết quả.

Các quy tắc hay bị hỏi:

| Câu hỏi | Trả lời ngắn |
| --- | --- |
| Hết giờ thì sao? | Server tính hạn nộp (không tin đồng hồ trên trình duyệt); hết giờ worker tự nộp bằng đáp án đã lưu |
| Mất mạng, tải lại trang? | Đáp án đã lưu từng lần chọn nên không mất, đồng hồ không đặt lại |
| Sao sinh viên không vào được trang của giảng viên? | Kiểm tra quyền ở server, sai vai trò báo lỗi 403 |
| Nhập sai mật khẩu nhiều lần? | 5 lần sai khóa tạm 15 phút |
| Đề đã phát hành có sửa được không? | Không, để kết quả cũ không bị đổi |
| Sinh viên xem điểm lúc nào? | Sau khi giảng viên công bố điểm |
| Mật khẩu có lưu thẳng không? | Không, Django lưu dạng đã mã hóa (băm) |

## 7. Cô hỏi về GitHub, Jira (công cụ quản lý)

- **Mỗi việc một task Jira** (mã S3-xx) → tạo **nhánh** `feature/S3-xx-...` từ `develop` → code, test → mở **Pull Request** vào `develop` → bạn khác xem lại → merge. Cuối cùng `develop` vào `main`.
- **Vì sao dùng nhánh và PR?** Mỗi người làm riêng không phá code của nhau, có người xem lại trước khi gộp.
- **Minh chứng**: tab Commits, Pull requests, Insights → Contributors trên GitHub cho thấy từng thành viên đã làm gì.
- Tin nhắn commit viết ngắn, tiếng Việt, kiểu `feat(S3-10): đo tải 500 sinh viên`.

## 8. Thành viên và phần phụ trách

Xem bảng chi tiết (lớp, file, test, câu hay bị hỏi) ở [van-dap-theo-thanh-vien.md](../project/van-dap-theo-thanh-vien.md). Tóm tắt:

| Người | Phần |
| --- | --- |
| Nguyễn Duy Thái | Tài khoản, đăng nhập, phân quyền (S3-01..05) |
| Nguyễn Quý | Ngân hàng câu hỏi, nhập Excel, đo tải (S3-06..10) |
| Võ Bùi Quốc Nam | Đề thi (S3-11..15) |
| Phạm Công Chánh | Làm bài, nộp bài, chấm (S3-16..20) |
| Lê Hải Đăng | Kết quả, worker, Docker, sao lưu (S3-21..25) |

Lưu ý: tên task S3-01 ghi "Flask" nhưng dự án dùng **Django**. Nếu bị hỏi: nhóm chọn Django ở giai đoạn thiết kế kiến trúc.

## 9. Cô hỏi: "Hệ thống bảo mật như thế nào?"

**Trả lời ngắn:** "Nhóm em bảo vệ ở 4 lớp: **ai được vào** (đăng nhập), **được làm gì** (phân quyền), **dữ liệu có an toàn không** (mật khẩu, chống tấn công phổ biến), và **ghi lại ai làm gì** (nhật ký)."

Ví dụ ngôi nhà: đăng nhập là chìa khóa cửa, phân quyền là mỗi người chỉ vào được phòng của mình, nhật ký là camera ghi lại.

| Vấn đề | Nhóm làm gì | Ở đâu |
| --- | --- | --- |
| **Mật khẩu** | Không lưu mật khẩu thật, Django lưu dạng đã băm (mã hóa một chiều, không dịch ngược được). Luật: ≥ 8 ký tự, có cả chữ và số, không quá phổ biến, không giống email | `settings.py` (`AUTH_PASSWORD_VALIDATORS`), `accounts/validators.py` |
| **Đoán mật khẩu** | Nhập sai 5 lần thì khóa tạm 15 phút (NFR-SEC-07). Khác với Admin khóa hẳn tài khoản | `accounts/models.py` (`User.login`) |
| **Phân quyền** | `@role_required(...)` kiểm tra vai trò **ở máy chủ**: chưa đăng nhập thì về trang Login, sai vai trò thì lỗi 403. Ẩn nút trên giao diện chưa đủ nên không dựa vào đó | `accounts/decorators.py`, mọi `views.py` |
| **Phiên đăng nhập** | Hết hạn sau 30 phút không hoạt động. Cookie đặt `HttpOnly` (JavaScript không đọc được) và `SameSite` (không gửi kèm khi bấm link từ trang lạ), bật `Secure` khi tắt DEBUG | `settings.py` |
| **Khóa/đổi mật khẩu thì phiên cũ** | Hủy hết phiên cũ ngay, người bị khóa bị đá ra liền | `accounts/services.py` (`revoke_user_sessions`) |
| **CSRF** (bị lừa gửi yêu cầu giả) | Mọi form `POST` có `{% csrf_token %}`, Django kiểm tra mã này. Không có chỗ nào tắt kiểm tra | Template, quy tắc ở `03-coding-guidelines.md` |
| **SQL injection** (chèn lệnh vào ô nhập) | Dùng ORM của Django, không tự ghép chuỗi SQL; code không dùng `.raw()` hay `extra()` | Toàn bộ `models.py`, `views.py` |
| **XSS** (chèn mã JavaScript) | Template Django tự "escape" nội dung nhập; không dùng `\|safe`; không nhét dữ liệu người dùng vào `onclick` | `templates/`, quy tắc coding |
| **Open redirect** (đăng nhập xong bị chuyển sang web lạ) | Tham số `next` chỉ chấp nhận địa chỉ cùng website | `accounts/views.py` (`_is_safe_next_url`) |
| **Bí mật** | `SECRET_KEY`, mật khẩu database nằm trong `.env`, không đưa lên GitHub, chỉ có `.env.example` | `.gitignore`, `.env.example` |
| **Không gian lận khi thi** | Hạn nộp tính ở server (không tin đồng hồ trình duyệt); nộp rồi không sửa được; đề đã phát hành không đổi; sinh viên chỉ xem điểm sau khi giảng viên công bố, không thấy đáp án đúng | `attempts/services.py`, `exams/models.py`, `results/models.py` |
| **Tranh chấp dữ liệu** | Khóa dòng database khi sửa cùng lúc (`select_for_update`), mỗi đáp án có `version` để tab cũ không ghi đè tab mới | `exams`, `attempts` |
| **Dữ liệu sai lọt vào** | Database tự chặn (CHECK, khóa ngoại, trigger) kể cả khi ai đó ghi thẳng vào database | `*/migrations/0002_db_rules.py` |
| **Dữ liệu cá nhân** | Xóa tài khoản là xóa mềm (đánh dấu `DELETED`), giữ lịch sử bài thi; dữ liệu demo toàn email giả `@demo.example` | `accounts/models.py` |
| **Docker** | Container chạy bằng user thường, không phải root; cổng database chỉ mở cho `127.0.0.1` (máy mình) | `Dockerfile`, `compose.yaml` |

### Nhật ký `[AUDIT]` (vừa bảo mật vừa bảo trì)

Các thao tác quan trọng được ghi lại kèm thời gian: đăng nhập/đăng xuất, khóa tài khoản, đặt lại mật khẩu, nộp bài, đóng đề, công bố điểm.
Xem khi demo:

```bash
docker compose logs web worker | grep AUDIT
```

Khi có tranh cãi ("em đã nộp bài rồi mà", "ai khóa tài khoản này") thì tra nhật ký.

### Mức bảo mật đạt tới đâu (nói thật)

- Bản demo chạy trên máy cá nhân, **chưa có HTTPS** (mã hóa đường truyền). Khi triển khai thật phải đặt sau máy chủ có HTTPS; code đã có sẵn cấu hình `BEHIND_PROXY` và `CSRF_TRUSTED_ORIGINS` cho trường hợp này.
- Chưa có xác thực 2 bước, chưa có chức năng "quên mật khẩu qua email" (Admin đặt lại mật khẩu thay).
- Test bảo mật có trong `accounts/tests/test_auth_security.py`, `test_audit_log.py`, `test_admin_reset_password.py`.

### Câu hỏi thêm có thể gặp

- **Sinh viên gõ thẳng đường dẫn của giảng viên thì sao?** Trang 403 (demo bước 12).
- **Hai người cùng đăng nhập một tài khoản?** Vẫn được, nhưng khóa/đổi mật khẩu thì mọi phiên bị hủy.
- **Admin có thể tự khóa mình không?** Không. Hệ thống cũng không cho khóa Admin cuối cùng.
- **Mật khẩu của sinh viên admin có xem được không?** Không, chỉ đặt lại được, vì chỉ lưu bản băm.

## 10. Cô hỏi: "Tính bảo trì của hệ thống?"

**Trả lời ngắn:** "Bảo trì là sửa lỗi và thêm chức năng sau này dễ hay khó. Nhóm em làm cho dễ bằng cách: **chia nhỏ code theo chức năng**, **có test tự động**, **có tài liệu**, **có nhật ký** và **quản lý thay đổi bằng Git/Jira**."

Ví dụ: nhà chia thành phòng riêng, có ghi chú vị trí ống nước và dây điện nên thợ đến sửa nhanh.

| Cách làm | Giúp gì | Ở đâu |
| --- | --- | --- |
| **MVC + chia app** | Mỗi chức năng một thư mục (`accounts`, `questions`, `exams`, `attempts`, `results`); đổi giao diện không đụng luật nghiệp vụ | `src/` |
| **Luật nghiệp vụ gom ở Model/`services.py`** | Muốn đổi luật (ví dụ số lần khóa) chỉ sửa một nơi, không rải khắp nơi | `models.py`, `services.py` |
| **Lớp trùng tên với sơ đồ lớp** | Đọc sơ đồ là biết tìm code ở đâu | `models.py` |
| **Test tự động (~425 hàm)** | Sửa xong chạy lại `manage.py test`, nếu hỏng chỗ khác sẽ báo ngay | `src/<app>/tests/` |
| **Migration** | Đổi cấu trúc database có file ghi lại từng bước, máy nào cũng cập nhật giống nhau | `*/migrations/` |
| **Docker** | Cài đặt giống nhau trên mọi máy, dựng lại hệ thống bằng vài lệnh | `Dockerfile`, `compose.yaml` |
| **Cấu hình trong `.env`** | Đổi mật khẩu, cổng, chế độ DEBUG không cần sửa code | `.env.example` |
| **Nhật ký `[AUDIT]`** | Tra lại ai làm gì, lỗi xảy ra lúc nào | `settings.py` (LOGGING) |
| **Sao lưu và phục hồi** | Có sự cố thì lấy lại dữ liệu; có script kiểm tra bản sao lưu dùng được | `scripts/backup_db.sh`, `restore_db.sh`, `check_backup.sh` |
| **Quy tắc viết code chung** | Cả nhóm đặt tên, viết form, ghi migration như nhau nên người khác đọc được | `docs/guides/03-coding-guidelines.md` |
| **Tài liệu** | Hướng dẫn cài đặt, Git, test, sao lưu, kịch bản demo | `docs/guides/`, `docs/project/` |
| **Git + Jira** | Mỗi thay đổi có task, nhánh, PR, lịch sử commit; lỗi nào cũng truy ngược được ai sửa, sửa gì, vì sao | GitHub, Jira |
| **Pin phiên bản thư viện** | `requirements.txt` ghi cố định (ví dụ `Django==5.2.19`) nên không bị lỗi khi thư viện tự cập nhật | `requirements.txt` |
| **Health check** | `/health/` báo web và database còn sống không | `config/views.py` |

### Ví dụ "muốn đổi thì sửa ở đâu?"

| Muốn đổi | Sửa ở |
| --- | --- |
| Khóa 3 lần thay vì 5 lần, hoặc 10 phút thay vì 15 | `accounts/models.py` (hằng số ở đầu file) rồi chạy test |
| Thêm cột cho câu hỏi | Sửa `Question` trong `questions/models.py`, chạy `makemigrations`, commit cả migration |
| Đổi giao diện danh sách đề | `templates/exams/` (không đụng `models.py`) |
| Đổi thời gian worker quét | `attempts/management/commands/run_worker.py` |

### Điểm cần nói thật

- Sơ đồ `.drawio` chưa cập nhật hết các chức năng thêm sau (nhóm ghi rõ ở tài liệu).
- Bản demo chạy `runserver`; muốn chạy thật nên dùng gunicorn (đã có trong `requirements.txt` và đã thử khi đo tải).

## 11. Điểm yếu nên biết trước (nói thật, đừng né)

- Bản demo chạy trên máy cá nhân bằng `runserver`, **chưa có HTTPS**; chạy thật cần máy chủ web chuyên dụng (gunicorn, nhóm đã thử khi đo tải).
- Đo tải: khi 500 sinh viên đăng nhập dồn trong 30 giây thì p95 đăng nhập 3,5 giây (chưa đạt mục tiêu 3 giây); dàn trong 60 giây thì 0,44 giây.
- Sơ đồ `.drawio` chưa cập nhật một số thứ code có thêm sau này (khóa tạm, đổi/đặt lại mật khẩu, nhập Excel, nhân bản đề, thống kê, xuất CSV). Trả lời: "bổ sung sau thiết kế, ở các task S3-30..36".

## 12. Danh sách tự kiểm tra trước ngày báo cáo

- [ ] Giải thích được MVC bằng ví dụ nhà hàng và chỉ ra `models.py`, `views.py`, `templates/`.
- [ ] Kể được 5 biện pháp bảo mật (mật khẩu băm, khóa tạm, phân quyền ở server, CSRF, nhật ký) và chỉ file tương ứng.
- [ ] Kể được 5 cách làm cho dễ bảo trì và chỉ ra "muốn đổi X thì sửa ở đâu".
- [ ] Nói được Docker có 3 container và vai trò từng cái.
- [ ] Tự chạy `docker compose up`, `seed_demo`, rồi `manage.py test` thấy `OK`.
- [ ] Tự làm được luồng demo 12 bước ở [demo-and-handover.md](../project/demo-and-handover.md#kịch-bản-demo).
- [ ] Mở được 3 sơ đồ trên app.diagrams.net và đọc tên 12 lớp.
- [ ] Biết phần mình làm ứng với lớp nào, file nào, test nào, PR nào.
