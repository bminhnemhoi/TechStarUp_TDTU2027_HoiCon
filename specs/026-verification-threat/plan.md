# Kế hoạch Spec 026: Tác tử xác minh, tra cứu E10 & danh sách đe dọa trên máy

**Mã**: `026-verification-threat` · **ROADMAP**: `P2-11` · **Làn**: A + B · Spec: [`spec.md`](spec.md)

## 1. Kiểm theo hiến chương

| Nguyên tắc | Áp dụng |
|---|---|
| I. Dừng an toàn tất định ≤ 3 s | Tra bucket là phép tìm nhị phân trong bộ nhớ (≤ 5 ms), không I/O và không mạng trong `onScreenCall`. Đường dừng an toàn không đổi |
| II. Riêng tư theo thiết kế | D1 (bucket k-ẩn danh, không phát h1); số thô không rời máy; URL chỉ giữ HMAC của host; `bucket_enc` mã hóa; mục đích đồng ý `lookups` mới |
| III. LLM chỉ nâng, qua `llm_router` | Không có lời gọi LLM mới; `rescore` tất định và chỉ nâng; ghi xuyên `incidents.level` bằng `raise_level` |
| IV. Công khai AI + đồng ý | `disclaimer` trong hợp đồng; E10 đọc to; tin `evidence` qua `texts._message`; `consents.purpose += lookups` |
| V. Hợp đồng trước, migration bất biến | 3 schema mới + 1 enum, viết trước; `0007` mới, không sửa `0001`…`0006` |
| VI. UX người cao tuổi | E10 theo CLAUDE.md luật 15 (≥ 20sp, ≥ 64dp, 200%, ≤ 2 hành động, màu + biểu tượng + chữ). **Không** dùng ngưỡng 56dp / fontScale 1,5 của bản giao việc |
| VII. Bằng chứng trung thực | Số E10 là số máy ảo; tỉ lệ khớp nhầm đo bằng số hư cấu; k-ẩn danh ghi là ước tính có công thức |
| VIII. Ít code, tái sử dụng | Dùng lại `lookup_h1`, `candidate_hmacs`/`hmac_h1`, `_aead`, `_lock`, `texts._message`, `notify`, `PhoneHasher`, `Speaker`, `ConsentLedger`, mẫu `ElderApiClient`/`ElderAnswerWorker` |
| IX. Chặn phát hành | Không đổi; vẫn cần P2-02 + P2-05 + P1-08 |

## 2. Quyết định kiến trúc

### D1. Danh sách đe dọa trên máy: bucket k-ẩn danh, không phát h1 (đề xuất ADR-011, sửa đổi một ý của ADR-006)

**Vấn đề.** Muốn tra ngoại tuyến, máy phải trả lời được "h1 này có trong danh sách không" mà không cần mạng. Nhưng bất cứ
thứ gì cho phép máy trả lời câu đó với độ chính xác tuyệt đối thì kẻ tấn công cũng chạy được trên toàn bộ không gian số
(ước tính S ≈ 3,6 × 10⁸ số di động VN: khoảng 36 đầu số 3 chữ số × 10⁷). Nghĩa là danh sách sẽ lộ nguyên vẹn, kể cả số
của người vô tội bị kẻ gian giả mạo. Một Bloom filter chính xác cao cũng không khá hơn. Khóa nhúng trong app cũng không
giúp gì, vì app công khai trên Play.

**Các phương án.**

| Phương án | Ngoại tuyến | Lộ danh sách | Máy chủ phải lưu | Kết luận |
|---|---|---|---|---|
| A. Tập h1 (ADR-006 cũ) | chính xác | **toàn bộ**, dò ngược trong vài giây | h1 hoặc `value_enc` | loại |
| B. Chỉ tra trực tuyến | không | không | không | loại: mất US-06.3 khi mất mạng, thêm độ trễ mạng vào `onScreenCall` (hạn 5 s của Telecom) |
| **C. Bucket k-ẩn danh** | "có thể" (khớp nhầm có giới hạn) | mỗi chỉ báo lẫn trong ≈ S/2^b số | `bucket_enc` mã hóa | **chọn** |

