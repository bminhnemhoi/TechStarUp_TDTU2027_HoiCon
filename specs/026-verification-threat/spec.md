# Spec 026: Tác tử xác minh, tra cứu chủ động E10 & danh sách đe dọa trên máy (Verification & Threat List)

**Mã ROADMAP**: `P2-11` · **Làn**: A (Android) + B (server) · **User story PRD**: US-06 · **Cột mốc**: Gate M2
· **Phụ thuộc**: `003-agent-core-mcp-threat` (bảng `threat_indicators`, `lookup_h1`, MCP có token + hạn mức — đã xong),
`024-risk-and-intervention` (đồ thị, `IncidentService`), `025-trace-sse` (`agent_steps`, `redact_json`),
`022-sentinel-v1` (Room `sentinel.db`, `HcCallScreeningService`, `RiskEngine` R1), `020` (sổ đồng ý)
· **Nhánh**: `feat/026-verification-threat` · **ADR**: ADR-001, ADR-006, ADR-009; **ADR-011 mới (đề xuất)**

---

## 1. Bối cảnh

US-06: "Là mẹ/con, tôi tra cứu một số/link/QR đáng ngờ — E10, có nguồn dẫn." Hiện trạng đã đọc (16/10/2026):

| Thành phần | Hiện trạng | Hệ quả cho spec này |
|---|---|---|
| `threat_indicators` (`0004`) | Chỉ `HMAC(pepper[kid], h1)` + `last3`, `kind IN ('phone')`; nạp bằng `ops/threat_list` từ tệp có `h1` | Máy chủ **không có h1** ⇒ không thể phát "tập h1" xuống máy nếu không lưu thêm gì (DATA-MODEL §2 đã ghi đây là nhánh rẽ còn mở) |
| ADR-006 | Ghi "Danh sách đe dọa gửi xuống máy dạng tập h1", đồng thời thừa nhận "h1 dò ngược được" | Mâu thuẫn: `h1` không muối, không gian số di động VN ước tính ≈ 3,6 × 10⁸ ⇒ ai cài app cũng dò ngược được **toàn bộ** danh sách, gồm cả số người vô tội bị kẻ gian giả mạo. Spec này đề xuất **ADR-011** (plan D1) |
| Android `threat_hashes` (Room v1) | Bảng `h1 + last3` **không mã hóa**, chưa từng được ghi; `LocalLists.isFlagged` chỉ có 1 h1 demo cứng trong bản debug | Trái chính chú thích của 022 ("h1 không muối dò ngược được ⇒ không để trong bảng không mã hóa") ⇒ bỏ bảng này |
| `RiskEngine` R1 | Số lạ + app tài chính ⇒ `high`; số bị gắn cờ ⇒ `critical` | Danh sách trên máy chỉ cần trả lời "có thể bị gắn cờ" đủ nhanh cho `onScreenCall` (chạy trên main thread) |
| Đồ thị sự cố | `ingest` đã tra `threat` cho số gọi đến (trong `prepare_event`, có SAVEPOINT); state **không mang h1** (spec 024) | Node xác minh trong đồ thị không băm lại số được; bản ghi xác minh của số gọi đến phải ghi ở `POST /v1/events` (nơi còn h1) |
| Trạng thái `verifying` / `rescore` | Có trong `IncidentService.ALLOWED` nhưng `decided_state` coi mọi trạng thái ngoài `detected/assessing/awaiting_guardian` là "đã quyết" | Chuyển sự cố sang `verifying` sẽ khiến `await_guardian` nhảy thẳng tới `resolve` ⇒ spec này **không dùng** hai trạng thái đó (plan D2) |
| Mức đồ thị nâng | `risk_scorer` nâng `state.level` nhưng chưa ghi về `incidents.level` (còn mở từ 024) | Node `verification` ghi xuyên mức (chỉ nâng) ⇒ trang `/a/` và E9 thấy đúng mức |
| Sổ đồng ý | 9 mục đích; văn bản E3 không nói gì về "tra cứu số/đường link bác tự nhập" | Mục đích dữ liệu mới ⇒ enum `lookups` + văn bản có phiên bản (CLAUDE.md luật 7) |
| Danh mục ngân hàng `bank_apps.vn.json` | Chỉ có `package`, tên, Play URL; **không có** tên miền hay tổng đài chính thức | Chưa có nguồn nào cho phép kết luận "an toàn" ⇒ v1 **không bao giờ** trả `safe` (FR-004) |

