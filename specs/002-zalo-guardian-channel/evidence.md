# Bằng chứng nghiệm thu: Kênh Zalo cho người giám hộ (spike P1-S3)

**Spec**: `specs/002-zalo-guardian-channel/spec.md` · **Mã ROADMAP**: P1-S3 · **Nhánh/PR**: feat/002-zalo-guardian-channel · chưa có PR (chưa commit) · **Ngày**: 15/10/2026

**Trạng thái tổng**: code + test hoàn tất ở chế độ **mock**. **Chưa nghiệm thu xong**: SC-001 và T024/T025 **BLOCKED: chờ token bot thật (W0-3)**.
Spec **chưa** được đánh dấu hoàn thành ở ROADMAP. D1/D2 (ADR-010) do **Tiến duyệt 15/10/2026**; Minh xác nhận lại ở PR.

## Tiêu chí thành công (SC) ↔ số đo

| SC | Ngưỡng | Đo được | Môi trường (máy ảo / FTL / máy thật, n) | Đạt? | Bằng chứng |
|---|---|---|---|---|---|
| SC-001 | p95 ≤ 5 000 ms xếp tin → Zalo xác nhận; n ≥ 20 + ≥ 5 lần bấm giờ tới điện thoại | **BLOCKED: chờ token bot thật (W0-3)** — chưa đo. Chỉ có số MOCK phần máy chủ (KHÔNG phải bằng chứng SC-001): p50 6,6 ms / p95 8,3 ms (n=20) khi gọi thẳng; ~27–190 ms khi qua worker (`spike demo`) | bot dev thật: chưa có; số mock: máy dev Linux, Postgres 17 (Docker), n=20 | **BLOCKED (không ☑)** | `docs/spikes/P1-S3-zalo.md` §3; đo thật bằng `spike demo --family <tên>` ≥ 20 lần khi có token |
| SC-002 | toàn bộ test tính năng chạy mock, không token, < 60 s | 248 test Zalo xanh trong 6,3 s; toàn bộ backend 350 test trong 12,3 s; 0 skipped | máy dev Linux, Postgres 17 (Docker) bật, không token | Đạt | `uv run --directory backend pytest` (tập Zalo: 17 tệp test) |
| SC-003 | 0 lần token/định danh Zalo thô trong log, output test, bảng DB | 0. `test_zalo_no_leak.py` chạy cả luồng bằng client thật qua transport giả, token/khóa/ID/tên/mã "canary", log DEBUG + `httpx` INFO, stdout, 5 bảng ⇒ không thấy; không có cột ID thô; `privacy-audit`: 0 số điện thoại thô trong `backend/src`, 0 dòng khớp trong `messages_out`/`members`/`jobs`(zalo)/`agent_steps` | Postgres dev 15432, n = 1 luồng đầy đủ (3 cập nhật + 2 tin gửi + 1 lỗi 500) | Đạt | `tests/integration/test_zalo_no_leak.py`; `rg` + truy vấn SQL theo skill `privacy-audit` §1–§2 (không tạo `phase-reports`, chưa tới gate) |
| SC-004 | cùng cập nhật gửi 5 lần ⇒ xử lý 1 lần | 5 × HTTP 200, đúng 1 job `zalo_update`; handler chạy lại 3 lần ⇒ 1 người ghép, 1 tin trả lời | Postgres dev, n = 5 lần gửi lại | Đạt | `test_same_update_sent_five_times_is_processed_once`, `test_redelivered_update_pairs_once_and_replies_once` |
| SC-005 | secret sai/thiếu ⇒ 100% từ chối, 0 job | 6 biến thể (thiếu, rỗng, sai, thừa/thiếu ký tự, khác hoa-thường) ⇒ 401, 0 job; chưa cấu hình/ngắn/dài quá ⇒ 503, 0 job | Postgres dev, n = 6 + 3 | Đạt | `test_wrong_or_missing_secret_is_rejected_and_queues_nothing`, `test_webhook_not_configured_fails_closed`, `test_webhook_with_a_too_short_secret_fails_closed` |
| SC-006 | 100% tin gửi đi mở đầu bằng câu công khai AI | Mọi mẫu (cảnh báo, nhắc, chuyển hạng, trả lời `/start`, xác nhận, chi tiết, đóng) có test; cổng `deliver` **từ chối** mọi tin thiếu câu công khai (`failed`/`no_ai_disclosure`) nên không có đường lọt | mọi mẫu × diễn tập/không; cổng kiểm ở mọi tin gửi | Đạt | `test_texts_zalo.py`, `test_message_without_ai_disclosure_is_refused_at_the_gate` |
| SC-007 | ≥ 95% hạn mức: 100% tin không khẩn bị giữ, 100% tin sự cố vẫn gửi | Hạn mức test 20: ở 19/20 tin không khẩn ⇒ `held_quota` (0 lần gọi Zalo), tin sự cố ⇒ `sent`; hết hạn ⇒ `fallback_required`; cảnh báo 80% đúng 1 lần; sang tháng mới đếm lại; tin lặp lại được không bị coi là khẩn | Postgres dev, hạn mức giả 20 (mặc định thật 3.000 ⇒ 2.400/2.850) | Đạt | `tests/integration/test_quota.py`, `test_repeatable_replies_are_not_urgent…` |
| SC-008 | mã quá 15 phút hoặc đã dùng ⇒ 100% bị từ chối | Mã sai/hết hạn/đã dùng/không kèm mã đều nhận cùng một câu, 0 người được ghép, mã không bị tiêu thụ; mã đúng nhưng vượt giới hạn thử cũng bị từ chối | Postgres dev, n = 4 loại mã + 2 kịch bản giới hạn | Đạt | `test_bad_codes_all_get_the_same_generic_reply_and_reveal_nothing`, `test_expired_code_stays_rejected…`, `test_too_many_start_attempts…` |

