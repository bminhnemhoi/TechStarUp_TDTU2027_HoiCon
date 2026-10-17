# Implementation Plan: Kênh Zalo cho người giám hộ (spike P1-S3)

**Branch**: `feat/002-zalo-guardian-channel` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-zalo-guardian-channel/spec.md`

## Summary

Nối job `notify_guardian` (đang chỉ log) với Zalo Bot qua **một `ZaloClient`** có hai bản:
- `LiveZaloClient`: `httpx`, token trên URL, lọc log, lỗi không mang URL.
- `MockZaloClient`: mặc định khi thiếu token/CI.

Webhook `POST /webhooks/zalo/{bot_id}` nằm trong **ứng dụng con** riêng, phơi qua cloudflared ở dev:
1. Kiểm secret.
2. Xếp job `zalo_update` với khóa chống trùng `zalo:{bot_id}:{message_id}` (Zalo không gửi `update_id`) — dùng lại `jobs.idempotency_key`, không bảng mới.
3. Trả 200.

Handler xử lý `/start <mã>` (ghép người giám hộ) và `1/2/3` (resume `await_guardian`).

Migration 0003 tạo `families`, `members`, `pairing_codes`, `messages_out` theo DATA-MODEL; cột Zalo theo D1:
`zalo_chat_enc` AES-GCM + `zalo_user_hmac`.

Bộ đếm hạn mức trên `messages_out`. Báo cáo spike + ADR-010. **D1/D2: Tiến duyệt 15/10/2026** (trước migration).

## Technical Context

**Language/Version**: Python 3.12 (`uv`)

**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic, psycopg 3, `httpx` (đã có gián tiếp ⇒ khai báo
trực tiếp), `cryptography` (AES-GCM; đã có gián tiếp ⇒ khai báo trực tiếp). Không thêm thư viện mới.

**Storage**: Postgres (dev 15432) — migration `0003` (4 bảng); hàng đợi `jobs` sẵn có

**Testing**: `uv run --directory backend pytest` (unit + integration cần Postgres) · `ruff` · hợp đồng `tests/contract/`

**Target Platform**: Linux (dev: máy Tiến; tunnel cloudflared); VPS ở spec 012

**Project Type**: monorepo — spec này chỉ làn B (`backend/**`, `docs/**`)

**Performance Goals**: xếp tin → Zalo xác nhận p95 ≤ 5 s; webhook trả 200 ≤ 300 ms (chỉ kiểm secret + insert job)

**Constraints**: token không bao giờ ra log/lỗi; không lưu Zalo ID thô; 3.000 tin/tháng/bot; CI không có token ⇒ mock

**Scale/Scope**: 1 bot dev; cấu hình sẵn nhiều `bot_id` (3 bot thí điểm)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn offline | Không | Máy chủ, sau đường găng |
| II | Riêng tư | **Có** | D1: `chat_id` mã hóa + HMAC; văn bản trả lời không lưu; lọc token; quét log (SC-003); `security-privacy-reviewer` |
| III | LLM chỉ nâng | Không gọi LLM | Tin mẫu từ `texts.py`; văn bản người giám hộ không vào prompt |
| IV | Công khai AI, đồng ý | **Có** | Mọi tin qua `texts._message` (câu công khai + nhãn diễn tập); test SC-006. Đồng ý `guardian_channel` ở 011/020; bot dev chỉ tài khoản đội |
| V | Hợp đồng trước, migration bất biến | **Có** | Schema cập nhật Zalo vào `docs/schemas/` trước code; migration 0003 do làn B; theo DATA-MODEL (sửa cột Zalo sau khi D1 được duyệt) |
| VI | UX | Câu chữ | `ux-elder-reviewer` duyệt mẫu tin mới |
| VII | Bằng chứng trung thực | **Có** | SC-001 đo trên bot thật; thiếu token ⇒ BLOCKED; số mock ghi nhãn "mock" |
| VIII | Ít code, tái sử dụng | **Có** | Dùng lại `jobs` (chống trùng, retry), `texts.py`, `pii.py`, `check_keys` (mẫu lệnh ops) |
| IX | Chặn phát hành | Có | Bot dev chỉ cho tài khoản đội; không bot thí điểm trước 011/020 |

Kết quả: **ĐẠT, có điều kiện** — D1 sửa một cột trong DATA-MODEL (HMAC → mã hóa + HMAC) ⇒ Tiến đã duyệt 15/10/2026 (ADR-010; Minh xem lại ở PR)
trước task migration. Không vi phạm hiến chương.

## Tái sử dụng *(mandatory — điền TRƯỚC khi thiết kế mới)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới (lý do) |
|---|---|---|
| Hàng đợi, retry 2^n, chống trùng | `backend/src/hoicon/jobs/queue.py` (`enqueue` + `idempotency_key` + `on_conflict_do_nothing`, `complete`, `MAX_ATTEMPTS`) | **dùng lại** cho webhook (khóa `zalo:{bot_id}:{message_id}`) và gửi tin |
| Handler `notify_guardian` | `backend/src/hoicon/jobs/worker.py::incident_handlers` | **mở rộng**: gửi thật qua `ZaloClient` + `messages_out` |
| Câu công khai AI, nhãn diễn tập | `backend/src/hoicon/agents/texts.py` (`AI_DISCLOSURE`, `_message`) | **mở rộng**: thêm mẫu trả lời `/start`, hướng dẫn 1/2/3, xác nhận |
| HMAC định danh | `backend/src/hoicon/domain/pii.py::hmac_h1` (pepper + kid) | **mở rộng**: hàm HMAC có tiền tố miền `hoicon:zalo:v1:` dùng cùng pepper |
| Resume đồ thị | `IncidentRuntime.resume(thread_id, value, expect)` | **dùng lại** cho phản hồi 1/2/3 |
| Bắt đầu sự cố | `IncidentRuntime.start(...)` | **mở rộng**: tham số `family_id` tùy chọn ⇒ có trong payload `notify_guardian` |
| Gọi API chỉ in Đạt/Lỗi | `backend/src/hoicon/ops/check_keys.py` (`check_zalo` gọi `getMe`) | **mẫu** cho `hoicon.ops.zalo_webhook` và `hoicon.ops.pairing_code` |
| Sinh bí mật | `backend/src/hoicon/ops/init_env.py` (AUTO: pepper, webhook secret) | **mở rộng**: sinh `HOICON_DATA_KEY_1` |
| Mã định danh | `backend/src/hoicon/db/ids.py::new_id` | dùng lại |

## Project Structure

### Documentation (this feature)

```text
specs/002-zalo-guardian-channel/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md
├── contracts/README.md   # trỏ docs/schemas/zalo_update.v1.json + fixture
├── tasks.md · checklists/requirements.md
└── evidence.md           # phase cuối
```

### Source Code (repository root)

```text
docs/schemas/zalo_update.v1.json + docs/schemas/fixtures/zalo_update.v1.{valid,invalid}.json   # hợp đồng (trước)
backend/src/hoicon/channels/zalo.py        # ZaloClient (Live/Mock), ZaloError, bộ lọc log token
backend/src/hoicon/channels/guardian.py    # gửi tin + hạn mức messages_out; xử lý cập nhật (/start, 1/2/3)
backend/src/hoicon/api/webhooks.py         # app con: POST /webhooks/zalo/{bot_id}; gắn vào app chính + chạy riêng cho tunnel
backend/src/hoicon/db/models.py            # Family, Member, PairingCode, MessageOut
backend/src/hoicon/domain/pii.py           # hmac_zalo, encrypt/decrypt chat_id (AES-GCM, kid)
backend/src/hoicon/agents/{texts,runtime,incident_graph}.py   # mẫu tin mới; family_id
backend/src/hoicon/jobs/worker.py          # handlers notify_guardian (thật), zalo_update
backend/src/hoicon/ops/{zalo_webhook,pairing_code}.py · ops/{init_env,check_keys}.py
backend/migrations/versions/20261016_0003_families_members_pairing_messages.py
backend/tests/{unit,integration,contract}/test_zalo_*.py
docs/spikes/P1-S3-zalo.md · docs/adr/ADR-010-kenh-zalo.md (nháp, Minh duyệt) · docs/DATA-MODEL.md · docs/API.md
```

**Structure Decision**: thư mục mới `backend/src/hoicon/channels/` cho kênh gửi tới người giám hộ (Zalo nay, web push sau)
— tách khỏi `agents/` vì không phải tác tử và không gọi LLM.

## Thiết kế & trade-off

- **Chống trùng bằng `jobs.idempotency_key`** thay vì bảng `zalo_updates` riêng: đã có unique index + `on_conflict_do_nothing`;
  không cần migration thêm. Hệ quả: cửa sổ chống trùng = hạn lưu `jobs` (30 ngày) — đủ (Zalo chỉ gửi lại trong vài phút).
- **Webhook trả 200 sau khi insert job thành công**; DB lỗi ⇒ 503 để Zalo gửi lại (không mất cập nhật).
- **App con cho webhook**: `webhooks.py` là một `FastAPI()` nhỏ: được `mount` vào app chính, và chạy riêng
  `uvicorn hoicon.api.webhooks:app --port 18080` cho cloudflared (chỉ route webhook ra Internet — ADR-003).
- **Mock**: chọn bằng `HOICON_ZALO_MODE=mock|live` (mặc định `mock`; `live` mà thiếu token ⇒ lỗi khi khởi động, không âm
  thầm rơi về mock). Mock ghi tin vào bộ nhớ (test) và có lệnh giả lập cập nhật đến dựa trên fixture hợp đồng.
- **Gửi đúng một lần**: khóa job `incident:msg:template` đã có; thêm `messages_out` theo khóa đó; trước khi gọi Zalo kiểm dòng
  đã `sent` ⇒ bỏ qua (retry không gửi lặp). Còn rủi ro "Zalo đã nhận nhưng ta timeout" ⇒ chấp nhận gửi lặp hiếm (ghi ở ADR-010).
- **Hạn mức**: `count(*) where bot_id, quota_month, status in (sent)`; ngưỡng cấu hình; tin sự cố (`template` thuộc nhóm
  incident) bỏ qua ngưỡng 95% nhưng vẫn đếm.
- **Ánh xạ phản hồi ⇒ sự cố**: phản hồi 1/2/3 của người giám hộ ⇒ dòng `messages_out` gần nhất đã gửi tới người đó có
  `incident_id` ⇒ `runtime.resume(incident_id, {"decision": "safe"|"scam"}, expect="await_guardian")` ("1" ⇒ `safe`,
  "2" ⇒ `scam`, "3" ⇒ gửi chi tiết, **không** resume) — khớp `incident_graph.await_guardian`. Bảng `incidents`/`guardian_actions` ở 021/023.
- **Nút bấm**: R1 (15/10) không thấy keyboard/callback trong tài liệu chính thức ⇒ chỉ 1/2/3 (ADR-003 đã cho phép).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