## 2. User story (ưu tiên)

| # | Ưu tiên | Câu chuyện | Kiểm chấp nhận |
|---|---|---|---|
| US-06.1 | **P1** | Là mẹ, tôi gõ một số lạ vào E10 và biết ngay số đó có trong danh sách cảnh báo không, kèm nguồn, bằng chữ to và giọng đọc | SC-001, SC-003, SC-005 |
| US-06.2 | **P1** | Là con, khi bố mẹ có sự cố, mức rủi ro tôi thấy phản ánh mọi kết quả xác minh (số gọi đến, số bố mẹ vừa tra) và không bao giờ bị hạ | SC-003 |
| US-06.3 | **P2** | Là mẹ, kể cả khi mất mạng, cuộc gọi từ số có thể nằm trong danh sách cảnh báo vẫn bật khoảng dừng an toàn mức cao nhất | SC-002, SC-004 |
| US-06.4 | **P2** | Là con, nếu đang có sự cố mà mẹ tra ra một số/đường link nguy hiểm, tôi nhận thêm đúng **một** tin báo có bằng chứng | SC-003, SC-006 |
| US-06.5 | **P3 (cắt được)** | Là mẹ, tôi dán đường link hoặc quét mã QR; mã chuyển khoản VietQR hiện tên người nhận ngay trên máy để tôi đối chiếu | SC-005 |

Thứ tự cắt khi trễ (theo luật "gate trễ > 2 ngày ⇒ cắt"): US-06.5 → phần tin bằng chứng của US-06.4 (giữ phần nâng mức).

## 3. Tiêu chí thành công

| Mã | Tiêu chí | Ngưỡng | Nguồn đo |
|---|---|---|---|
| **(SC-001)** | Độ trễ tra cứu | `POST /v1/lookups` p95 ≤ 300 ms phía máy chủ (n ≥ 50, Postgres dev); E10 từ lúc bấm "Kiểm tra" tới khi hiện kết quả p95 ≤ 2 s trên AVD API 36 nối backend dev | pytest đo thời gian; log mốc thời gian trên máy ảo (máy ảo ≠ máy thật, ghi rõ) |
| **(SC-002)** | Riêng tư | 0 số điện thoại thô, 0 `h1`, 0 đường dẫn/truy vấn URL trong `verifications`, `jobs`, `agent_steps`, log; phản hồi `threat-list` chỉ chứa bucket (không h1/HMAC/last3); DB không chứa bucket dạng rõ (chỉ `bucket_enc`); với `bucket_bits = 22`, mỗi bucket ứng với ước tính ≥ 80 số di động VN | test quét DB/log sau bộ test; test schema; phép tính trong plan D1 |
| **(SC-003)** | Đúng đắn của kết luận & nâng mức | Bảng kết luận (plan §4) đúng 100% ca test; `phone`/`account` không bao giờ ra `safe`; `incidents.level ≥ rule_floor` và không bao giờ giảm qua mọi đường (lookup, đồ thị); `hoicon-eval smoke` so baseline: recall ≥ baseline, báo nhầm ≤ baseline, 0 vi phạm, công khai AI 100% | pytest + eval smoke |
| **(SC-004)** | Ngoại tuyến trên máy | Tra bucket trong `onScreenCall` p99 ≤ 5 ms với 100.000 bucket (JVM, `:rules`), không I/O trên main thread; đồng bộ lần hai khi danh sách không đổi ⇒ `304`; tỉ lệ khớp nhầm đo trên 100.000 số hư cấu ngẫu nhiên nằm trong ±30% của `N / 2^bits` | test JVM `:rules`; test API; test thống kê |
| **(SC-005)** | E10 cho người cao tuổi | Ảnh AVD API 36 ở cỡ chữ 100% và 200% cho đủ 5 trạng thái (nguy hiểm, cảnh báo, chưa có thông tin, an toàn [chỉ xem trước], mất mạng): chữ ≥ 20sp, vùng chạm ≥ 64dp, tương phản ≥ 7:1, màu luôn kèm biểu tượng + chữ, ≤ 2 hành động chính, câu công khai AI hiển thị và được đọc to; báo cáo `ux-elder-reviewer` không còn mục chặn | ảnh + báo cáo reviewer |
| **(SC-006)** | Chống lạm dụng | Vượt hạn mức tra cứu ⇒ 429 + `Retry-After` (thiết bị 20/giờ & 60/ngày; người giám hộ 60/giờ; gia đình 200/ngày); chưa đồng ý `lookups` ⇒ 403; `incident_id` của nhà khác ⇒ 404; mỗi sự cố tối đa 1 tin bằng chứng; `threat-list` tối đa 24 lần/ngày/thiết bị | pytest tích hợp |