Ngoài SC: webhook trả lời (kiểm secret + thu gọn + insert job) p50 2,5 ms / p95 4,3 ms (n=50, trong tiến trình qua ASGI, Postgres dev; **không** gồm mạng/đường hầm) — mục tiêu plan ≤ 300 ms.

## Yêu cầu chức năng (FR) ↔ test

| FR | Test / cách kiểm | Kết quả |
|---|---|---|
| FR-001 | `test_zalo_webhook.py` (secret, so sánh hằng thời gian, 401/404/503, app con không phơi /docs…) | Đạt |
| FR-002 | `test_same_update_sent_five_times_is_processed_once`, `test_database_failure_returns_503…`, đo p95 4,3 ms | Đạt |
| FR-003 | `test_pairing.py` (hạng, mã 15 phút/một lần, không lộ mã, đua hai người, giới hạn lần thử) | Đạt |
| FR-004 | `test_ops_pairing_code.py` (mã chỉ lưu băm, 15 phút, từ chối gia đình thật/prod, thu hồi mã cũ) | Đạt |
| FR-005 | `test_notify_guardian.py` (đúng hạng, một lần, một client duy nhất, `messages_out`) | Đạt |
| FR-006 | `test_texts_zalo.py`, `test_drill_label_survives…`, cổng `deliver` ép câu công khai + nhãn diễn tập | Đạt |
| FR-007 | `test_quota.py` (80/95/100%, tháng mới, theo bot) — "cảnh báo đội" = log WARNING (plan R3; kênh cảnh báo đội thật ở spec 034) | Đạt |
| FR-008 | `test_permanent_error_needs_fallback…`, `test_transient_error_on_last_attempt…`, `test_missing_guardian_or_zalo…` | Đạt |
| FR-009 | `test_guardian_reply.py` (1 ⇒ safe, 2 ⇒ scam, 3 ⇒ chi tiết, không hiểu ⇒ hướng dẫn, đến muộn, hạng 2). **Không có nút bấm** (tài liệu Zalo) nên chỉ chữ 1/2/3 | Đạt (không có nút: do nền tảng) |
| FR-010 | `test_zalo_no_leak.py`, `test_schema_0003.py` (không cột ID thô), `test_pii_zalo.py` (AES-GCM, HMAC, bản mã gắn chủ), job không mang chữ thô + scrub sau xử lý | Đạt |
| FR-011 | `test_zalo_client.py` (lỗi không mang URL/token, lọc log), `test_zalo_webhook_ops.py`, `test_zalo_no_leak.py` | Đạt |
| FR-012 | `MockZaloClient` mặc định, `build_zalo_client` (live thiếu token ⇒ lỗi; mock bị từ chối ngoài dev/test), `zalo_simulate` | Đạt |
| FR-013 | `test_zalo_webhook_ops.py` (set/info/delete chỉ in Đạt/Lỗi), `test_tunnel_app_exposes_only_the_webhook_route`, chạy thật `uvicorn hoicon.api.webhooks:app` (404 cho /docs, /openapi.json, /healthz, /mcp) | Đạt |
| FR-014 | `test_demo_incident_never_reaches_a_real_family`, `test_real_incident_never_reaches_a_demo_family_either`, `test_drill_incident_message_without_the_drill_label_is_refused` | Đạt |
| FR-015 | `docs/spikes/P1-S3-zalo.md` (tra tài liệu, hạn mức, điều khoản, nút bấm, dự phòng) + ADR-010 (D1/D2, điều chỉnh, rủi ro còn lại). **Thiếu số đo thật và hạn mức đo thật** | **Một phần — BLOCKED token (T024/T025)** |

