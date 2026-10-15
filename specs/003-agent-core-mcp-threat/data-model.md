# Data model (delta) — spec 003

Nguồn sự thật đầy đủ: [`docs/DATA-MODEL.md`](../../docs/DATA-MODEL.md) §"Xác minh & hồ sơ". Spec này chỉ thêm **một bảng**.

## `threat_indicators` (migration `0004`, `down_revision = "0003"`)

Số điện thoại bị gắn cờ. **Chỉ lưu `HMAC-SHA256(pepper[kid], h1)` + 3 số cuối** (ADR-006); không có cột nào chứa h1 hay số
điện thoại, và không có cột "giá trị thô" để đồng bộ xuống máy (xem "Đã biết" dưới).

| Cột | Kiểu | Ràng buộc |
|---|---|---|
| `id` | uuid | PK |
| `kind` | varchar(16) | `CHECK kind IN ('phone')` |
| `value_hmac` | char(64) | `CHECK value_hmac ~ '^[0-9a-f]{64}$'` (hex chữ thường; `char(64)` tự đệm khoảng trắng nên cần CHECK) |
| `value_kid` | smallint | kid của pepper dùng để băm |
| `last3` | char(3) | rỗng được |
| `source` | varchar(64) | |
| `confidence` | numeric(3,2) | `CHECK confidence >= 0 AND confidence <= 1` |
| `tactic` | varchar(64) | rỗng được |
| `list_version` | varchar(32) | phiên bản danh sách nạp |
| `is_demo` | bool | mặc định `false`; tệp `is_demo` bị từ chối khi `HOICON_ENV=prod` |
| `first_seen` / `last_seen` | timestamptz | mặc định `now()`; nạp lại cập nhật `last_seen` |
| `expires_at` | timestamptz | rỗng được; quá hạn ⇒ tra ra `unknown` |

- `UNIQUE (kind, value_kid, value_hmac)` (`uq_threat_indicators_value`) — đồng thời là chỉ mục tra cứu và khóa upsert.
- Tra cứu: `WHERE kind='phone' AND (value_kid, value_hmac) IN (…mọi kid có pepper…) AND (expires_at IS NULL OR expires_at > now())
  ORDER BY confidence DESC LIMIT 1`.
- Xoay pepper: nạp dùng kid hiện hành (`HOICON_PHONE_PEPPER_KID`); tra thử mọi kid đã cấu hình (`candidate_hmacs`) nên dòng
  kid cũ vẫn tìm thấy.

## Không vào DB

- **McpClient**: tên client ↔ SHA-256 của token, trong cấu hình `HOICON_MCP_THREAT_CLIENTS`; hạn mức đếm trong bộ nhớ tiến trình.
- **BenchReport**: tệp JSON ngoài repo, theo `docs/schemas/bench_report.v1.json`.
- **ThreatSeed**: tệp nạp theo `docs/schemas/threat_seed.v1.json` (đầu vào có h1 — số hư cấu cho tệp demo).

## Đã biết

Máy (Android) so với **h1** của số gọi đến, mà bảng chỉ có HMAC ⇒ chưa đồng bộ được danh sách xuống máy. Spec 022/026 phải chọn:
cột `value_enc` AES-256-GCM (như D1 của spec 002) hoặc danh sách h1 tách khỏi DB. Đã ghi ở ROADMAP "Ghi chú"; không thêm
cột trước khi cần.