**Cơ chế.**
- **Tính bucket.** `bucket24 = int(h1[0:6], 16)`. h1 đã là SHA-256 nên 24 bit đầu phân bố đều, máy không cần băm thêm.
  Ảnh chụp phát `bucket = bucket24 >> (24 − b)` với `b = HOICON_THREAT_BUCKET_BITS` (mặc định **22**).
- **k-ẩn danh.** b = 22 ⇒ ≈ 3,6 × 10⁸ / 4.194.304 ≈ **86 số di động mỗi bucket**. Kẻ tấn công chỉ biết "một trong 86
  số này *có thể* có tên trong danh sách". b = 24 ⇒ ≈ 21 số.
- **Khớp nhầm trên máy.** Tỉ lệ khớp nhầm là `N / 2^b` cho một số lạ ngẫu nhiên. Với b = 22: N = 2.000 ⇒ 0,05%;
  N = 10.000 ⇒ 0,24%. Khi tỉ lệ này vượt 0,25% thì ops nâng b lên 23–24. Số 0,25% là giới hạn đề xuất: đổi lấy khoảng
  21–43 số mỗi bucket.
- **Hệ quả của khớp nhầm.** R1 vốn đã `high` cho mọi chuỗi "số lạ → app tài chính". Khớp bucket chỉ nâng lên `critical`,
  và AlertService cảnh báo ở cả hai mức. Máy chủ vẫn tra chính xác `h1` khi nhận sự kiện (`prepare_event`), và lý do
  "có trong danh sách cảnh báo" trong tin gửi người giám hộ chỉ lấy từ kết quả tra chính xác đó. Vì vậy khớp nhầm không
  bao giờ tạo ra một khẳng định sai gửi tới con.
- **Lưu ở máy chủ.** Không được lưu `bucket24` dạng rõ cạnh `last3`. Lý do: kẻ lấy được bản sao DB chỉ cần thử S số với
  SHA-256 là ra (24 bit + 3 số cuối gần như xác định duy nhất một số), tức là vô hiệu pepper của ADR-006. Vì vậy lưu
  `bucket_enc = "<kid>." + base64url(nonce ‖ AES-256-GCM(bucket24, HOICON_DATA_KEY_<kid>, aad))`, với
  `aad = "hoicon:threat:bucket:v1:<kid>:<value_hmac>"` để tráo bản mã giữa hai dòng làm giải mã hỏng. Thực hiện theo mẫu
  `encrypt_chat_id`.
- **Không có delta.** Ảnh chụp ≈ 3 byte mỗi bucket: 10.000 chỉ báo ≈ 30 KB (≈ 40 KB khi base64). Không cần delta tới
  khoảng 100.000 chỉ báo. `since` là phiên bản ảnh chụp: trùng thì trả 304.

**Phần ADR-006 bị sửa:** chỉ một ý "Danh sách đe dọa gửi xuống máy dạng tập h1". ADR-011 ở trạng thái **Đề xuất**: Tiến
chấp nhận rồi mới gắn dòng "Sửa đổi bởi ADR-011" vào ADR-006.

### D2. Xác minh trong đồ thị: node `verification`, rescore tất định, không dùng trạng thái `verifying`/`rescore`

- **Vị trí:** `risk_scorer` → (không còn câu hỏi) → **`verification`** → `intervention`. Đặt trước `intervention` để
  mức đã gom đủ kết quả xác minh khi báo người giám hộ. Đặt sau `ask_elder` để gom được cả số mà người cao tuổi tra trong
  lúc trả lời câu hỏi E8.
- **Hai lý do không chuyển sự cố sang `verifying`:**
  - `decided_state` sẽ coi sự cố là "đã quyết", khiến `await_guardian` nhảy tới `resolve`.
  - `ALLOWED` chỉ cho `awaiting_guardian → verifying`, tức là phải chờ người giám hộ trước.

  Xác minh vì vậy là chú thích (dòng `verifications`) cộng với nâng mức, không phải một trạng thái. Hai trạng thái kia giữ
  nguyên trong máy trạng thái để dùng sau; ghi vào ROADMAP "Ghi chú".