## Cổng các tầng (lệnh đã chạy)

| Tầng | Lệnh | Kết quả |
|---|---|---|
| Backend | `uv run --directory backend ruff check . && uv run --directory backend ruff format --check . && uv run --directory backend pytest` | ruff sạch · 77 tệp đúng định dạng · **350 passed, 0 skipped** (Postgres dev bật) |
| Migration | `alembic upgrade head` → `downgrade -1` → `upgrade head` (0003); `alembic check` | chạy 2 chiều; 4 bảng mới + `ix_jobs_kind_created` không lệch với model (còn lệch cũ: bảng checkpoint LangGraph, ngoài Alembic) |
| Lock | `uv lock --check --directory backend` | đạt (`httpx`, `cryptography` khai báo trực tiếp; `revision` lock giữ 3) |
| Android | `apps/android/gradlew -p apps/android :rules:test :app:lintDebug` | **SKIPPED** — làn B, spec không đụng `apps/android/**` |
| Web | `pnpm --dir apps/web typecheck && pnpm --dir apps/web lint` | **SKIPPED** — không đụng `apps/web`; không có endpoint `/v1` mới nên không sinh lại client TS |
| Hook | `node --test ".claude/hooks/test/*.test.mjs"` | **SKIPPED** — không đụng `.claude/` |
| Máy ảo | `python scripts/emu-scenario.py …` | **SKIPPED** — không đụng cảm biến Android |
| Eval | `run-eval smoke` | **UNAVAILABLE** — CLI `hoicon-eval` chưa có (P2-15). Prompt LLM không đổi; chỉ thêm `family_id` vào đồ thị và đổi câu chữ mẫu tin (bộ test mẫu tin/đồ thị xanh) |
| Truy vết | `python3 scripts/check-spec-trace.py` | 0 lỗi (spec chưa tick hết nên chưa bị buộc có SC đủ cột; vẫn điền đủ) |
| Chạy thật | `pairing_code` → `zalo_simulate "/start <mã>"` → `spike demo --family …` trên Postgres dev (khóa giả, LLM tắt) | ghép đúng, 4 tin cảnh báo (3 `sent`/mock, hạng 2 chưa ghép ⇒ `fallback_required`), outcome `resolved_prevented`; đã dọn dữ liệu thử |

## Review

| Reviewer | Kết quả | Đã xử lý |
|---|---|---|
| `security-privacy-reviewer` | Vòng 1: **1 Cao**, 5 Trung bình, 9 Thấp. Vòng 2 (sau sửa): **0 Cao**; còn 2 Trung bình mở một phần + 4 mục mới (1 TB, 3 Thấp) | Cao (mock âm thầm không gửi) ⇒ từ chối mock ngoài dev/test, cảnh báo log, `messages_out.error='mock'`, `/readyz` báo `zalo_mode`. Đã sửa: chống dò mã (theo Zalo + theo bot + một mã/gia đình), tin lặp lại không khẩn + im lặng sau 10 tin/giờ, nhãn diễn tập theo `agent_runs`, `init_env --new-data-key`, scrub `chat_enc`/`code_hash`, bản mã gắn chủ (AAD), demo↔thật hai chiều + ép nhãn diễn tập, `SET NULL`, chỉ mục, lọc `role=guardian`, secret 8–256, mã cũ bị thu hồi, ops chỉ dev. Còn lại ghi ở ADR-010 "Rủi ro còn lại" và mục dưới |
| `ux-elder-reviewer` | Vòng 1: **3 Cao**, 20 Trung bình, 5 Thấp. Vòng 2: **0 Cao**; 3 Trung bình (1 mới, 2 hoãn có chủ ý) + 8 Thấp | Sửa 3 Cao (hướng dẫn trả lời không đóng nhầm cảnh báo, escalation, tin "đã đóng") và phần lớn Trung bình/Thấp; áp tiếp: lối thoát cho `pairing_help`, `pairing_already`, "Thêm:" thay "Chi tiết:". Hoãn: #9 dòng "Mức nguy cơ" (câu chữ P1-S4), #23 mẫu "đã lỡ chuyển tiền" (ngoài phạm vi ⇒ ghi chú ROADMAP) |
| `/ponytail-review` | Tự rà theo skill (diff + chạy kiểm chứng), **không phải reviewer độc lập**: không có phát hiện chặn; đã bỏ trùng lặp (`_parse` ⇒ `_result` dùng chung, `build_job_payload` dùng chung giữa webhook và `zalo_simulate`); tránh over-engineering: không thêm MCP `zalo`, không bảng đếm riêng (dùng `jobs`/`messages_out`), không xoay khóa động (ghi YAGNI). Nên có reviewer thứ hai đọc PR trước khi merge | — |