## 4. Yêu cầu chức năng

- **(FR-001)** Hợp đồng trước (làm ở checkout chính, merge trước khi hai làn tách):
  - `docs/schemas/lookup_request.v1.json`: `kind` ∈ {`phone`, `url`}, `via` ∈ {`typed`, `qr`}, `incident_id?`.
    - Với `phone`: bắt buộc `h1` (hex 64) + `last3`; **cấm** mọi trường chứa số thô.
    - Với `url`: `url` ≤ 2.048 ký tự.
    - `account` để dành cho sau (bị từ chối 422 với `kind_not_supported`).
  - `docs/schemas/lookup_result.v1.json`: `verification_id`, `kind`, `verdict` ∈ {`safe`, `warning`, `dangerous`, `unknown`},
    `confidence`, `reasons[]` (mã + câu tiếng Việt), `sources[]` (`name`, `type` ∈ {`threat_list`, `heuristic`, `registry`},
    `list_version?`, `url?`), `disclaimer` (bắt đầu bằng "Đây là trợ lý AI HỏiCon."), `incident_level?`, `is_demo`.
  - `docs/schemas/threat_list.v1.json`: `version`, `bucket_bits` ∈ [16, 24], `count`, `buckets_b64`, `generated_at`.
  - Thêm `lookups` vào enum `purpose` của `consent_record.v1.json`.

  Mỗi schema có fixture `valid`/`invalid`. Đổi API ⇒ sinh lại client TS.
- **(FR-002)** Migration `0007_verification_lookups` (chỉ làn B):
  - Bảng `verifications`: `id`, `family_id` (FK `CASCADE`), `incident_id` (FK `incidents`, `CASCADE`, nullable), `actor`
    ∈ {`device`, `guardian`, `system`}, `actor_id`, `kind`, `via` ∈ {`typed`, `qr`, `call`}, `subject_kid`,
    `subject_hmac` (CHECK hex 64), `last3`, `verdict`, `confidence`, `sources` jsonb, `list_version`, `is_demo`, `at`.
    - Chỉ mục `(actor_id, at)` cho hạn mức.
    - Chỉ mục `(incident_id)`.
    - UNIQUE một phần `(incident_id, kind, subject_kid, subject_hmac) WHERE via = 'call'` để ghi số gọi đến lũy đẳng.
  - `threat_indicators` thêm `bucket_enc` (text, nullable).
  - CHECK `consents.purpose` thêm `lookups`.
  - Cập nhật `db/models.py`, `docs/DATA-MODEL.md`.