- **Không có LLM.** "Nguồn dẫn" phải là dữ kiện có thật (tên danh sách, phiên bản, quy tắc). LLM chỉ có thể bịa thêm
  nguồn. Thiết kế này lệch khỏi bảng hồ sơ `strong` cho "xác minh" trong `docs/AGENTS.md`, nên phải cập nhật tài liệu đó.
- **Đồ thị không băm lại số.** State đồ thị không mang h1 (bất biến của 024). Dòng xác minh của số gọi đến được ghi ở
  `POST /v1/events`, nơi request còn h1 (FR-008).
- **Ghi xuyên mức.** `verification` gọi `IncidentService.raise_level(max(state.level, sàn xác minh))`. Việc này cũng ghi
  về mức mà `risk_scorer`/E8 đã nâng, đóng phần còn mở của 024 ("mức đồ thị nâng chưa ghi về `incidents.level`").
- **Bằng chứng giữa lúc chờ:**
  - `/v1/lookups` không gửi tin (luật 5). Router xếp job `graph_resume {"evidence": id}` với `expect="await_guardian"`.
  - Node `await_guardian`, vốn đã được phép gửi tin, gửi tin mẫu `evidence`. Khóa `notify` là `{incident}:msg:evidence`,
    nên mỗi sự cố tối đa một tin.
  - Nếu đồ thị chưa tới `await_guardian` thì `resume` bị bỏ qua (giá trị đến sớm). Khi đó `verification` sẽ gom dòng
    đó ở lượt đi qua, nên không mất gì.
  - Nếu bằng chứng đến sau khi job khóa `{incident}:evidence` đã dùng thì chỉ còn nâng mức, không có tin thứ hai (chủ ý).

### D3. Hạn mức `/v1/lookups`: đếm bền trên `verifications`, khóa theo người gọi

- **Vì sao cần.** Tra `phone` là một "oracle" chính xác: kẻ có JWT có thể dò từng số. Hạn mức biến việc dò cả danh sách
  thành bất khả thi: 60 lần/ngày so với 3,6 × 10⁸ số.
- **Cách đếm.** Trong cùng giao dịch: lấy `pg_advisory_xact_lock(hashtext('lookup:' || actor_id))`, rồi
  `count(*) FROM verifications WHERE actor_id = :a AND at > now() - interval` (chỉ mục `(actor_id, at)`), rồi mới ghi dòng
  mới. Hai request đồng thời không cùng lọt qua mức "còn 1 lần".
- **Vì sao không dùng bộ đếm trong bộ nhớ như MCP:** đếm trên DB bền qua khởi động lại và để lại vết kiểm toán sẵn.
- **Ngưỡng.** Thiết bị 20/giờ, 60/ngày. Người giám hộ 60/giờ. Gia đình 200/ngày (cộng mọi người tra). Request bị từ
  chối không được ghi.
- `threat-list`: 24 lần/ngày/thiết bị. Đếm bằng bộ đếm trong bộ nhớ là đủ, vì dữ liệu này đằng nào cũng phát cho mọi máy.

### D4. Trên máy: một dòng BLOB + chỉ mục trong bộ nhớ, không phải mỗi chỉ báo một dòng Room

- `onScreenCall` chạy trên main thread mà Room cấm truy vấn trên main thread. Hiện `isFlagged` là hàm đồng bộ nên cần
  một cấu trúc trong bộ nhớ.
- `threat_snapshot` (Room v2) giữ một dòng BLOB để bền qua khởi động lại. `ThreatBucketIndex` (`IntArray` đã sắp xếp,
  `binarySearch`) nằm ở `:rules` để test JVM được. 100.000 phần tử ≈ 400 KB RAM, mỗi lần tra 17 phép so sánh.