## `/speckit-converge`

1 lượt (chạy thủ công theo skill, chỉ-đọc), `tasks.md` **không bị thay đổi** bởi converge. Đối chiếu 15 FR, 8 SC, 5 user story (15 acceptance), 7 edge case, quyết định trong plan, 9 nguyên tắc hiến chương:

- **0 finding chạy được bằng code** (`missing`/`partial`/`contradicts` = 0).
- **Chặn bởi bên ngoài (theo MASTER-PLAN §2.5 ⇒ không thêm task code):** SC-001 và FR-015 phần số đo thật/hạn mức thật ⇒ **BLOCKED: chờ token bot thật (W0-3)**; gắn với T024, T025.
- `unrequested` (LOW, đã có lý do trong ADR-010 "Điều chỉnh khi hiện thực"): lệnh `zalo_simulate` (đáp FR-012), `spike demo --family` (nguồn số đo SC-001), giới hạn tần suất/scrub/`/readyz zalo_mode` (từ review bảo mật).

## Còn tồn / hoãn có chủ ý

- **T024 / T025 — BLOCKED: chờ token bot thật (W0-3)**: đo SC-001 (p50/p95, ≥ 20 lần + ≥ 5 lần bấm giờ), hạn mức thật (tin đến có tính vào 3.000 không), tần suất gửi lặp, hành vi gửi lại webhook của Zalo; sau đó hoàn thiện ADR-010 (T025) rồi mới đánh dấu P1-S3 hoàn thành ở ROADMAP.
- **Spec 020**: bước xác nhận thứ hai khi ghép + thu hồi hạng người giám hộ (giảm rủi ro đoán trúng mã 6 số bằng nhiều tài khoản); luồng sinh mã từ app phải áp "một mã còn hiệu lực mỗi gia đình".
- **Spec 011/020/034**: bản ghi `consents` cho `guardian_channel`, job xóa theo hạn lưu (kể cả `jobs.payload` của `notify_guardian`). Cho tới lúc đó **bot dev chỉ dùng với tài khoản Zalo của đội**.
- **Spec 012**: đặt `HOICON_ENV=prod` và `HOICON_ZALO_MODE=live` ở VPS (mock bị từ chối ngoài dev/test); `env` mặc định vẫn là `dev`.
- **Spec 021/023**: FK `messages_out.incident_id → incidents`, cờ `is_drill`/`is_demo` ở `messages_out`, mã ngắn khi có nhiều sự cố đồng thời, kênh dự phòng `/a/[token]` xử lý `fallback_required`.
- **P2-07/P2-08**: duyệt lại câu chữ cuối ("Mức nguy cơ: …", `reminder`/`escalation` ghi chung "ứng dụng tài chính").
- **ROADMAP "Ghi chú" (qua PR từ checkout chính)**: mẫu tin cho người nhà báo đã lỡ chuyển tiền (ngoài phạm vi 002, cần PRD/Minh duyệt số khẩn cấp).
- Xoay `kid` chưa dùng được: `Settings` chỉ có `data_key_1`/`phone_pepper_1`; AAD gắn `user_hmac` nên xoay pepper cần bước giải mã–mã hóa lại.
- Đồng bộ `.env` của máy dev: Minh/Tiến tự chạy `init_env --new-data-key` một lần để có `HOICON_DATA_KEY_1` (Claude không ghi `.env`; xem `docs/setup/ACCOUNTS.md` §3).
