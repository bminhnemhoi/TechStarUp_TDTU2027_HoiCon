# Mô hình dữ liệu HỏiCon

> Đặc tả trước khi viết migration (luật "hợp đồng trước"). Migration thật nằm ở `backend/migrations/`; mọi thay đổi ở
> đây phải đi kèm migration mới (migration đã lên `main` là bất biến). Schema sự kiện: `docs/schemas/`.

## 1. Quy ước

- Khóa chính `id uuid` **UUIDv7** (sắp theo thời gian). Sự kiện do **máy sinh id** ⇒ gửi lại không bị trùng (idempotent).
- Thời gian `timestamptz` (UTC); hiển thị theo `Asia/Ho_Chi_Minh`.
- Mọi bảng nghiệp vụ có `family_id` (truy vấn luôn lọc theo gia đình) và cờ `is_demo`, `is_drill` khi áp dụng.
- Enum dùng kiểu `text` + `CHECK` (dễ thêm giá trị bằng migration hơn `CREATE TYPE`).
- Không có cột chứa số điện thoại, số tài khoản, tên thật, Zalo ID, OTP ở dạng thô (xem §3).

## 2. Bảng

### Gia đình & đồng ý
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `families` | id, display_name (bí danh do người dùng đặt), region (`bac/trung/nam`), plan, created_at, is_demo | **đã có** (`0003`, spec 002); **`deleted_at`** (`0009`): tombstone sau yêu cầu xóa, `display_name` = `[đã xóa]` |
| `members` | id, family_id, role (`protected/guardian`), alias (cách xưng hô: "Mẹ", "Bố"…, rỗng được), address_form, guardian_rank (1, 2), **zalo_bot_id, zalo_user_hmac, zalo_hmac_kid, zalo_chat_enc**, locale, created_at | **đã có** (`0003`); không lưu tên thật; 4 cột Zalo cùng có hoặc cùng rỗng; unique `(family_id, guardian_rank)` cho người giám hộ, unique `(zalo_bot_id, zalo_user_hmac)`; cột Zalo theo D1 (§3b); **`deleted_at`** (`0009`): tombstone đã ẩn danh (alias `[đã xóa]`, các cột Zalo = NULL), token người giám hộ bị từ chối |
| `devices` | id, family_id, member_id, platform, label, app_version, rules_version, threat_list_version, permission_state jsonb, fcm_token_enc, device_secret_hash, last_heartbeat_at, revoked_at, created_at | **đã có** (`0005`, spec 020); tạo khi ghép đôi; `device_secret_hash` = SHA-256 của refresh token (unique, không lưu token thô); `label` = bí danh máy, không PII; FK gia đình/thành viên `CASCADE` |
| `consents` | id, family_id, member_id, purpose, granted bool, consent_version, text_sha256, channel (`app/zalo/web`), recorded_at | **đã có** (`0005`); **chỉ ghi thêm**: trigger `trg_consents_immutable` (UPDATE/DELETE, mỗi dòng) và `trg_consents_no_truncate` (TRUNCATE) cùng gọi `prevent_consent_tamper()` ⇒ ném lỗi (bật `ENABLE ALWAYS`: vẫn chạy khi `session_replication_role = replica`; chủ bảng/superuser vẫn tắt được ⇒ prod nên tách role ứng dụng chỉ có INSERT/SELECT); `downgrade` từ chối khi còn dòng; rút đồng ý = dòng mới `granted=false`; FK `RESTRICT` (xóa gia đình/thành viên không kéo theo xóa bằng chứng; muốn xóa cần thủ tục riêng có người duyệt, tắt trigger trong một giao dịch); `text_sha256` là 64 hex thường |

`purpose` (enum, thêm giá trị ⇒ văn bản đồng ý mới): `core_protection`, `call_screening`, `usage_monitoring`,
`overlay_pause`, `guardian_alerts`, `llm_processing`, `voice_input`, `drills`, `pilot_research`, `lookups` (`0007`, spec 026:
tra số/đường link do người dùng tự nhập; `downgrade` dựng lại CHECK cũ bằng `NOT VALID` vì sổ chỉ-ghi-thêm không xóa được dòng `lookups`).