- So với mỗi chỉ báo một dòng (`ThreatIndicatorEntity` như bản giao việc gợi ý): phương án đó cần 10.000 lần chèn mỗi
  lần đồng bộ, truy vấn không gọi được từ main thread, mà vẫn phải có bản trong bộ nhớ.
- Xóa `threat_hashes` của v1, vì nó lưu h1 + last3 không mã hóa (đúng thứ chú thích của 022 cấm) và chưa từng được ghi.

### D5. URL & QR (P3)

- QR không phải một loại chủ thể mà là một cách nhập (`via=qr`). Nội dung QR được phân loại **trên máy**:
  - URL ⇒ `kind=url`;
  - `tel:` ⇒ `kind=phone` (băm trên máy);
  - VietQR (EMVCo, GUID `A000000727`) ⇒ hiện tên người nhận (tag 59) + cảnh báo chung, **không gửi gì**, vì chưa có
    nguồn dữ liệu tài khoản và số tài khoản là dữ liệu cá nhân.
- Quét bằng Google Code Scanner (`play-services-code-scanner`): giao diện quét do Play services cung cấp nên app **không
  cần quyền `CAMERA`**. Đây là thư viện mới; lý do: không có quyền nào thêm và không đóng gói model. Implementer phải tra
  phiên bản bằng `documentation-lookup`/`search-first` trước khi thêm.

## 3. Luồng chính

```
(1) Tra chủ động (US-06.1/06.4)
E10 ─ số thô (chỉ trong bộ nhớ) ─► PhoneHasher ─► {kind:phone, h1, last3, incident_id?}
   ─► POST /v1/lookups ─[JWT, consent lookups, advisory lock + đếm hạn mức]─► VerificationService.verify_phone
        └► lookup_h1 (HMAC mọi kid) ─► bảng kết luận ─► INSERT verifications ─► (incident_id?) raise_level
                                                                          └► (thiết bị + dangerous) job graph_resume{evidence}
   ◄─ lookup_result {verdict, reasons, sources, disclaimer, incident_level}
   mất mạng/5xx ⇒ E10 dùng ThreatBucketIndex: khớp ⇒ "có thể", không ⇒ "chưa kiểm tra được"

(2) Trong sự cố (US-06.2)
POST /v1/events ─► prepare_event (lookup_h1 trong SAVEPOINT) ─► _start_graph ─► INSERT verifications (system, call, ON CONFLICT DO NOTHING)
đồ thị: ingest → fast_alert → risk_scorer ⇄ ask_elder → verification ─► intervention → await_guardian ⇄ {t1,t2,t3,evidence,decision} → resolve
                                              └ đọc verifications(incident) → rescore max() → raise_level(incidents.level) → agent_steps

(3) Đồng bộ ngoại tuyến (US-06.3)
ThreatSyncWorker ─ GET /v1/threat-list?since=v ─► 304 | 200 {bits, buckets_b64} ─► kiểm hợp lệ ─► Room threat_snapshot ─► ThreatBucketIndex.swap()
onScreenCall ─ PhoneHasher.hash ─► ThreatBucketIndex.contains(bucket(h1)) ─► CallSignal.flagged ─► RiskEngine R1 (critical)
```

## 4. Bảng kết luận (tất định, `VerificationService`)

