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
| `families` | id, display_name (bí danh do người dùng đặt), region (`bac/trung/nam`), plan, created_at, is_demo | |
| `members` | id, family_id, role (`protected/guardian`), alias (cách xưng hô: "Mẹ", "Bố"…), address_form, guardian_rank (1, 2), zalo_user_ref (HMAC), locale, created_at | không lưu tên thật |
| `devices` | id, family_id, member_id, platform, app_version, rules_version, threat_list_version, permission_state jsonb, fcm_token_enc, last_heartbeat_at, revoked_at | |
| `consents` | id, family_id, member_id, purpose, granted bool, consent_version, text_sha256, channel (`app/zalo/web`), recorded_at | **chỉ ghi thêm**: trigger chặn UPDATE/DELETE; rút đồng ý = dòng mới `granted=false` |

`purpose` (enum, thêm giá trị ⇒ văn bản đồng ý mới): `core_protection`, `call_screening`, `usage_monitoring`,
`overlay_pause`, `guardian_alerts`, `llm_processing`, `voice_input`, `drills`, `pilot_research`.

### Liên hệ & xác thực
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `trusted_contacts` | id, family_id, member_id, phone_hmac, phone_kid, last3, label | R0: không cảnh báo |
| `pairing_codes` | id, family_id, code_hash, expires_at, used_at | mã 6 số / QR, hết hạn 15 phút |
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
| `agent_runs` | id, incident_id, graph (`incident/coach`), status, thread_id, started_at, finished_at, cost_usd | checkpoint LangGraph nằm ở bảng của `AsyncPostgresSaver` |
| `agent_steps` | id, run_id, node, model_profile, model, input_redacted jsonb, output jsonb, latency_ms, tokens_in/out, cost_usd, fallback_used, at | đã che PII; nguồn cho `/trace` |

### Người giám hộ & tin nhắn
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `guardian_actions` | id, incident_id, member_id, action (`called/safe/scam/details/escalate`), channel, at | |
| `messages_out` | id, family_id, incident_id, channel (`zalo/push/web`), bot_id, template_id, status, quota_month, sent_at, error | bộ đếm hạn mức theo bot/tháng |

### Xác minh & hồ sơ
| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `verifications` | id, incident_id, kind (`phone/url/qr/account`), subject_hmac, verdict, sources jsonb, at | |
| `threat_indicators` | id, kind, value_hmac, value_kid, last3, source, confidence, first_seen, last_seen, expires_at | đồng bộ xuống máy dạng danh sách hash |
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
| `jobs` | id, kind, payload jsonb, run_at, attempts, locked_at, locked_by, done_at, error | `FOR UPDATE SKIP LOCKED` |
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
