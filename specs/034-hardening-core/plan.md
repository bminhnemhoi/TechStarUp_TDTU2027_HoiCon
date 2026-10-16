# Kế hoạch Spec 034: Gia cố lõi trước người dùng thật

**Mã**: `034-hardening-core` · **ROADMAP**: `P2-20` (lõi) · **Làn**: B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Thực thi hạn lưu đã cam kết; xóa theo yêu cầu; sao lưu mã hóa; tách role DB |
| IV. Đồng ý | Máy chủ thực thi rút đồng ý; `consents` bất biến kể cả khi xóa gia đình |
| V. Migration bất biến | Chỉ thêm migration mới |
| VII. Bằng chứng | Số khôi phục đo trên máy dev; phần lịch chạy/VPS ghi BLOCKED tới 012 |
| VIII. Tái sử dụng | `AsyncPostgresSaver.adelete_thread`, `enqueue` có khóa, worker sẵn có, `consent_support.purge_family` (test) làm gợi ý cho danh sách bảng, `_aead`/`init_env` cho khóa |

## 2. Quyết định kiến trúc

### D1. Xóa theo yêu cầu = xóa dữ liệu + ẩn danh danh tính, giữ sổ đồng ý

`consents` → `families`/`members` là `RESTRICT` (020), và luật đòi giữ bằng chứng đồng ý. Ba phương án:

| Phương án | Kết luận |
|---|---|
| Đổi FK `consents` sang `CASCADE` | loại: mất bằng chứng đồng ý, trái Nghị định 356/2025 |
| Tách `consents` sang bảng lưu trữ rồi xóa gia đình | loại: phải sửa trigger chỉ-ghi-thêm (chính trigger chặn DELETE), rủi ro cao |
| **Giữ dòng `families`/`members` làm tombstone đã ẩn danh** | **chọn**: `members` chỉ có bí danh + HMAC Zalo + `chat_enc`; làm rỗng các cột đó thì dòng không còn nhận diện được ai. `consents` chỉ còn `purpose`, `granted`, `text_sha256`, thời điểm |

Thứ tự trong job `purge_family`, mỗi bước một giao dịch, lũy đẳng:
1. Thu hồi thiết bị **trước**, để thiết bị không gửi thêm dữ liệu trong lúc đang xóa.
2. Thu thập id sự cố → `adelete_thread` từng thread (ngoài giao dịch DB, vì checkpointer dùng kết nối riêng).
3. Xóa trong một giao dịch: `jobs` (theo `payload->>'family_id'` hoặc khóa có tiền tố id sự cố), `messages_out`,
   `action_tokens`, `agent_steps`/`agent_runs` (theo `thread_id`), `risk_events`, `incidents` (CASCADE nhật ký chuyển),
   `verifications`, `drills`, `trusted_contacts`, `pairing_codes`, `devices`.
4. Ẩn danh `members`, `families`; đánh `data_requests.done`.

Danh sách bảng kiểm bằng test "mọi bảng có cột `family_id` hoặc `incident_id` (truy theo `information_schema`) đều được
xử lý". Thêm bảng mới mà quên cập nhật purge thì test đỏ.

### D2. Hạn lưu chạy theo lô, mỗi loại một hàm, mốc thời gian tiêm được

`RETENTION = {"risk_events": 90 ngày, "agent_steps_content": 30 ngày, …}` đặt ở một chỗ. Mỗi hàm nhận `now` để test lùi
thời gian không cần chờ. Mỗi hàm xóa theo lô `LIMIT 1000` qua `ctid`/`id` trong vòng lặp, mỗi lô một giao dịch, nên
không khóa bảng lâu. Với checkpoint: chọn thread của sự cố `closed_at < now - 7 ngày`, gọi `adelete_thread` từng cái.

### D3. Sao lưu: `pg_dump` trong container, mã hóa theo khối ở phía Python

- Máy dev không có `pg_dump`. Container `postgres` có sẵn, nên chạy
  `docker exec <container> pg_dump -Fc -U hoicon hoicon` và đọc stdout theo luồng.
- Python mã hóa từng khối 1 MiB bằng AES-256-GCM:
  - nonce = 4 byte tiền tố ngẫu nhiên + số thứ tự khối 8 byte;
  - AAD = `hoicon:backup:v1:<kid>:<chỉ số khối>:<cờ khối cuối>`, nên cắt bớt hay đảo khối đều bị phát hiện;
  - bản rõ không bao giờ ghi ra đĩa.
- Manifest ghi số dòng từng bảng (đếm trong cùng snapshot với dump: `pg_dump --snapshot` hoặc
  `REPEATABLE READ` + `pg_export_snapshot()`).