| Chủ thể | Điều kiện (xét từ trên xuống, dừng ở dòng khớp đầu tiên) | `verdict` | Sàn nâng mức | Mã lý do |
|---|---|---|---|---|
| phone | `lookup_h1` = flagged, `confidence ≥ 0,70` | `dangerous` | `critical` | `listed_high` |
| phone | flagged, `confidence < 0,70` | `warning` | `high` | `listed_low` |
| phone | unknown | `unknown` | — | `not_listed` ("chưa có trong danh sách cảnh báo — vẫn hỏi con trước khi chuyển tiền") |
| url | đường dẫn kết thúc bằng `.apk`, `.xapk`, `.apks`, `.exe`, `.bat`, `.scr` | `dangerous` | `critical` | `app_download` |
| url | host là địa chỉ IP, hoặc có `xn--` (punycode), hoặc thuộc danh sách rút gọn link (`bit.ly`, `tinyurl.com`, `t.ly`, `shorturl.at`, `is.gd`, `cutt.ly`, `rb.gy`) | `warning` | `high` | `ip_host` / `punycode` / `shortener` |
| url | host chứa từ khóa tên ngân hàng hoặc cơ quan (lấy từ `bank_apps.vn.json` + danh sách cố định `congan`, `bocongan`, `thue`, `evn`, `baohiem`, `toaan`) | `warning` | `high` | `brand_lookalike` ("HỏiCon không xác nhận được đây là trang chính thức") |
| url | scheme `http` (không TLS) | `warning` | `high` | `no_tls` |
| url | còn lại | `unknown` | — | `no_signal` |
| bất kỳ | — | `safe` | — | chỉ khi khớp sổ đăng ký chính thức (chưa có ở v1 ⇒ không bao giờ phát ra) |

- `confidence` của URL là cố định theo quy tắc (0,9 / 0,6).
- `sources` ghi `{"name": "<ThreatIndicator.source>", "type": "threat_list", "list_version": "…"}` hoặc
  `{"name": "Quy tắc HỏiCon: <mã>", "type": "heuristic"}`.
- `reasons` là mẫu tiếng Việt, giọng ấm áp, có hành động cụ thể, không chứa cụm nào trong `PANIC_PHRASES` của eval (`eval/checks.py`).

## 5. Bản vẽ migration `0007_verification_lookups`

```python
op.create_table(
    "verifications",
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
    sa.Column("incident_id", sa.Uuid(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True),
    sa.Column("actor", sa.String(16), nullable=False),            # CHECK IN ('device','guardian','system')
    sa.Column("actor_id", sa.Uuid(), nullable=True),             # devices.id | members.id; NULL khi system
    sa.Column("kind", sa.String(16), nullable=False),             # CHECK IN ('phone','url','account')
    sa.Column("via", sa.String(8), nullable=False),               # CHECK IN ('typed','qr','call')
    sa.Column("subject_kid", sa.SmallInteger(), nullable=False),
    sa.Column("subject_hmac", sa.CHAR(64), nullable=False),       # CHECK ~ '^[0-9a-f]{64}$'
    sa.Column("last3", sa.CHAR(3), nullable=True),                # chỉ phone; CHECK ~ '^[0-9]{3}$'
    sa.Column("verdict", sa.String(16), nullable=False),          # CHECK IN ('safe','warning','dangerous','unknown')
    sa.Column("confidence", sa.Numeric(3, 2), nullable=False),    # CHECK 0..1
    sa.Column("sources", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column("list_version", sa.String(32), nullable=True),
    sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
)
op.create_index("ix_verifications_actor_at", "verifications", ["actor_id", "at"])
op.create_index("ix_verifications_incident", "verifications", ["incident_id"])
op.create_index("uq_verifications_call", "verifications", ["incident_id", "kind", "subject_kid", "subject_hmac"],
                unique=True, postgresql_where=sa.text("via = 'call'"))
op.add_column("threat_indicators", sa.Column("bucket_enc", sa.String(128), nullable=True))
# consents: thay CHECK purpose bằng danh sách có thêm 'lookups' (drop + create cùng tên ck_consents_purpose)
```

`downgrade` làm ngược lại: xóa bảng và cột, rồi dựng lại CHECK cũ của `consents` bằng `ADD CONSTRAINT … NOT VALID`.
Không được xóa các dòng `lookups`: trigger `trg_consents_immutable` (migration `0005`) chặn mọi lệnh DELETE trên
`consents`, và đó là bằng chứng đồng ý. `NOT VALID` giữ nguyên các dòng cũ nhưng chặn ghi thêm dòng `lookups` mới.
`test_schema_0007` phải chạy được vòng hạ cấp rồi nâng cấp lại khi đã có dòng `lookups`.

