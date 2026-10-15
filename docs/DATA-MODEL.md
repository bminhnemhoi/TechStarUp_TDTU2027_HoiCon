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
| `families` | id, display_name (bí danh do người dùng đặt), region (`bac/trung/nam`), plan, created_at, is_demo | **đã có** (`0003`, spec 002) |
| `members` | id, family_id, role (`protected/guardian`), alias (cách xưng hô: "Mẹ", "Bố"…, rỗng được), address_form, guardian_rank (1, 2), **zalo_bot_id, zalo_user_hmac, zalo_hmac_kid, zalo_chat_enc**, locale, created_at | **đã có** (`0003`); không lưu tên thật; 4 cột Zalo cùng có hoặc cùng rỗng; unique `(family_id, guardian_rank)` cho người giám hộ, unique `(zalo_bot_id, zalo_user_hmac)`; cột Zalo theo D1 (§3b) |
| `devices` | id, family_id, member_id, platform, app_version, rules_version, threat_list_version, permission_state jsonb, fcm_token_enc, last_heartbeat_at, revoked_at | |
| `consents` | id, family_id, member_id, purpose, granted bool, consent_version, text_sha256, channel (`app/zalo/web`), recorded_at | **chỉ ghi thêm**: trigger chặn UPDATE/DELETE; rút đồng ý = dòng mới `granted=false` |

`purpose` (enum, thêm giá trị ⇒ văn bản đồng ý mới): `core_protection`, `call_screening`, `usage_monitoring`,
`overlay_pause`, `guardian_alerts`, `llm_processing`, `voice_input`, `drills`, `pilot_research`.

### Liên hệ & xác thực
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `trusted_contacts` | id, family_id, member_id, phone_hmac, phone_kid, last3, label | R0: không cảnh báo |
| `pairing_codes` | id, family_id, code_hash, expires_at, used_at | **đã có** (`0003`); mã 6 số / QR, hết hạn 15 phút; chỉ lưu `HMAC(pepper, "hoicon:pairing:v1:"+mã)`; unique trên `code_hash` khi `used_at IS NULL` |
| `action_tokens` | id, incident_id, member_id, token_hash, scope, expires_at, used_at | magic link `/a/[token]` |

### Sự kiện & sự cố
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `risk_events` | id (từ máy), family_id, device_id, type, rule_id, rule_floor, caller_hmac, caller_last3, caller_in_contacts, call_duration_s, app_category, occurred_at, received_at, is_drill | **chỉ siêu dữ liệu** — không nội dung cuộc gọi |
| `incidents` | id, family_id, state, level, rule_floor, opened_by_event_id, outcome, version (khóa lạc quan), opened_at, closed_at, is_drill, is_demo | |
| `incident_transitions` | id, incident_id, from_state, to_state, actor (`device/agent/guardian/timer/system`), reason, at | ghi mọi chuyển trạng thái |

### Tác tử
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `agent_runs` | id, incident_id, graph (`incident/coach`), status (`running/waiting/done/failed`), thread_id, started_at, finished_at, cost_usd, is_drill, is_demo | **đã có** (migration `0002`, P1-S4); FK `incident_id` thêm ở P2-03; checkpoint LangGraph nằm ở bảng của `AsyncPostgresSaver` |
| `agent_steps` | id, run_id, node, model_profile, model, prompt_version, input_redacted jsonb, output jsonb, latency_ms, tokens_in/out, cost_usd, fallback_used, error, at | **đã có** (`0002`); đã che PII; nguồn cho `/trace` |

### Người giám hộ & tin nhắn
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `guardian_actions` | id, incident_id, member_id, action (`called/safe/scam/details/escalate`), channel, at | |
| `messages_out` | id, family_id (rỗng được), incident_id (chưa có FK tới `incidents`), **member_id**, channel (`zalo/push/web`), bot_id, template_id, status (`queued/sent/held_quota/failed/fallback_required`), quota_month (`YYYY-MM` giờ Việt Nam), sent_at, error, **job_key** (unique ⇒ gửi đúng một lần), created_at | **đã có** (`0003`); bộ đếm hạn mức theo bot/tháng (index `bot_id, quota_month, status`); `family_id` rỗng vì tin trả lời người chưa ghép vẫn tính hạn mức (ADR-010) |