- **(FR-003)** Bucket k-ẩn danh (ADR-011):
  - `domain/threat_bucket.py`: `bucket24(h1) = int(h1[:6], 16)`.
  - Mã hóa bucket: `encrypt_bucket` / `decrypt_bucket` (AES-256-GCM với `HOICON_DATA_KEY_<kid>`, AAD
    `hoicon:threat:bucket:v1:<kid>:<value_hmac>`; tráo bản mã giữa hai dòng ⇒ giải mã hỏng).
  - Lệnh nạp `ops/threat_list` ghi `bucket_enc` cho mỗi chỉ báo (tệp nạp có h1). Dòng cũ thiếu `bucket_enc` không được
    phát xuống máy cho tới khi nạp lại.
  - Trên máy: `ThreatBucketIndex` (`:rules`, JVM thuần) tính bucket từ cùng h1 của `PhoneHasher`.
- **(FR-004)** `services/verification_service.py`:
  - `verify_phone(session, h1, last3)` dùng lại `lookup_h1` (không viết truy vấn mới).
  - `verify_url(url)` áp quy tắc tất định ở plan §4.
  - `record(...)` ghi `verifications`.
  - Bảng kết luận cố định: `phone`/`account` **không bao giờ** `safe`; `safe` chỉ dành cho khớp sổ đăng ký chính thức
    (v1 chưa có, nên không bao giờ phát ra).
  - Lý do và nguồn là mẫu soạn sẵn, **không gọi LLM**. Mỗi kết quả có `disclaimer` công khai AI.
  - URL chỉ giữ tên máy chủ (đã chuẩn hóa IDNA, chữ thường) trong bộ nhớ của request. Chỉ lưu
    `HMAC(pepper, SHA-256("hoicon:url:v1:" + host))`. Đường dẫn, truy vấn và thông tin đăng nhập trong URL bị bỏ ngay
    sau khi phân tích.
- **(FR-005)** `POST /v1/lookups` (router `lookups.py`):
  - Nhận JWT thiết bị hoặc JWT người giám hộ.
  - Đòi đồng ý `lookups` mới nhất đang `granted` của thành viên; nếu không ⇒ 403 `consent_required`.
  - Hạn mức đếm trên `verifications` trong cùng giao dịch, dưới `pg_advisory_xact_lock(actor_id)` để chính xác khi gọi
    đồng thời; vượt ⇒ 429 + `Retry-After`.
  - `incident_id` phải thuộc gia đình của người gọi, nếu không ⇒ 404.
  - Lỗi 422 chỉ nêu vị trí (handler sẵn có).
  - Không log `h1`, URL, host hay HMAC.
- **(FR-006)** Nâng mức từ tra cứu trong sự cố (raise-only):
  - Thêm `IncidentService.raise_level(session, incident_id, level, reason)`: chỉ nâng `level` (không đụng `rule_floor`),
    tăng `version`, không đổi trạng thái, giữ khóa sự cố. Sự cố không ở `GUARDIAN_DECIDABLE` ⇒ không làm gì.
  - Khi `/v1/lookups` có `incident_id` và kết luận `dangerous` (⇒ `critical`) hoặc `warning` (⇒ `high`): gọi
    `raise_level`.
  - Nếu thêm nữa người tra là **thiết bị** (người cao tuổi) và kết luận là `dangerous`: xếp job `graph_resume`
    `{"evidence": verification_id}`, `expect="await_guardian"`, khóa `{incident_id}:evidence` (mỗi sự cố một lần).