Hạn lưu (`docs/DATA-MODEL.md` §6): `verifications` giữ 90 ngày như sự cố, qua job `retention` (P2-20).

## 6. Phác thảo hợp đồng (Draft 2020-12, `additionalProperties: false` ở mọi đối tượng)

```json
// lookup_request.v1.json
{"oneOf": [
  {"required": ["kind","via","h1","last3"], "properties": {"kind": {"const": "phone"}, "via": {"enum": ["typed","qr"]},
   "h1": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "last3": {"type": "string", "pattern": "^[0-9]{3}$"},
   "incident_id": {"type": "string", "format": "uuid"}}},
  {"required": ["kind","via","url"], "properties": {"kind": {"const": "url"}, "via": {"enum": ["typed","qr"]},
   "url": {"type": "string", "minLength": 4, "maxLength": 2048}, "incident_id": {"type": "string", "format": "uuid"}}}
]}
// lookup_result.v1.json
{"required": ["verification_id","kind","verdict","confidence","reasons","sources","disclaimer","is_demo"],
 "properties": {"verdict": {"enum": ["safe","warning","dangerous","unknown"]},
   "reasons": {"type": "array", "items": {"required": ["code","text"]}},
   "sources": {"type": "array", "items": {"required": ["name","type"], "properties": {"type": {"enum": ["threat_list","heuristic","registry"]}}}},
   "disclaimer": {"type": "string", "pattern": "^Đây là trợ lý AI HỏiCon\\."},
   "incident_level": {"enum": ["low","medium","high","critical"]}}}
// threat_list.v1.json
{"required": ["version","bucket_bits","count","buckets_b64","generated_at"],
 "properties": {"version": {"pattern": "^[0-9a-f]{16}$"}, "bucket_bits": {"minimum": 16, "maximum": 24},
   "count": {"minimum": 0}, "buckets_b64": {"contentEncoding": "base64"}}}
```

Fixture invalid phải bắt được các lỗi sau:
- `phone` mang trường `number`;
- `h1` chữ hoa;
- `disclaimer` thiếu câu công khai;
- `verdict` lạ;
- `bucket_bits = 32`;
- `lookup_result` có khóa `h1` hoặc `subject_hmac`.

## 7. Bản đồ file

| Làn | File | Thay đổi |
|---|---|---|
| chung | `docs/schemas/{lookup_request,lookup_result,threat_list}.v1.json` + fixtures; `consent_record.v1.json` (+`lookups`) | mới/sửa |
| chung | `docs/adr/ADR-011-danh-sach-de-doa-bucket.md` | mới (Đề xuất) |
| B | `backend/migrations/versions/20261016_0007_verification_lookups.py`, `db/models.py` | mới/sửa |
| B | `domain/threat_bucket.py` (bucket24, encrypt/decrypt), `ops/threat_list.py` (ghi `bucket_enc`) | mới/sửa |
| B | `services/verification_service.py`, `services/threat_list_service.py`, `services/incident_service.py` (`raise_level`) | mới/sửa |
| B | `api/routers/lookups.py` (`/v1/lookups`, `/v1/threat-list`), `api/main.py`, `api/routers/events.py` (FR-008) | mới/sửa |
| B | `agents/incident_graph.py` (`verification`, `await_guardian` evidence), `agents/texts.py` (`guardian_evidence`) | sửa |
| B | tests: `unit/test_threat_bucket.py`, `unit/test_verification_rules.py`, `contract/test_lookup_schemas.py`, `integration/test_api_lookups.py`, `integration/test_threat_list.py`, `integration/test_graph_verification.py`, `integration/test_schema_0007.py` | mới |
| A | `rules/.../ThreatBucketIndex.kt` + test JVM | mới |
| A | `data/local/SentinelDatabase.kt` (v2, `ThreatSnapshotEntity`, migration), `app/schemas/…/2.json` | sửa |
| A | `data/remote/LookupApiClient.kt`, `work/Workers.kt` (`ThreatSyncWorker`), `sensing/CallSignalStore.kt` (`LocalLists`) | mới/sửa |
| A | `ui/LookupScreen.kt`, `ui/LookupResultScreen.kt`, `LookupActivity.kt`, `ui/ProtectionStatusScreen.kt` (nút phụ), `data/consent/*` (`lookups`), `res/values/strings.xml` | mới/sửa |
| A (P3) | `ui/QrScan.kt`, `domain/qr/VietQrParser.kt` (+ test JVM) | mới |
| docs | `docs/API.md`, `docs/DATA-MODEL.md`, `docs/AGENTS.md`, `docs/DESIGN-SYSTEM.md` (E10), `docs/ROADMAP.md` | sửa |