### Xác minh & hồ sơ
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `verifications` | id, incident_id, kind (`phone/url/qr/account`), subject_hmac, verdict, sources jsonb, at | |
| `threat_indicators` | id, kind (`phone`), value_hmac (char 64, CHECK hex), value_kid, last3 (char 3, rỗng được), source, confidence (0–1), tactic, list_version, is_demo, first_seen, last_seen, expires_at | **đã có** (`0004`, spec 003); chỉ HMAC (ADR-006), không cột h1; `UNIQUE (kind, value_kid, value_hmac)` cũng là chỉ mục tra cứu; nạp bằng `ops/threat_list`. **Chưa đồng bộ xuống máy được**: máy so **h1** mà bảng chỉ có HMAC ⇒ 022/026 phải chọn (cột `value_enc` AES-GCM hoặc danh sách h1 tách khỏi DB) |
| `case_files` | id, incident_id, status (`draft/approved/sent`), content jsonb, approved_by, approved_at | hồ sơ gửi cơ quan sau khi người giám hộ duyệt |

### Diễn tập & đánh giá
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `scenarios` | id, slug, tactic, region, version, yaml_sha256 | nguồn: `data/scenarios/*.yaml` |
| `drills` | id, family_id, scenario_id, scheduled_for, window, result (`passed/failed/aborted`), debriefed_at | luôn `is_drill` |
| `eval_runs` / `eval_results` | suite, baseline, metrics jsonb / case_id, expected, actual, passed, safety_violations | |

### Vận hành & quyền dữ liệu
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `jobs` | id, kind, payload jsonb, run_at, idempotency_key (unique), attempts, locked_at, locked_by, done_at, error, created_at | **đã có** (`0002`); `FOR UPDATE SKIP LOCKED`; khóa chống trùng khi node chạy lại (ADR-009) |
| `demo_sessions` | id, code, created_at, expires_at | dữ liệu demo tự xóa sau 24 giờ |
| `data_requests` | id, family_id, kind (`export/delete`), status, requested_at, completed_at | quyền chủ thể dữ liệu (Luật 91/2025) |

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

## 5. Trên máy (Android)

- Room `sentinel.db`: `outbox` (sự kiện chờ gửi, id UUIDv7), `threat_hashes` (tập h1 + phiên bản), `risk_window`
  (trạng thái cửa sổ hiện tại), `trusted_contacts` (h1 + last3, mã hóa Tink AEAD).
- DataStore mã hóa Tink: token thiết bị, cấu hình, phiên bản đồng ý đã chấp nhận.
- `android:allowBackup="false"`, `dataExtractionRules` loại trừ toàn bộ — không sao lưu lên đám mây.

## 6. Hạn lưu

| Dữ liệu | Hạn | Cơ chế |
|---|---|---|
| `risk_events` | 90 ngày | job `retention` hằng ngày |
| `agent_steps.input_redacted/output` | 30 ngày (giữ số đo) | job `retention` |
| `incidents` + transitions | 12 tháng | job `retention` |
| Dữ liệu demo | 24 giờ | `demo_sessions.expires_at` |
| `consents` | suốt thời gian dịch vụ + 2 năm | không xóa (bằng chứng đồng ý, Nghị định 356/2025) |
| Giọng nói | không lưu trên máy chủ | STT xử lý luồng rồi bỏ |
| Lời kể tự do của người cao tuổi | **không lưu** | chỉ giữ cờ tất định `note_flags` (ADR-009) |
| Checkpoint LangGraph (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`) | sự cố đóng + 7 ngày | job `retention` gọi `adelete_thread` (P2-20); `agent_steps` đủ cho trace |
| `jobs` (gồm `payload.text` = toàn văn tin gửi người giám hộ) | 30 ngày sau `done_at` | job `retention` (P2-20) |