- **(FR-007)** Đồ thị sự cố:
  - **Node `verification`** chèn giữa `risk_scorer` (khi không còn câu hỏi) và `intervention`:
    - đọc mọi dòng `verifications` của sự cố;
    - `rescore` tất định `level = max(state.level, sàn từ kết luận)`;
    - ghi xuyên `incidents.level` qua `raise_level` (gồm cả mức `risk_scorer` đã nâng, đóng phần mở của 024);
    - ghi `agent_steps` với `{checked, dangerous, warning, level_before, level_after}` (không HMAC, không nguồn thô);
    - lượt eval/demo không có sự cố thật ⇒ bỏ qua đọc/ghi DB.
  - **`await_guardian`** nhận thêm giá trị resume `{"evidence": id}`: nếu sự cố chưa quyết thì gửi đúng một tin mẫu
    `evidence` (`texts.guardian_evidence`, mở đầu công khai AI, nhãn diễn tập, chỉ "số đuôi …123" hoặc "một đường link")
    qua `notify` (khóa `{incident}:msg:evidence`), rồi quay lại chờ. Bộ hẹn giờ T1/T2/T3 giữ nguyên mốc vì có khóa theo tên.
  - Không thêm lời gọi LLM. Không dùng trạng thái `verifying`/`rescore`.
- **(FR-008)** Ghi xác minh số gọi đến ở `POST /v1/events`: khi `_start_graph` khởi động đồ thị cho sự cố, ghi một dòng
  `verifications` (`actor=system`, `via=call`) từ kết quả `prepare_event` (đang có h1 trong request), dùng
  `ON CONFLICT DO NOTHING`. State đồ thị vẫn không mang h1.
- **(FR-009)** `GET /v1/threat-list?since=<version>` (JWT thiết bị):
  - Dựng ảnh chụp từ các dòng còn hiệu lực có `bucket_enc` (bản prod bỏ dòng `is_demo`): giải mã, dịch về
    `bucket_bits`, bỏ trùng, sắp xếp, đóng gói uint24 big-endian, mã hóa base64.
  - `version = sha256(nội dung)[:16]`; `since` trùng `version` ⇒ `304`.
  - Bộ nhớ đệm trong tiến trình 5 phút. Hạn mức 24 lần/ngày/thiết bị. `HOICON_THREAT_BUCKET_BITS` mặc định 22.
- **(FR-010)** Android đồng bộ & tra ngoại tuyến (làn A):
  - Migration Room v1→v2: xóa `threat_hashes`, thêm `threat_snapshot` (một dòng: `version`, `bucket_bits`, `count`,
    `buckets` BLOB, `fetched_at`). Xuất schema vào `app/schemas`.
  - `ThreatSyncWorker`: định kỳ 12 giờ + một lần khi mở app/ghép đôi xong (`KEEP`), cần mạng, backoff.
    - Kiểm tính hợp lệ (bits, `count × 3 == len`, đã sắp xếp); hỏng ⇒ giữ ảnh cũ.
  - `ThreatBucketIndex` (`IntArray` sắp xếp, tìm nhị phân):
    - nạp ngoài main thread khi tiến trình khởi động;
    - thay thế nguyên khối (`@Volatile`) sau mỗi lần đồng bộ;
    - chưa nạp xong ⇒ trả "không khớp" (an toàn vì máy chủ vẫn tra chính xác khi nhận sự kiện).
  - `LocalLists.isFlagged` = khớp bucket (giữ h1 demo cứng của bản debug cho `emu-scenario`).
  - Không thêm quyền Android nào.
- **(FR-011)** Android E10 (làn A):
  - Màn nhập: ô số lớn, bàn phím số. Số thô chỉ sống trong bộ nhớ màn hình; băm bằng `PhoneHasher` rồi xóa.
  - `LookupApiClient` gửi `POST /v1/lookups`.
  - `LookupResultScreen.kt` có 5 trạng thái theo token `risk.*` của DESIGN-SYSTEM, luôn kèm biểu tượng + chữ, tự đọc to
    bằng `Speaker`. Hai hành động chính: "Hỏi con" (luồng sẵn có) và "Xong".
  - Mất mạng ⇒ kết luận từ `ThreatBucketIndex`: khớp ⇒ "có thể nằm trong danh sách cảnh báo"; không khớp ⇒ "chưa kiểm
    tra được". Không bao giờ hiện "an toàn".
  - Lối vào: nút phụ trên E6 "Kiểm tra số hay đường link" (giữ ≤ 2 hành động chính của E6).
  - Màn đồng ý đúng lúc (just-in-time) ở lần dùng đầu ghi mục đích `lookups` qua `ConsentLedger`. Không buộc đồng ý lại
    các mục đích khác.