## 8. Giai đoạn (hợp đồng trước, sau đó hai làn chạy song song)

| Giai đoạn | Nơi làm | Nội dung | Cổng |
|---|---|---|---|
| 0 | checkout chính | ADR-011 (Đề xuất) + 3 schema + enum đồng ý + fixture + test hợp đồng | merge vào `tien-collab-dev` trước; hai worktree rebase |
| B1 | `hoicon-wt/server` | migration 0007 + model + bucket + loader | `test_schema_0007`, `test_threat_bucket` |
| B2 | server | `VerificationService` + `/v1/lookups` + hạn mức + đồng ý + `raise_level` | `test_verification_rules`, `test_api_lookups` |
| B3 | server | `/v1/threat-list` + cache + 304 | `test_threat_list` |
| B4 | server | FR-008 + node `verification` + evidence + texts | `test_graph_verification`, eval smoke |
| A1 | `hoicon-wt/android` | `ThreatBucketIndex` (`:rules`) + Room v2 + `ThreatSyncWorker` + `LocalLists` | `:rules:test`, `:app:testDebugUnitTest`, test migration Room |
| A2 | android | `LookupApiClient` + E10 + đồng ý `lookups` + lối vào từ E6 | ảnh 100/200%, `ux-elder-reviewer` |
| A3 (P3) | android | QR + VietQR + dán link | test parser, ảnh |
| Z | checkout chính | E2E máy ảo API 36/34, `security-privacy-reviewer`, docs, evidence | mọi lệnh kiểm xanh |

Làn A chạy được trên máy ảo trước khi làn B xong: dùng `MockWebServer`/test với fixture của hợp đồng. Bước E2E (Z) cần cả
hai làn.

## 9. Rủi ro

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Tiến không chấp nhận ADR-011 (giữ tập h1) | Cao về pháp lý | Plan vẫn chạy với `bucket_bits = 24`; nếu vẫn muốn tập h1 thì phải sửa DPIA và có ý kiến Minh (dữ liệu bên thứ ba bị lộ) |
| Khớp nhầm bucket ⇒ `critical` sai trên máy | TB | Có giới hạn `N/2^b` ≤ 0,25%; tin gửi con chỉ dựa trên tra chính xác ở máy chủ; SC-004 đo |
| Danh sách cũ (dòng thiếu `bucket_enc`) không xuống máy | Thấp | Lệnh nạp ghi `bucket_enc`; evidence ghi số dòng thiếu; nạp lại seed demo ở dev |
| Mất `HOICON_DATA_KEY_<kid>` | TB | Nạp lại tệp seed (có h1) là dựng lại được `bucket_enc`; ghi vào `docs/setup` |
| Đổi version `ConsentLedger` buộc người dùng đồng ý lại mọi thứ | TB | FR-011 cấm điều đó; test riêng |
| Node mới làm lệch eval (thêm bước, đổi mức) | TB | Rescore chỉ nâng từ dòng xác minh có thật; ca eval không có dòng nào ⇒ mức không đổi; chạy `--compare baseline` |
| Resume `evidence` đến khi đồ thị chưa chờ ⇒ bị bỏ qua | Thấp | `verification` gom ở lượt đi qua; đã ghi rõ trong D2 |
| Google Code Scanner không có trên máy không có GMS | Thấp | Ẩn nút; P3 cắt được |