### Liên hệ & xác thực
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `trusted_contacts` | id, family_id, member_id, phone_hmac, phone_kid, last3, label, created_at | **đã có** (`0005`, chưa có API); R0: không cảnh báo; chỉ HMAC + 3 số cuối, CHECK 64 hex |
| `pairing_codes` | id, family_id, code_hash, expires_at, used_at | **đã có** (`0003`); mã 6 số / QR, hết hạn 15 phút; chỉ lưu `HMAC(pepper, "hoicon:pairing:v1:"+mã)`; unique trên `code_hash` khi `used_at IS NULL` |
| `action_tokens` | id, incident_id, member_id, token_hash, scope, expires_at, used_at, created_at | **đã có** (`0005`, chưa có API); magic link `/a/[token]`; chỉ lưu băm (unique); `scope` ∈ `incident_decision/guardian_view/drill_debrief`; `incident_id` FK tới `incidents` (CASCADE, từ `0006`) |

### Sự kiện & sự cố
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `risk_events` | id (từ máy, khóa chính ⇒ chống trùng), family_id, device_id, incident_id (SET NULL), type, rule_id, rule_floor, occurred_at, received_at, caller_hmac, caller_kid, caller_last3, caller_in_contacts, call_duration_s, app_category, app_package, timing_detect_ms, timing_pause_ms, is_drill, drill_id, payload (JSONB, đã bỏ `caller.h1`) | **đã có** (`0006`); **chỉ siêu dữ liệu** — không nội dung cuộc gọi, không h1; CHECK enum/hex/độ dài, `caller_hmac`/`caller_kid`/`caller_last3` cùng có hoặc cùng không; index `(device_id, received_at)`, `(incident_id)`, `(received_at)` cho job `retention` |
| `incidents` | id, family_id, member_id, device_id (SET NULL), state, level, rule_floor, version (khóa lạc quan), is_drill, drill_id, is_demo, opened_by_event_id (SET NULL), outcome, opened_at, closed_at | **đã có** (`0006`); CHECK `level >= rule_floor` (`ck_incidents_level_ge_floor`), `closed_at` có giá trị ⇔ trạng thái cuối, diễn tập phải có `drill_id`; trigger `trg_incidents_terminal` (`ENABLE ALWAYS`) chặn rời trạng thái cuối và biến sự cố đã kết thúc thành chỉ-đọc (`state/level/rule_floor/outcome/closed_at`); index `(family_id, opened_at DESC)` và partial `(device_id) WHERE chưa kết thúc` |
| `incident_transitions` | id, incident_id (CASCADE), from_state, to_state, actor (`device/agent/guardian/timer/system`), reason (≤ 256, mã do máy chủ đặt), at | **đã có** (`0006`); ghi mọi chuyển trạng thái, chỉ thêm dòng (trigger `trg_incident_transitions_immutable` chặn UPDATE và DELETE trực tiếp; DELETE do CASCADE khi xóa sự cố/gia đình vẫn qua; `TRUNCATE` và quyền DDL chưa chặn — prod nên thu quyền của role ứng dụng, xem `consents`); index `(incident_id, at)` |

### Tác tử
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `agent_runs` | id, incident_id, graph (`incident/coach`), status (`running/waiting/done/failed`), thread_id, started_at, finished_at, cost_usd, is_drill, is_demo | **đã có** (migration `0002`, P1-S4); FK `incident_id` thêm ở P2-03; checkpoint LangGraph nằm ở bảng của `AsyncPostgresSaver` |
| `agent_steps` | id, run_id, node, model_profile, model, prompt_version, input_redacted jsonb, output jsonb, latency_ms, tokens_in/out, cost_usd, fallback_used, error, at | **đã có** (`0002`); đã che PII; nguồn cho `/trace` |

### Người giám hộ & tin nhắn
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `guardian_actions` | id, incident_id, member_id, action (`called/safe/scam/details/escalate`), channel, at | |
| `messages_out` | id, family_id (rỗng được), incident_id (FK `incidents`, SET NULL từ `0006`), **member_id**, channel (`zalo/push/web`), bot_id, template_id, status (`queued/sent/held_quota/failed/fallback_required`), quota_month (`YYYY-MM` giờ Việt Nam), sent_at, error, **job_key** (unique ⇒ gửi đúng một lần), created_at | **đã có** (`0003`); bộ đếm hạn mức theo bot/tháng (index `bot_id, quota_month, status`); `family_id` rỗng vì tin trả lời người chưa ghép vẫn tính hạn mức (ADR-010) |