- **(FR-012)** (P3, cắt được) URL & QR:
  - Màn nhập có "Dán đường link". Máy bỏ truy vấn/mảnh/thông tin đăng nhập trước khi gửi.
  - "Quét mã QR" bằng Google Code Scanner (không xin quyền `CAMERA`; ẩn nút khi máy không có Google Play services).
  - QR là URL ⇒ tra như URL; QR là `tel:` ⇒ tra như số; QR là VietQR (EMVCo) ⇒ phân tích **trên máy**, hiện tên người
    nhận + "HỏiCon không kiểm tra được tài khoản này, hỏi con trước khi chuyển", **không gửi gì lên máy chủ**.
- **(FR-013)** Kiểm chứng & tài liệu:
  - Test: unit, contract, tích hợp, JVM `:rules`, Android unit.
  - `hoicon-eval smoke --compare baseline` (đồ thị đổi).
  - `emu-scenario.py --scenario fake_police` trên AVD API 36 **và** 34 (đường cảm biến đổi).
  - Ảnh E10 + `ux-elder-reviewer`; `security-privacy-reviewer` (PII, manifest, đồng ý).
  - Tài liệu: ADR-011 (đề xuất); cập nhật `docs/API.md`, `docs/DATA-MODEL.md`, `docs/AGENTS.md`, `docs/DESIGN-SYSTEM.md` (E10).
  - `evidence.md` có số thật; ROADMAP `P2-11` ◐ (☑ chỉ khi chạy trên máy thật hoặc Minh chấp nhận số máy ảo).

## 5. Bất biến & ranh giới

1. **ADR-006:** số thô không bao giờ rời máy. Máy chủ chỉ nhận `h1` và **không băm hộ**: "server băm tại ranh giới"
   nghĩa là số thô đã đi qua mạng, nên bị loại.
2. **ADR-001:** luật trên máy vẫn tất định. Khớp bucket chỉ là một đầu vào boolean của R1, không có mô hình trên máy.
3. **ADR-009 / luật 5:** không thêm lời gọi LLM. Mức chỉ nâng, `level ≥ rule_floor`. Gửi tin chỉ từ node đồ thị trong
   danh sách cho phép (`await_guardian`), không gửi từ router.
4. **Công khai AI:** mọi `lookup_result.disclaimer`, câu đọc to trên E10 và tin `evidence` mở đầu bằng "Đây là trợ lý AI
   HỏiCon" (có test).
5. **Android:** không thêm quyền nào (đặc biệt không `CAMERA`, SMS, call log, danh bạ, Accessibility). `minSdk 29` giữ
   nguyên. Không chặn cuộc gọi.
6. **Diễn tập/demo:** `verifications.is_demo`, tin `evidence` có nhãn `[DIỄN TẬP]` khi sự cố là diễn tập. Bản prod
   không phát chỉ báo `is_demo` xuống máy.
7. Migration đã lên `main` (`0001`…`0006`) không sửa. Chỉ thêm `0007`.

## 6. Ngoài phạm vi

Tra cứu số tài khoản (chưa có nguồn dữ liệu; `kind=account` để dành) · sổ đăng ký tên miền/tổng đài chính thức (cần nguồn
đã kiểm và Minh duyệt) · cập nhật danh sách dạng delta (ảnh chụp đầy đủ ≈ 3 byte/chỉ báo, đủ tới khoảng 100.000 chỉ báo)
· giao diện tra cứu trên web cho người giám hộ (027) · nguồn công khai bên ngoài qua mạng (không gọi API bên thứ ba)
· chuyển trạng thái `verifying`/`rescore` (cần sửa `decided_state` trước, ghi vào ROADMAP "Ghi chú").
