# Implementation Plan: Hoàn tất lõi tác tử P1-S4 (danh sách đe dọa HMAC, MCP có token + hạn mức, bench, trần chi tiêu bền)

**Branch**: `feat/003-agent-core-mcp-threat` (tách từ `origin/tien-collab-dev` @ `9ae5532`) | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-agent-core-mcp-threat/spec.md`

## Summary

Chuyển danh sách đe dọa từ tệp JSON chứa h1 sang bảng `threat_indicators` chỉ lưu HMAC (migration `0004`, lệnh nạp
idempotent). Tra cứu thành hàm async dùng chung cho đồ thị và MCP. Bọc `/mcp/threat` bằng một middleware ASGI nhỏ: kiểm Bearer
token (so với SHA-256 trong cấu hình) và giới hạn tần suất theo client; sau đó gắn MCP ở mọi môi trường. `spike bench` thêm
`--model`/`--json`. `LlmRouter` đọc chi tiêu trong ngày từ `agent_steps`. Eval smoke nạp danh sách demo vào DB eval và phải
giữ nguyên kết quả.

**Quyết định kỹ thuật (Opus đề xuất theo ủy quyền của Tiến 15/10/2026, áp dụng mặc định; chạy một mạch, §2.6):**
- **T1 — Bảng `threat_indicators` chỉ HMAC** (ADR-006). Loại: giữ tệp JSON h1 (trái ADR-006, không nạp được danh sách thật);
  lưu thêm h1 mã hóa (chưa ai cần — đồng bộ xuống máy là việc của 022/026, xem "Đã biết").
- **T2 — Middleware ASGI riêng (~60 dòng) cho token + hạn mức**, bọc app `streamable_http_app` của MCP. Loại: `token_verifier`
  + `AuthSettings` của MCP SDK 2.3. SDK bắt khai `issuer_url` của máy chủ OAuth (HỏiCon không có, sẽ quảng bá metadata sai ở
  `/.well-known/oauth-protected-resource`) và không trả được 429 (từ chối trong `verify_token` chỉ ra 401).
- **T3 — Cấu hình `mcp_threat_clients: dict[str, str]`** (tên client → SHA-256 hex của token, đọc từ biến môi trường JSON).
  Máy chủ không giữ token thô. Rỗng ⇒ mọi yêu cầu 401 (đóng mặc định).
- **T4 — Hạn mức đếm trong bộ nhớ** (cửa sổ cố định theo phút + theo ngày giờ Việt Nam, mỗi client), mặc định 30/phút,
  1.000/ngày. Đủ cho một tiến trình (ADR-002). Loại: đếm trong Postgres (thêm truy vấn mỗi lượt tra, chưa cần).
- **T5 — Gắn `/mcp/threat` ở mọi môi trường** (bỏ `MOUNT_MCP`). Mở ra Internet hay không do Caddy (012) quyết.
- **T6 — Lỗi tra cứu ⇒ `unknown` + mã lỗi, sự cố vẫn chạy.** An toàn vì mức sàn của máy + `raise_only` không phụ thuộc tra
  cứu; chặn sự cố vì DB tra cứu lỗi thì mất đường cảnh báo (tệ hơn).
- **T7 — Trần chi tiêu = `SUM(agent_steps.cost_usd WHERE at ≥ 00:00 giờ VN)` + giữ chỗ trong tiến trình.** Lỗi đọc ⇒ fallback
  (`budget_unknown`), đóng mặc định về chi phí. Router nhận `sessions` tùy chọn; không có ⇒ hành vi cũ (test đơn vị cũ không đổi).

## Technical Context

**Language/Version**: Python 3.12 (`uv`)

**Primary Dependencies**: FastAPI/Starlette (ASGI), SQLAlchemy 2 + Alembic, psycopg 3, MCP Python SDK 2.3 (`MCPServer`),
LangGraph — **không thêm thư viện** (`secrets`, `hashlib`, `hmac`, `zoneinfo` là thư viện chuẩn)

**Storage**: Postgres 17 — migration `0004` (bảng `threat_indicators`)

**Testing**: `uv run --directory backend pytest` (unit + integration + contract) · `ruff check` · `alembic upgrade/downgrade` ·
`hoicon-eval --suite smoke --compare baseline` · client MCP qua ASGI (`httpx.ASGITransport`) như test hiện có

**Target Platform**: máy dev Linux (Postgres Docker 15432) + GitHub Actions

**Project Type**: monorepo — làn B

**Performance Goals**: tra cứu p95 ≤ 20 ms (index duy nhất); không đổi độ trễ điều phối (p50 ≈ 0,13 s/lượt)

**Constraints**: không h1 trên đĩa máy chủ; không log h1/token; không đọc `.env`; MCP đóng mặc định

**Scale/Scope**: danh sách demo 1 dòng; thiết kế cho ≤ 100.000 dòng (thí điểm)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Nguồn: `.specify/memory/constitution.md`.

| # | Nguyên tắc | Đụng tới? | Đạt / cách đảm bảo |
|---|---|---|---|
| I | Dừng an toàn | Không | Không đụng Android; `fast_alert` không phụ thuộc tra cứu (T6) |
| II | Riêng tư | **Có** | Chỉ HMAC + 3 số cuối (ADR-006); quét byte trong test; log không h1/token; token chỉ lưu SHA-256 |
| III | LLM chỉ nâng, qua router | **Có** (router) | Không đổi node/prompt/`raise_only`; trần chi tiêu đóng mặc định ⇒ fallback mẫu |
| IV | Công khai AI, `is_demo` | **Có** (`is_demo`) | Dòng demo có cờ; prod từ chối nạp demo; không tin mới |
| V | Hợp đồng trước, migration bất biến | **Có** | Migration mới `0004` (không sửa 0001–0003); `ThreatVerdict` giữ hình dạng; DATA-MODEL cập nhật cùng spec |
| VI | UX | Không | — |
| VII | Bằng chứng trung thực | **Có** | Bench không khóa ghi `llm_mode: fallback`; số model + VPS ghi BLOCKED, không ước |
| VIII | Ít code | **Có** | Dùng lại `hmac_h1`, `get_sessionmaker`, mẫu test MCP, `percentile`; middleware nhỏ thay vì OAuth |
| IX | Chặn phát hành | Gián tiếp | Đóng lỗ hổng dò danh sách trước khi MCP ra ngoài dev |

Kết quả: **ĐẠT**.

## Tái sử dụng *(mandatory)*

| Cần gì | Đã có ở đâu | Dùng lại / mở rộng / viết mới |
|---|---|---|
| HMAC h1 theo kid, pepper ngoài DB | `domain/pii.py::hmac_h1`, `_pepper` | **dùng lại**; thêm hàm liệt kê kid đã cấu hình nếu cần (kid 1 hiện tại) |
| Kết quả tra cứu | `mcp_servers/threat.py::ThreatVerdict`, tool `lookup_phone` | **giữ hình dạng**; `lookup_h1` thành async đọc DB |
| Gọi tra cứu trong sự cố | `agents/runtime.py::IncidentRuntime.start` (dòng `lookup_h1(event.caller.h1)`) | **sửa** thành `await`, bọc lỗi (T6) |
| Gắn MCP + lifespan | `api/main.py` (`MOUNT_MCP`, `session_manager.run()`) | **mở rộng**: bọc middleware, bỏ điều kiện dev |
| Phiên DB | `db/session.py::get_sessionmaker` | **dùng lại** (MCP tool, lệnh nạp) |
| Lệnh ops có argparse | `ops/pairing_code.py`, `ops/zalo_simulate.py` | **theo mẫu** cho `ops/threat_list.py`, `ops/mcp_token.py` |
| Test MCP | `tests/unit/test_texts_and_threat.py` (`mcp.client.Client`) | **mở rộng**: test HTTP có header qua `httpx.ASGITransport` |
| Quét byte checkpoint | `eval/checks.py` (hàm chuyển từ `test_incident_graph.py::checkpoint_bytes` ở 030) | **dùng lại** + quét `threat_indicators` |
| Bench | `agents/spike.py::bench`, `percentile`, `deps` | **mở rộng** (`--model`, `--json`) |
| Bảng giá model | `agents/llm_router.py::MODELS` | **dùng lại** (kiểm `--model`) |
| Chi phí từng bước | `agent_steps.cost_usd`, cột thời gian `at` | **dùng lại** cho trần bền (T7) |
| Eval cô lập DB | `eval/runner.py` (DB eval riêng, `is_demo`) | **mở rộng**: nạp seed demo trước lượt |
| Khóa giả cho test | `tests/integration/conftest.py` (pepper + data key giả) | **dùng lại**; CI eval đặt pepper giả tương tự |

## Project Structure

### Documentation (this feature)

```text
specs/003-agent-core-mcp-threat/
├── spec.md · plan.md · quickstart.md (tasks phase tạo)
├── data-model.md        # delta: threat_indicators (trỏ docs/DATA-MODEL.md)
├── tasks.md             # /speckit-tasks
└── evidence.md          # phase cuối
```

### Source Code (repository root)

```text
backend/migrations/versions/2026101?_0004_threat_indicators.py   # MỚI (FR-001) revision "0004", down "0003"
backend/src/hoicon/db/models.py                 # + ThreatIndicator
backend/src/hoicon/threat/__init__.py           # (hoặc giữ trong mcp_servers/threat.py — chọn một chỗ, đồ thị + MCP cùng gọi)
backend/src/hoicon/mcp_servers/threat.py        # lookup_h1 async (FR-003), tool async
backend/src/hoicon/mcp_servers/auth.py          # MỚI — middleware Bearer + hạn mức (FR-005, FR-006, FR-009)
backend/src/hoicon/api/main.py                  # gắn mọi môi trường + bọc middleware (FR-007)
backend/src/hoicon/agents/runtime.py            # await lookup, T6 (FR-004)
backend/src/hoicon/agents/llm_router.py         # trần bền (FR-011)
backend/src/hoicon/agents/spike.py              # --model, --json (FR-010)
backend/src/hoicon/config.py                    # mcp_threat_clients, mcp_rate_per_min, mcp_rate_per_day
backend/src/hoicon/ops/threat_list.py           # MỚI — load (FR-002)
backend/src/hoicon/ops/mcp_token.py             # MỚI — new --client (FR-008)
backend/src/hoicon/eval/runner.py               # nạp seed demo vào DB eval (FR-012)
backend/tests/unit/test_mcp_auth.py · test_threat_lookup.py · test_bench_json.py · test_llm_budget.py   # MỚI (FR-013)
backend/tests/integration/test_threat_indicators.py                                                    # MỚI
.github/workflows/backend.yml                   # pepper giả cho bước eval (FR-012)
docs/adr/ADR-009-loi-tac-tu.md · docs/DATA-MODEL.md · docs/AGENTS.md · docs/spikes/P1-S4-loi-tac-tu.md
backend/README.md · docs/MASTER-PLAN.md (§3 dòng 003 + 026) · docs/ROADMAP.md (dòng P1-S4)                # FR-014
```

**Structure Decision**: giữ `lookup_h1` trong `mcp_servers/threat.py` (đồ thị đã import từ đó, đổi ít nhất); middleware ở
`mcp_servers/auth.py` để dùng lại cho MCP `zalo`/`scenario` sau này.

## Thiết kế & trade-off

- **Bảng `threat_indicators`**: `id uuid pk` · `kind varchar(16)` (CHECK `IN ('phone')`) · `value_hmac char(64)` · `value_kid smallint`
  · `last3 char(3) null` · `source varchar(64)` · `confidence numeric(3,2)` (CHECK 0–1) · `tactic varchar(64) null` · `list_version
  varchar(32)` · `is_demo bool default false` · `first_seen`, `last_seen timestamptz default now()` · `expires_at timestamptz null`.
  `UNIQUE (kind, value_kid, value_hmac)` (cũng là index tra cứu). Tra: `WHERE kind='phone' AND (value_kid, value_hmac) IN
  (…mọi kid…) AND (expires_at IS NULL OR expires_at > now())`, chọn dòng có `confidence` cao nhất.
- **Lệnh nạp**: đọc JSON (`version`, `is_demo`, `indicators[{h1, source, confidence, tactic, last3?, expires_at?}]`), kiểm toàn
  bộ trước khi ghi (một giao dịch), `INSERT … ON CONFLICT (kind, value_kid, value_hmac) DO UPDATE SET source, confidence,
  tactic, list_version, last_seen = now()`. In `thêm N · cập nhật M`. `env == "prod" and is_demo` ⇒ exit 2. Tệp demo hiện có
  (`data/threat_seed.demo.json`) giữ nguyên định dạng (vẫn chứa h1 của số **hư cấu** — dữ liệu đầu vào, không phải lưu trữ máy chủ).
- **Middleware** (`McpGuard`, ASGI thuần, không phụ thuộc Starlette `BaseHTTPMiddleware` để không phá streaming):
  1. Lấy `Authorization`; không phải `Bearer <token>` ⇒ 401 JSON `{"error": "unauthorized"}` + `WWW-Authenticate: Bearer`.
  2. `sha256(token)` so với từng hash cấu hình bằng `hmac.compare_digest` (duyệt hết danh sách, không dừng sớm) ⇒ tên client.
  3. Hạn mức: `dict[client] → (phút, đếm)`, `(ngày VN, đếm)`; vượt ⇒ 429 + `Retry-After` = giây tới hết cửa sổ.
  4. Chuyển tiếp tới app MCP; gói `send` để lấy mã trạng thái; ghi log một dòng (FR-009). Verdict lấy từ tool (biến ngữ cảnh
     `contextvars` do tool đặt) — không đọc lại body phản hồi.
  Đếm cả yêu cầu `initialize`/`tools/list` (đơn giản, an toàn hơn). Mặc định 30/phút đủ cho người dùng tay và script nhỏ.
- **Async lookup + MCP tool**: tool `async def lookup_phone(h1)` dùng `get_sessionmaker()`; đồ thị gọi `await lookup_h1(self._sessions, h1)`
  (runtime đã có `_sessions`). `ValueError` (h1 sai) vẫn ném ra ở MCP (lỗi tool); ở runtime thì `RiskEvent` đã kiểm h1 từ trước.
- **Trần bền (T7)**: `LlmRouter(..., sessions=None)`. Có `sessions` ⇒ trước khi giữ chỗ: `spent_db = SELECT COALESCE(SUM(cost_usd),0)
  FROM agent_steps WHERE at >= :start_of_day_vn`; `spent = spent_db + reserved_in_flight`. Bỏ `_spent` theo ngày, chỉ giữ tổng
  giữ chỗ đang bay (trừ khi lời gọi xong — `agent_steps` sẽ ghi chi phí thật). `from_settings` nhận `sessions` từ `deps()`.
  Ghi chú: chi phí ghi vào `agent_steps` sau node ⇒ giữa lúc gọi xong và lúc ghi có khe nhỏ; chấp nhận (trần là ngân sách mềm,
  sai số ≤ một lời gọi).
- **Bench JSON**: `{"model", "llm_mode", "n", "turns": {"start→ask_elder": {"p50_s","p95_s","max_s"}, …}, "fallback_rate",
  "cost_usd_avg", "measured_at", "host": "<os + cpu + ram, tự mô tả>"}`. `fallback_rate` = tỷ lệ `agent_steps.fallback_used`
  của các run bench. Lọc run của lượt bench theo `thread_id` đã tạo (không dùng `limit(n)` theo thời gian như hiện tại — sai khi có
  run khác chạy cùng lúc).
- **Eval (FR-012)**: runner gọi hàm nạp (cùng code với lệnh ops) cho `data/threat_seed.demo.json` trước khi chạy ca. CI
  `backend.yml`: đặt pepper giả (chuỗi cố định công khai, như conftest) cho bước `hoicon-eval`. Test eval tích hợp dùng fixture khóa
  giả sẵn có.
- **Đã biết / ngoài phạm vi**: DATA-MODEL ghi `threat_indicators` "đồng bộ xuống máy dạng danh sách hash" — máy cần **h1** để so
  với số gọi đến, mà bảng chỉ có HMAC. Spec 022/026 phải quyết (gợi ý: cột `value_enc` AES-256-GCM như D1 của 002, hoặc danh sách
  h1 tách khỏi DB). Ghi vào mục "Ghi chú" của ROADMAP; không thêm cột trước khi cần.
- **Rủi ro**: (a) đổi `lookup_h1` sang async làm vỡ test/caller cũ (`test_texts_and_threat.py`, `spike`, eval) — chạy cả bộ
  pytest sau mỗi bước; (b) middleware ASGI làm hỏng streamable HTTP — test gọi `initialize` + `tools/call` thật qua ASGI; (c) CI
  thiếu pepper ⇒ eval đỏ — FR-012.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