- `restore-check` đi ngược lại, `pg_restore` vào DB tạm rồi so manifest.
- Tên container/URL lấy từ cấu hình, không viết cứng.

### D4. Mặc định `prod`

Đổi mặc định là thay đổi phá vỡ cho máy dev. Bù lại:
- `.env.example` có `HOICON_ENV=dev`;
- `tests/conftest.py` đặt `HOICON_ENV=test` trước khi nạp cấu hình;
- các workflow CI đặt biến tường minh;
- `init_env` ghi `HOICON_ENV=dev`.

Có test bảo đảm mọi chặn "chỉ prod" bật khi biến không được đặt.

### D5. Thực thi đồng ý: đọc dòng mới nhất, đệm ngắn

`SELECT DISTINCT ON (purpose) purpose, granted FROM consents WHERE member_id = :m ORDER BY purpose, recorded_at DESC`,
đệm 60 giây theo `member_id` trong bộ nhớ tiến trình (ADR-002: một tiến trình). Ghi đồng ý mới qua `/v1/consents` thì
xóa mục đệm ngay. Chấp nhận trễ tối đa 60 giây cho trường hợp đồng ý thay đổi từ nơi khác.

## 3. Bản đồ file

| File | Thay đổi |
|---|---|
| `backend/migrations/versions/<ngày>_<số>_hardening_core.py`, `db/models.py` | `data_requests`, `deleted_at`, chỉ mục |
| `services/retention_service.py`, `services/purge_service.py`, `jobs/worker.py` (đăng ký job + lịch hằng ngày) | mới/sửa |
| `ops/data.py`, `ops/backup.py`, `scripts/backup.sh`, `ops/devices.py` (P2), `ops/threat_list.py` (`unflag`, P2) | mới/sửa |
| `api/main.py` (giới hạn thân, `/readyz`), `api/routers/events.py` (+ heartbeat nếu có), `api/routers/consents.py` (xóa đệm) | sửa |
| `config.py` (`env` mặc định `prod`, `backup_key_*`), `ops/init_env.py`, `backend/.env.example`, `.github/workflows/*.yml`, `tests/conftest.py` | sửa |
| `infra/postgres/roles.sql` (P2) | mới |
| tests: `integration/test_retention.py`, `integration/test_purge_family.py`, `integration/test_backup_restore.py`, `integration/test_consent_enforcement.py`, `integration/test_ops_safety.py` (env, readyz, 413), `integration/test_db_roles.py` (P2), `integration/test_schema_<số>.py` | mới |
| docs: `DATA-MODEL.md` §6, `PRIVACY-DPIA.md`, `setup/BACKUP.md`, `API.md` | sửa/mới |

## 4. Giai đoạn

1. Migration + model.
2. Mặc định an toàn: env, `/readyz`, giới hạn thân. Làm sớm vì có thể làm đỏ test cũ.
3. Thực thi đồng ý ở máy chủ.
4. Hạn lưu.
5. Xóa theo yêu cầu.
6. Sao lưu và khôi phục.
7. (P2) Lệnh vận hành, tách role DB.
8. Rà soát bảo mật toàn bộ, tài liệu, evidence.

## 5. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Đổi mặc định `env` làm đỏ CI/máy dev | TB | Giai đoạn 2 làm trước, sửa cấu hình trong cùng PR; test riêng cho mặc định |
| Purge sót bảng mới (026/028 thêm bảng) | TB | Test duyệt `information_schema` bắt mọi bảng có `family_id`/`incident_id` |
| Job hạn lưu xóa nhầm dữ liệu trong hạn | Cao | Test biên (đúng ngày, trước một giây); chạy thử có cờ `--dry-run` in số dòng sẽ xóa |
| Khôi phục chậm hoặc lỗi trên dữ liệu lớn | Thấp (thí điểm nhỏ) | Đo và ghi số; 012 quyết lịch và nơi lưu |
| 403 `consent_withdrawn` chặn sự kiện của máy chưa kịp ghi sổ | TB | Android 022 đã chỉ gửi khi `mayShare()`; test liên làn trong E2E |
| Android hiện coi **mọi** 403 là "chưa xác thực" (`PairingApiClient`: `401, 403 -> Unauthorized`) ⇒ hiện "Kết nối lại" thay vì "cần đồng ý lại" | TB | Thân 403 mang `{"detail": {"code": "consent_withdrawn"}}`; phần sửa Android nằm ở 029 làn A (FR-001). Trước khi sửa, ca này chỉ xảy ra khi app cũ cố gửi sau khi rút đồng ý |
