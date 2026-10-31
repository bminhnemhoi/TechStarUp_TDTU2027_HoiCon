# Sao lưu và khôi phục Postgres (spec 034)

Phạm vi của 034: **lệnh và tài liệu**. Lịch chạy (cron/systemd timer), nơi lưu ngoài máy và việc áp dụng trên VPS thuộc
spec 012 (chưa có) nên chưa làm.

## Cách hoạt động
- `pg_dump -Fc` chạy **trong container Postgres** (`docker exec`): máy dev không có `pg_dump`/`psql`.
- Python đọc stdout theo luồng và mã hóa từng khối 1 MiB bằng **AES-256-GCM**. Bản rõ chỉ ở bộ nhớ và đường ống, không bao
  giờ chạm đĩa máy chủ.
- Khóa: `HOICON_BACKUP_KEY_<kid>` (hex 64 ký tự), **riêng** với khóa dữ liệu Zalo `HOICON_DATA_KEY_<kid>`. `HOICON_BACKUP_KEY_KID`
  chọn khóa mã hóa bản mới; kid cũ vẫn giải mã được bản cũ (xoay khóa: thêm `HOICON_BACKUP_KEY_2`, đặt KID=2, giữ khóa 1).
- Sinh khóa: `uv run --directory backend python -m hoicon.ops.init_env` (tự thêm biến còn thiếu vào cấu hình cục bộ, không in giá
  trị). **Sao lưu khóa này ở nơi khác với bản sao lưu dữ liệu**: mất khóa là mất khả năng khôi phục.
- Mỗi bản có manifest JSON cạnh nó: số dòng từng bảng (đếm trong **cùng snapshot** với dump nhờ `pg_export_snapshot`),
  `alembic_version`, sha256 của bản mã, kid, số khối. Manifest không chứa khóa hay dữ liệu.

## Định dạng `*.dump.enc`
Phiên bản 2 (spec 037): `HCBK` | phiên bản (1 byte) | kid (1 byte) | salt (16 byte ngẫu nhiên), rồi các khung `độ dài |
bản mã + thẻ GCM`. **Khóa con của từng tệp** = HKDF-SHA256(khóa chính, salt) nên hai tệp không bao giờ dùng chung khóa (hết
rủi ro trùng nonce giữa các tệp); nonce = 4 byte 0 + chỉ số khối; AAD = `hoicon:backup:v2:<kid>:<chỉ số>:<cờ khối cuối>`. Sửa một
byte, cắt khối cuối, đảo hoặc nhân đôi khối, thêm đuôi đều làm giải mã báo lỗi.
Phiên bản 1 (tiền tố nonce 4 byte ngẫu nhiên, dùng thẳng khóa chính; AAD `v1`) vẫn ĐỌC được để khôi phục bản cũ, không còn ghi.

## Lệnh
```bash
bash scripts/backup.sh                 # sao lưu + xoay vòng
bash scripts/backup.sh restore-check   # khôi phục bản mới nhất vào DB tạm rồi kiểm
uv run --directory backend python -m hoicon.ops.backup backup [--dir <thư mục>]
uv run --directory backend python -m hoicon.ops.backup restore-check [--file <tệp>]
uv run --directory backend python -m hoicon.ops.backup restore --to <csdl_rong> [--file <tệp>]   # khôi phục THẬT
uv run --directory backend python -m hoicon.ops.backup rotate [--dry-run]
```
Biến: `HOICON_BACKUP_CONTAINER` (mặc định `hoicon-db`), `HOICON_BACKUP_DIR` (mặc định `~/hoicon-backups`, thư mục 0700, tệp
0600). Người dùng và tên CSDL lấy từ `HOICON_DATABASE_URL`.

## restore-check kiểm gì
Giải mã → `pg_restore` vào DB tạm `hoicon_restore_check` (xóa nếu còn sót, và luôn xóa khi xong, kể cả khi lỗi) →
1. `alembic_version` khớp manifest **và** là head hiện tại của mã nguồn;
2. số dòng **từng** bảng bằng manifest;
3. bốn trigger bất biến còn và ở chế độ `ALWAYS`: `trg_consents_immutable`, `trg_consents_no_truncate`,
   `trg_incidents_terminal`, `trg_incident_transitions_immutable`;
4. in thời gian khôi phục.

Số đo trên máy dev ngày 16/10/2026 (DB dev, 23 bảng, ≈184 nghìn dòng, bản mã ≈8 MB): khôi phục ≈ 3 giây, tổng ≈ 3 giây.
Đây là số đo máy dev; số trên VPS thật phải đo lại ở 012.

## Xoay vòng
Giữ bản **mới nhất của mỗi ngày** trong 7 ngày gần nhất có bản, cộng bản mới nhất của mỗi tuần ISO trong 4 tuần gần nhất
có bản (ngày/tuần tính theo giờ Việt Nam). Tệp tên lạ không bao giờ bị xóa. `--dry-run` chỉ in.

## Khôi phục thật (sự cố): `ops.backup restore`
`restore-check` chỉ chứng minh khôi phục được; **không** ghi đè DB đang chạy. Khôi phục thật là quyết định của con người:
1. Tạo một CSDL **rỗng, mới** (ví dụ `docker exec hoicon-db createdb -U hoicon hoicon_restored`).
2. `uv run --directory backend python -m hoicon.ops.backup restore --to hoicon_restored [--file <tệp>]`.
   Lệnh từ chối CSDL đang chạy của ứng dụng, CSDL hệ thống, CSDL kiểm tra và đích không rỗng (không bao giờ ghi đè).
   Chạy bằng `pg_restore --single-transaction`: **một khối hỏng (sai khóa, sửa byte, cắt cụt) ⇒ bỏ cả lượt, CSDL đích không
   đổi**. Xong thì kiểm `alembic_version`, số dòng từng bảng theo manifest và 4 trigger bất biến ở chế độ `ALWAYS`.
3. Lệnh in danh sách gia đình có yêu cầu xóa dữ liệu **hoàn tất sau thời điểm sao lưu** (đọc `data_requests` của DB đang
   chạy). Bản sao lưu cũ còn dữ liệu của họ ⇒ chạy lại cho từng gia đình, trên CSDL mới, **trước khi** chuyển ứng dụng sang:
   `python -m hoicon.ops.data request-delete --family <id> --now` (với `HOICON_DATABASE_URL` trỏ CSDL đã khôi phục). Lệnh
   chỉ in nhắc, không tự xóa. Nếu DB cũ đã mất hẳn thì không đọc được danh sách: lấy từ nhật ký vận hành/ticket yêu cầu xóa.
4. Kiểm bằng `/readyz`, rồi chuyển ứng dụng sang CSDL mới. Xem thêm `docs/PRIVACY-DPIA.md` (mục Sao lưu).

## Chưa làm (012)
Lịch chạy hằng ngày, lưu bản sao ngoài máy, cảnh báo khi sao lưu thất bại, đo khôi phục trên VPS, nhật ký kiểm toán truy
cập khóa.