### Xác minh & hồ sơ
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `verifications` | id, family_id (FK `CASCADE`), incident_id (FK `incidents` `CASCADE`, rỗng được), actor (`device/guardian/system`), actor_id, kind (`phone/url/account`), via (`typed/qr/call`), subject_kid, subject_hmac (CHECK hex 64), last3 (chỉ phone), verdict (`safe/warning/dangerous/unknown`), confidence (0–1), sources jsonb, list_version, is_demo, at | **đã có** (`0007`, spec 026); chỉ HMAC của chủ thể (phone: `HMAC(pepper, h1)`; url: `HMAC(pepper, SHA-256("hoicon:url:v1:" + host))`, đường dẫn/truy vấn/thông tin đăng nhập bỏ ngay); không cột nào chứa số thô, h1 hay URL. Chỉ mục `(actor_id, at)` đếm hạn mức `POST /v1/lookups`, `(incident_id)`, UNIQUE một phần `(incident_id, kind, subject_kid, subject_hmac) WHERE via = 'call'` để ghi số gọi đến lũy đẳng. Giữ 90 ngày như sự cố (job `retention`, P2-20 — chưa có; **nợ**: chưa có job xóa theo hạn, chưa xóa/ẩn danh khi rút đồng ý `lookups`) |
| `threat_indicators` | id, kind (`phone`), value_hmac (char 64, CHECK hex), value_kid, last3 (char 3, rỗng được), source, confidence (0–1), tactic, list_version, is_demo, first_seen, last_seen, expires_at | **đã có** (`0004`, spec 003); chỉ HMAC (ADR-006), không cột h1; `UNIQUE (kind, value_kid, value_hmac)` cũng là chỉ mục tra cứu; nạp bằng `ops/threat_list`. **Cột `bucket_enc`** (`0007`, spec 026, ADR-011 *Đề xuất*): bucket 24 bit đầu của h1, MÃ HÓA AES-256-GCM (`"<kid>." + base64url(nonce ‖ bản mã)`, AAD `hoicon:threat:bucket:v1:<kid>:<value_hmac>` nên tráo bản mã giữa hai dòng làm giải mã hỏng); không bao giờ lưu bucket dạng rõ cạnh `last3`. Ảnh chụp bucket cho máy dựng từ cột này (`GET /v1/threat-list`); dòng cũ thiếu `bucket_enc` không xuống máy cho tới khi nạp lại tệp seed (`ops/threat_list` in số dòng còn thiếu) |
| `case_files` | id, incident_id, status (`draft/approved/sent`), content jsonb, approved_by, approved_at | hồ sơ gửi cơ quan sau khi người giám hộ duyệt |

### Diễn tập & đánh giá
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `scenarios` | id, slug, tactic, region, version, yaml_sha256 | nguồn: `data/scenarios/*.yaml` |
| `drills` | id, family_id (FK `CASCADE`), member_id (FK `CASCADE`), scheduled_by, script_id, window_start, window_end, status (`scheduled/offered/in_progress/passed/failed/aborted/declined/expired`), score, answers jsonb, offered_at, started_at, completed_at, debriefed_at, is_demo, created_at | **đã có** (`0008`, spec 028); CHECK status và CHECK khung giờ 30m–4h; chỉ mục `(family_id, window_start)`; không lưu văn bản tự do, answers chỉ chứa mã choice_id. |
| `eval_runs` / `eval_results` | suite, baseline, metrics jsonb / case_id, expected, actual, passed, safety_violations | |

