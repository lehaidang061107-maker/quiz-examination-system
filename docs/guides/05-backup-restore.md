# 05 · Backup & Restore

<!-- toc -->

**Mục lục**

- [Mục tiêu theo đặc tả](#mục-tiêu-theo-đặc-tả)
- [Sao lưu thủ công](#sao-lưu-thủ-công)
- [Sao lưu tự động hằng ngày](#sao-lưu-tự-động-hằng-ngày)
- [Trước mỗi kỳ thi](#trước-mỗi-kỳ-thi)
- [Phục hồi khi có sự cố](#phục-hồi-khi-có-sự-cố)
- [Giới hạn](#giới-hạn)
- [Troubleshooting](#troubleshooting)

<!-- /toc -->

Sao lưu và phục hồi database PostgreSQL theo NFR-REL-04: sao lưu hằng ngày, giữ ít nhất 7 bản gần nhất, kiểm tra
phục hồi trước kỳ thi. Dùng `pg_dump`/`pg_restore` có sẵn trong container `db`, nên máy chỉ cần Docker Desktop.

| Script | Làm gì | Đụng dữ liệu đang dùng? |
| --- | --- | --- |
| `scripts/backup_db.sh` | Tạo `backups/quiz-YYYYMMDD-HHMMSS.dump`, kiểm tra file đọc lại được, giữ 7 bản mới nhất | Không (chỉ đọc) |
| `scripts/check_backup.sh` | Phục hồi thử vào database tạm, đếm 9 bảng nghiệp vụ, so với database đang chạy, rồi xóa database tạm | Không |
| `scripts/restore_db.sh` | Thay toàn bộ dữ liệu bằng một bản sao lưu (tự sao lưu dữ liệu hiện tại trước) | **Có** |

Chạy ở thư mục gốc dự án, khi `db` đang chạy (`docker compose up -d --wait db`). Windows: mở **Git Bash** (cài
cùng Git) rồi chạy y như trên. Thư mục `backups/` đã nằm trong `.gitignore` vì chứa dữ liệu thật.

## Mục tiêu theo đặc tả

| Yêu cầu (NFR-REL-04) | Cách đáp ứng |
| --- | --- |
| Sao lưu hằng ngày | `backup_db.sh` chạy bằng cron lúc 02:00 ([Sao lưu tự động](#sao-lưu-tự-động-hằng-ngày)) |
| Giữ tối thiểu 7 bản gần nhất | Script tự xóa bản cũ, chỉ giữ 7 (`KEEP=7`) |
| Kiểm tra phục hồi trước kỳ thi | `check_backup.sh` ([Trước mỗi kỳ thi](#trước-mỗi-kỳ-thi)) |
| Phục hồi dịch vụ trong 4 giờ (RTO) | Đo trên máy nhóm: phục hồi dữ liệu demo mất khoảng 7 giây, cộng thời gian người trực xử lý |
| Mất dữ liệu tối đa 24 giờ (RPO) | Sao lưu mỗi 24 giờ; phục hồi từ bản gần nhất mất tối đa dữ liệu của một ngày |

Sao lưu **không thay thế** cơ chế lưu đáp án trực tuyến (NFR-REL-02): bài đang làm vẫn lưu thẳng vào database.

## Sao lưu thủ công

```bash
scripts/backup_db.sh
```

```text
Đã sao lưu: backups/quiz-20261122-020000.dump (60K)
Xóa bản cũ: backups/quiz-20261115-020000.dump
Đang giữ 7 bản trong backups/
```

Muốn giữ nhiều bản hơn: `KEEP=14 scripts/backup_db.sh`. File hỏng hoặc rỗng (ví dụ database tắt giữa chừng) bị bỏ,
script báo lỗi và không xóa bản cũ nào.

## Sao lưu tự động hằng ngày

**macOS / Linux** (cron). Mở `crontab -e`, thêm một dòng (sửa đường dẫn cho đúng máy mình):

```text
0 2 * * * cd /đường/dẫn/quiz-examination-system && PATH=/usr/local/bin:/opt/homebrew/bin:$PATH scripts/backup_db.sh >> backups/backup.log 2>&1
```

- `PATH=...` cần có vì cron không biết lệnh `docker` nằm ở đâu (`which docker` để xem).
- macOS: nếu dự án nằm trong `Documents`, cấp **Full Disk Access** cho `cron` (System Settings → Privacy & Security),
  nếu không cron không đọc được thư mục.
- Máy phải bật và Docker Desktop phải đang chạy lúc 02:00. Xem kết quả: `cat backups/backup.log`.

**Windows** (Task Scheduler): Create Basic Task → Daily, 02:00 → Start a program:
`"C:\Program Files\Git\bin\bash.exe"`, Arguments: `-c "cd /c/đường/dẫn/quiz-examination-system && scripts/backup_db.sh >> backups/backup.log 2>&1"`.

## Trước mỗi kỳ thi

Kiểm tra bản sao lưu mới nhất phục hồi được mà không đụng dữ liệu đang dùng:

```bash
scripts/backup_db.sh        # có bản mới nhất ngay trước kỳ thi
scripts/check_backup.sh     # hoặc chỉ định file: scripts/check_backup.sh backups/quiz-...dump
```

```text
Bảng                  Bản sao lưu   Đang chạy
users                            6           6
questions                        7           7
...
results                          3           3
ĐẠT: phục hồi thử thành công trong 1 giây (database tạm đã xóa).
```

Thấy `ĐẠT` là bản sao lưu dùng được. `KHÔNG ĐẠT` hoặc lỗi `pg_restore`: tạo bản mới và kiểm tra lại trước khi mở đề.
Ghi lại ngày giờ và kết quả vào biên bản kiểm thử.

## Phục hồi khi có sự cố

Dùng khi dữ liệu bị xóa nhầm, hỏng, hoặc chuyển sang máy khác. **Toàn bộ dữ liệu hiện tại bị thay** bằng dữ liệu
trong file sao lưu.

1. Chọn bản sao lưu: `ls backups/` (thường là bản mới nhất trước lúc xảy ra sự cố).
2. Chạy:

   ```bash
   scripts/restore_db.sh backups/quiz-20261122-020000.dump
   ```

   Script hỏi xác nhận, phải gõ đúng `dong y`. Sau đó nó tự làm:
   - sao lưu dữ liệu hiện tại vào `backups/truoc-phuc-hoi-*.dump` (lỡ chọn nhầm bản vẫn quay lại được);
   - tạm dừng `web`, `worker`;
   - xóa và tạo lại database, nạp bản sao lưu;
   - bật lại `web`, `worker` (web tự chạy `migrate` khi khởi động nếu bản sao lưu cũ hơn code).
3. Kiểm tra: mở http://127.0.0.1:8000/health/ thấy `"database": "ok"`, đăng nhập và xem dữ liệu.

Lưu ý sau khi phục hồi:

- Mọi thay đổi sau thời điểm sao lưu bị mất (đúng mức RPO 24 giờ). Phiên đăng nhập cũ có thể mất, đăng nhập lại.
- Bài đang làm trong bản sao lưu vẫn giữ hạn `deadline_at` cũ: nếu đã quá hạn, worker sẽ tự nộp bằng đáp án đã lưu
  (BR-21, không tự gia hạn).
- File `truoc-phuc-hoi-*.dump` không bị xóa tự động, xóa tay khi không cần nữa.

## Giới hạn

- Bản sao lưu nằm trên **cùng máy** với database: hỏng ổ đĩa là mất cả hai. Chép thư mục `backups/` sang ổ khác
  hoặc Google Drive của nhóm định kỳ.
- File sao lưu không mã hóa và chứa email, mật khẩu đã băm, bài làm. Không đưa lên GitHub hay chỗ công khai.
- Thời gian phục hồi đo trên dữ liệu demo nhỏ; dữ liệu theo NFR-PER-04 (500.000 bài nộp) sẽ lâu hơn, cần đo lại
  khi làm kiểm thử tải (S3-10).

## Troubleshooting

| Lỗi | Cách xử lý |
| --- | --- |
| `database chưa chạy` | Mở Docker Desktop, `docker compose up -d --wait db` |
| `Permission denied` khi chạy script | `chmod +x scripts/*.sh`, hoặc chạy `bash scripts/backup_db.sh` |
| `không phải bản sao lưu hợp lệ` | File hỏng hoặc không phải file `.dump` của `pg_dump`; chọn bản khác |
| Cron không chạy | Xem `backups/backup.log`; kiểm tra `PATH` có thư mục chứa `docker`, quyền Full Disk Access (macOS) |
| Phục hồi thất bại giữa chừng | Script tự bật lại web/worker và in đường dẫn bản `truoc-phuc-hoi-*.dump`; phục hồi bản đó để quay về |
