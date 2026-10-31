# Kế hoạch Spec 029: Bộ thí điểm & Play internal v0.3

**Mã**: `029-pilot-kit` · **ROADMAP**: `P2-14` · **Làn**: A + B + H · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| II. Riêng tư | Heartbeat chỉ có các trường Android đang gửi theo văn bản đồng ý hiện hành; báo cáo không có PII |
| IV. Đồng ý | Heartbeat kiểm `core_protection`; xác nhận ≥ 18 tuổi khi ghi danh |
| V. Hợp đồng trước | `heartbeat.v1`, `pilot_report.v1` viết trước, fixture dùng chung với Android |
| VII. Bằng chứng | Crash-free từ Play vitals ghi rõ nguồn + cỡ mẫu; máy ảo ≠ máy thật; chỉ tiêu nhập tay được đánh dấu |
| IX. Chặn phát hành | `release-gate.sh` tự động hóa checklist `release-block`; giai đoạn 2 không bắt đầu khi 012/034/W0-3 chưa xong |

## 2. Quyết định

### D1. Tách giai đoạn theo điều kiện tiên quyết thật

Các phụ thuộc 012 (chưa có spec), W0-3 (⏸) và 011 (chưa có spec) nằm ngoài tầm của code. Vì vậy:
- **Giai đoạn 1 (FR-001…FR-006)** làm ngay. Đây là những thứ Gate M2 cần mà chưa ai làm: heartbeat ở máy chủ, đo độ phủ,
  kiểm `release-block` tự động, tài liệu.
- **Giai đoạn 2 (FR-007…FR-009)** có điều kiện vào rõ ràng, ghi trong `tasks.md`. Thiếu điều kiện thì task đánh BLOCKED,
  không làm vòng.

### D2. Độ phủ heartbeat = số khung 15 phút có tín hiệu ÷ số khung kỳ vọng

- Một dòng `device_heartbeats` mỗi khung 15 phút (PK `(device_id, slot)`), nên kích thước bị chặn: 96 dòng/ngày/thiết bị.
- Khung kỳ vọng tính từ `max(devices.created_at, bắt đầu kỳ)` (thiết bị được tạo lúc ghép đôi) tới `min(revoked_at, hết kỳ)`.
- `protected` lấy từ `permission_state`: các quyền lõi (vai trò call screening, usage access) đều `true`. Danh sách quyền
  lõi lấy từ hằng số dùng chung với `PermissionsScreen`, ghi trong hợp đồng.
- WorkManager có thể dồn heartbeat (Doze), nên độ phủ thực tế trên máy thật có thể dưới 100% dù app vẫn bảo vệ. Ngưỡng
  90% của MASTER-PLAN giữ nguyên; evidence ghi số thật.

### D3. `release-gate.sh` đọc chính tệp phát hành, không đọc mã nguồn

- Kiểm trên AAB/APK thật bắt được cả lỗi cấu hình Gradle, ví dụ thư viện kéo thêm quyền vào manifest đã gộp. Kiểm trên
  mã nguồn thì bỏ sót.
- Công cụ: `aapt2` và `apkanalyzer` từ Android SDK (đã có ở `~/Android/Sdk`); với AAB thì dùng `bundletool` nếu có, nếu
  không thì giải nén `base/manifest/AndroidManifest.xml` (protobuf) bằng `aapt2 convert`.
- Danh sách quyền cấm lấy từ một tệp dữ liệu dùng chung với hook `guard-*` hiện có (nếu có), không chép lần thứ hai.

### D4. Crash-free trước Crashlytics

- Trước 037 chỉ có Android vitals trong Play Console. Ngưỡng của vitals cần đủ người dùng; với 5 gia đình, con số có thể
  "không đủ dữ liệu".
- `gate-m2` nhận số do người nhập (`--crash-free`, kèm `--crash-source "Play vitals, n=…"`) và in rõ "NHẬP TAY". Đây
  không phải số tự đo.

## 3. Hợp đồng (phác thảo)

```json
// heartbeat.v1.json — đúng thân PairingApiClient.sendHeartbeat
{"required": ["app_version","rules_version","permission_state"], "additionalProperties": false,
 "properties": {"app_version": {"type": "string", "maxLength": 32}, "rules_version": {"type": "string", "maxLength": 32},
   "threat_list_version": {"type": "string", "maxLength": 32},
   "permission_state": {"type": "object", "maxProperties": 16,
     "propertyNames": {"pattern": "^[a-z_]{1,32}$"}, "additionalProperties": {"type": "boolean"}}}}
// pilot_report.v1.json
{"required": ["generated_at","days","families"], "properties": {"families": {"items": {
  "required": ["alias","devices","incidents","false_alarms"], "properties": {"devices": {"items": {
    "required": ["device","coverage","protected_ratio","last_heartbeat_at","app_version"],
    "properties": {"device": {"pattern": "^[0-9a-f]{8}$"}, "coverage": {"minimum": 0, "maximum": 1}}}}}}}}}
```

`app_version`/`rules_version` theo cùng mẫu đã siết ở 021 (`risk_event.v1`). Dùng chung định nghĩa qua `$ref`, không
viết lại regex.

## 4. Bản đồ file

| Làn | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/heartbeat.v1.json`, `pilot_report.v1.json` + fixtures | mới |
| B | migration `device_heartbeats`, `db/models.py`, `api/routers/devices.py` (`POST /v1/heartbeat`), `ops/pilot.py` | mới/sửa |
| B | tests: `contract/test_heartbeat_schema.py`, `integration/test_heartbeat.py`, `integration/test_ops_pilot.py`, `integration/test_schema_<số>.py` | mới |
| A | `data/remote/PairingApiClient.kt` (phân biệt 403 `consent_withdrawn`), test ghim fixture `heartbeat.v1` | sửa |
| tooling | `scripts/release-gate.sh`, `scripts/tests/test_release_gate.py` (test trên APK debug ⇒ TRƯỢT) | mới |
| H | `docs/setup/PILOT-ONBOARDING.md`, `docs/setup/PILOT-SUPPORT.md`, `docs/PILOT-PROTOCOL.md` (phần thí điểm) | mới/sửa |
| docs | `docs/API.md`, `docs/DATA-MODEL.md`, `docs/PLAY-POLICY.md` (Data safety) | sửa |

## 5. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| 012/W0-3 trễ ⇒ trễ Gate M2 (20/12) | **Cao** (đường găng MASTER-PLAN) | Giai đoạn 1 làm ngay; báo Minh: 012 cần spec **ngay**, và Play Console cần máy thật để xác minh |
| Doze làm độ phủ < 90% trên máy thật dù app vẫn bảo vệ | TB | Đo trên máy thật ở giai đoạn 2; nếu thấp thì phân tích theo hãng và ghi vào evidence, không hạ ngưỡng âm thầm |
| Crash-free không đủ cỡ mẫu | TB | Ghi "không đủ dữ liệu" trung thực; 037 thêm Crashlytics |
| Không có ai ≥ 18 tuổi xác nhận đúng | Thấp | Cờ `--confirm-adult` bắt buộc + mục trong `PILOT-ONBOARDING` |