### Vận hành & quyền dữ liệu
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `jobs` | id, kind, payload jsonb, run_at, idempotency_key (unique), attempts, locked_at, locked_by, done_at, error, created_at | **đã có** (`0002`); `FOR UPDATE SKIP LOCKED`; khóa chống trùng khi node chạy lại (ADR-009) |
| `demo_sessions` | id, code, created_at, expires_at | dữ liệu demo tự xóa sau 24 giờ |
| `device_heartbeats` | device_id (FK `devices` `CASCADE`), slot (mốc 15 phút, CHECK chia hết 900 giây), protected bool; PK `(device_id, slot)` | **đã có** (`0010`, spec 029); tối đa 96 dòng/ngày/thiết bị; đo độ phủ heartbeat cho Gate M2 (`ops pilot report`); không văn bản tự do, không định danh; giữ 90 ngày (§6) |
| `data_requests` | id, family_id (FK `RESTRICT`: vết pháp lý còn lại sau khi xóa), kind (`delete`; `export` để dành), requested_via (`ops/app/web`), status (`pending/done/failed`), error_code (≤ 32, mã do máy chủ đặt), requested_at, completed_at | **đã có** (`0009`, spec 034); quyền chủ thể dữ liệu (Luật 91/2025); CHECK `(status = 'done') = (completed_at IS NOT NULL)`; không cột văn bản tự do |

## 3. Băm số điện thoại / số tài khoản (ADR-006)

```
Thiết bị:  e164 = PhoneHasher.toE164("09…")         # :rules — vector dùng chung docs/schemas/fixtures/h1_vectors.json
           h1   = SHA-256("hoicon:v1:" + e164)      # chỉ h1 + last3 rời máy
Máy chủ:   phone_hmac = HMAC-SHA256(pepper[kid], h1);  lưu phone_hmac, phone_kid, last3
```
- `pepper[kid]` nằm ngoài DB (biến môi trường / `D:\secrets`), có `kid` để xoay vòng.
- Danh sách đe dọa gửi xuống máy dạng tập `h1` (máy so khớp cục bộ) — máy chủ không biết máy đang so khớp số nào.
- Số tài khoản ngân hàng: cùng cách, tiền tố `"hoicon:acct:v1:"`.

## 3b. Định danh Zalo của người giám hộ (ADR-010 D1)

```
user_hmac = HMAC-SHA256(pepper[kid], "hoicon:zalo:v1:" + bot_id + ":" + user_id)    # members.zalo_user_hmac (+ zalo_hmac_kid)
chat_enc  = "<kid>." + base64url(nonce12 ‖ AES-256-GCM(chat_id, key[kid], aad="hoicon:zalo:chat:v1:<kid>"))   # members.zalo_chat_enc
```
- Không có cột Zalo ID thô, tên hiển thị hay văn bản người giám hộ gõ. `chat_enc` chỉ giải mã lúc gọi Zalo.
- Khóa `HOICON_DATA_KEY_<kid>` (hex 64 ký tự) nằm ngoài DB, sinh bằng `init_env`; **mất khóa ⇒ phải ghép lại** mọi người giám hộ.
- Job `zalo_update` (webhook xếp) chỉ mang `user_hmac`, `chat_enc`, loại lệnh và băm mã/lựa chọn đã phân loại.

## 4. Máy trạng thái sự cố

```
detected → assessing → awaiting_guardian ──(T1 = 2' nhắc; T2 = 5' chuyển người giám hộ 2)──┐
                │                │                                                          │
                │                └──► verifying → rescore ─┐                                 │
                └────────────────────────────────────────── ├─► resolved_{safe|prevented|false_alarm|no_response}
                                                            └─► case_open → closed
```
- Mọi chuyển trạng thái qua `IncidentService.transition(incident_id, to, actor, reason, expected_version)` — ghi
  `incident_transitions`, tăng `version`, giữ `pg_advisory_xact_lock(incident_id)` để thao tác người giám hộ và bộ hẹn
  giờ không giẫm nhau.
- **Bất biến 1:** `incidents.level >= incidents.rule_floor` ở mọi thời điểm (CHECK + test).
- **Bất biến 2:** trạng thái cuối (`resolved_*`, `closed`) không quay lại; mở lại = sự cố mới liên kết.
- Cạnh hợp lệ (`IncidentService.ALLOWED`): `detected→assessing`; `assessing→awaiting_guardian|resolved_*`; `awaiting_guardian→verifying|case_open|resolved_*`; `verifying→rescore`; `rescore→case_open|resolved_*`; `case_open→closed`. `resolved_*` và `closed` không có cạnh đi ra.
- `transition(..., expected_version)`: `ConcurrencyConflictError` nếu `version` đã đổi (người giám hộ so với bộ hẹn giờ); `InvalidTransitionError` nếu cạnh không hợp lệ. Service không commit — người gọi sở hữu giao dịch.
- **Nâng mức** (sự kiện sau có `rule_floor` cao hơn) chỉ nâng `rule_floor` + `level` và tăng `version`, không ghi `incident_transitions` (trạng thái không đổi).

## 5. Trên máy (Android)

- Room `sentinel.db`: `outbox` (sự kiện chờ gửi, id UUIDv7), `threat_hashes` (tập h1 + phiên bản), `risk_window`
  (trạng thái cửa sổ hiện tại), `trusted_contacts` (h1 + last3, mã hóa Tink AEAD).
- DataStore mã hóa Tink: token thiết bị, cấu hình, phiên bản đồng ý đã chấp nhận.
- `android:allowBackup="false"`, `dataExtractionRules` loại trừ toàn bộ — không sao lưu lên đám mây.

## 6. Hạn lưu

Thực thi bằng job `retention` hằng ngày (`services/retention_service.py`, hằng số `RETENTION`; spec 034). Mỗi loại xử lý
theo lô ≤ 1.000 dòng, mỗi lô một giao dịch, lũy đẳng; `python -m hoicon.ops.data retention --dry-run` in số dòng sẽ bị
đụng mà không ghi. Test `test_retention.py` so khớp bảng này với `RETENTION`.

| Dữ liệu | Hạn | Cơ chế |
|---|---|---|
| `risk_events` | 90 ngày | job `retention` hằng ngày (từ `received_at`) |
| `agent_steps.input_redacted/output` | 30 ngày (giữ số đo) | job `retention` làm rỗng, giữ dòng và `latency`/`tokens`/`cost` |
| `incidents` + transitions | 12 tháng | job `retention` xóa sự cố đã đóng (từ `closed_at`), CASCADE nhật ký chuyển, xác minh, token |
| Dữ liệu demo | 24 giờ | `demo_sessions.expires_at` |
| `consents` | suốt thời gian dịch vụ + 2 năm | không xóa (bằng chứng đồng ý, Nghị định 356/2025); xóa gia đình chỉ ẩn danh `families`/`members` |
| Giọng nói | không lưu trên máy chủ | STT xử lý luồng rồi bỏ |
| Lời kể tự do của người cao tuổi | **không lưu** | chỉ giữ cờ tất định `note_flags` (ADR-009) |
| Checkpoint LangGraph (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) | sự cố đóng + 7 ngày | job `retention` gọi `adelete_thread`; `agent_steps` đủ cho trace |
| `jobs` (gồm `payload.text` = toàn văn tin gửi người giám hộ) | 30 ngày sau `done_at` | job `retention` |
| `messages_out` | giữ dòng (không có cột văn bản) | đếm hạn mức Zalo theo tháng; toàn văn tin nằm ở `jobs.payload` và đi theo hạn của `jobs` |
| `action_tokens` | 30 ngày sau `expires_at` | job `retention` |
| `verifications` | 90 ngày | job `retention` (từ `at`) |
| `drills` | 12 tháng | job `retention` (từ `created_at`) |
| `device_heartbeats` | 90 ngày | job `retention` (từ `slot`, spec 029) |
| Nhật ký proxy/ứng dụng (Caddy, uvicorn; có IP khách, token đã che) | tối đa 5 × 10 MB mỗi dịch vụ | driver log Docker `json-file` (`max-size`/`max-file`) tự xóa bản cũ; hạn theo dung lượng, không theo ngày (spec 012 T019) |
| `data_requests` | giữ | vết pháp lý của yêu cầu xóa dữ liệu (không có văn bản tự do) |

### Xóa dữ liệu gia đình theo yêu cầu (spec 034)

`python -m hoicon.ops.data request-delete --family <id>` ghi `data_requests` và xếp job `purge_family`: thu hồi thiết bị,
xóa checkpoint, xóa mọi dữ liệu nghiệp vụ của gia đình, rồi **ẩn danh** `members` (bí danh `[đã xóa]`, HMAC Zalo và bản mã
định danh = NULL) và `families` (`display_name = [đã xóa]`); `deleted_at` đánh dấu tombstone. `consents` giữ nguyên vì
FK RESTRICT và luật. Mục tiêu hoàn tất ≤ 72 giờ (thực tế: ngay khi worker nhận job).
