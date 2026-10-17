---

description: "Tasks — 003-agent-core-mcp-threat (làn B)"
---

# Tasks: Hoàn tất lõi tác tử P1-S4 — danh sách đe dọa HMAC, MCP `threat` có token + hạn mức, bench so model, trần chi tiêu bền

**Input**: `specs/003-agent-core-mcp-threat/` (spec.md, plan.md; quyết định T1–T7 do Tiến duyệt trước, 15/10/2026)

**Chế độ chạy**: **TỰ HÀNH MỘT MẠCH** (docs/MASTER-PLAN.md §2.6). Không có task "chờ duyệt". Thứ thiếu từ bên ngoài (khóa
Anthropic P0-08, VPS P1-09) ⇒ `BLOCKED: <lý do>` trong evidence.md kèm lệnh chạy sẵn, làm tiếp task khác.

**Phạm vi sửa**: `backend/**`, `docs/schemas/**`, `data/threat_seed*`, `specs/003-agent-core-mcp-threat/**`, `docs/ROADMAP.md`,
`docs/{adr/ADR-009*,DATA-MODEL.md,AGENTS.md,spikes/P1-S4-loi-tac-tu.md,MASTER-PLAN.md}`, `.github/workflows/backend.yml`.
**Cấm** `apps/**`. Không đọc/ghi `.env`. Không commit/push.

**Tests**: bắt buộc, viết trước (đỏ — chạy và thấy đỏ) rồi mới code (xanh).

**Môi trường test**: `HOICON_DATABASE_URL` = DB dev 15432 `hoicon`; `HOICON_EVAL_DATABASE_URL` = DB `hoicon_eval` (nếu không,
test eval ghi dòng `eval-*` vào DB dev). Test cần pepper dùng khóa GIẢ của `tests/integration/conftest.py` (`11`×32), không dùng `.env`.

## Format: `[ID] [P?] [Story] Description — FR-xxx · Verify: \`lệnh\``

---

## Phase 1: Setup — hợp đồng trước

- [x] T001 [P] Viết `docs/schemas/threat_seed.v1.json` (tệp nạp: `version` string, `is_demo` bool, `indicators[]` mỗi phần tử `h1` ^[0-9a-f]{64}$, `source`, `confidence` 0–1, `tactic?`, `last3?` ^[0-9]{3}$, `expires_at?` date-time; thuộc tính tùy chọn `_note` string vì `data/threat_seed.demo.json` đang có; không thuộc tính lạ khác) + fixture `docs/schemas/fixtures/threat_seed.v1.{valid,invalid}.json` (invalid: h1 là số thô; thiếu `source`; `confidence` = 1.5; `last3` 4 chữ số) — FR-002, FR-013 · Verify: `uv run --directory backend pytest tests/contract/test_threat_schemas.py -q` (sau T003)
- [x] T002 [P] Viết `docs/schemas/bench_report.v1.json` (`model`, `llm_mode` ∈ {live,fallback}, `n` ≥ 1, `turns{<tên>:{p50_s,p95_s,max_s}}`, `fallback_rate` 0–1, `cost_usd_avg` ≥ 0, `measured_at` date-time, `host` string; không thuộc tính lạ) + fixture valid/invalid (invalid: `llm_mode` lạ; thiếu `model`; `fallback_rate` = 2) — FR-010, FR-013 · Verify: như T001
- [x] T003 Viết `backend/tests/contract/test_threat_schemas.py` (valid hợp lệ, invalid bị từ chối; `data/threat_seed.demo.json` hợp lệ theo `threat_seed.v1.json`) theo mẫu `test_eval_schemas.py` — FR-002, FR-010 · Verify: `uv run --directory backend pytest tests/contract -q`

---

## Phase 2: Foundational — bảng, cấu hình, hàm HMAC nhiều kid

**⚠️ Chặn mọi user story.**

- [x] T004 Test trước `backend/tests/integration/test_schema_0004.py` (theo mẫu `test_schema_0003.py`): bảng `threat_indicators` đủ cột (`id uuid`, `kind varchar(16)` CHECK `IN ('phone')`, `value_hmac char(64)`, `value_kid smallint`, `last3 char(3) null`, `source varchar(64)`, `confidence numeric(3,2)` CHECK 0–1, `tactic varchar(64) null`, `list_version varchar(32)`, `is_demo bool default false`, `first_seen`/`last_seen timestamptz default now()`, `expires_at timestamptz null`); `UNIQUE (kind, value_kid, value_hmac)`; chèn trùng bị từ chối; `kind='email'` và `confidence=1.5` bị CHECK từ chối; KHÔNG có cột tên chứa `h1` hay `phone`/`number` — FR-001 · Verify: `uv run --directory backend pytest tests/integration/test_schema_0004.py -q` (đỏ)
- [x] T005 Migration `backend/migrations/versions/20261016_0004_threat_indicators.py` (revision `0004`, down `0003`, có `downgrade` xóa bảng; KHÔNG sửa 0001–0003) + `ThreatIndicator` trong `backend/src/hoicon/db/models.py` (theo mẫu `PairingCode`/`Member`; tên constraint theo `naming_convention` của `Base`) — FR-001 · Verify: `uv run --directory backend alembic upgrade head && uv run --directory backend alembic downgrade -1 && uv run --directory backend alembic upgrade head && uv run --directory backend pytest tests/integration/test_schema_0004.py -q`
- [x] T006 [P] Test trước `backend/tests/unit/test_pii_kids.py`: `candidate_hmacs(h1)` trả HMAC theo MỌI kid có pepper (kid hiện hành + kid cũ khi `phone_pepper_2` được cấu hình), bỏ qua kid chưa cấu hình, thiếu hoàn toàn pepper ⇒ `RuntimeError`, h1 sai định dạng ⇒ `ValueError` — FR-003 · Verify: `uv run --directory backend pytest tests/unit/test_pii_kids.py -q` (đỏ)
- [x] T007 `backend/src/hoicon/config.py`: thêm `phone_pepper_2: SecretStr | None = None` (xoay pepper), `mcp_threat_clients: dict[str, str] = {}` (tên client → SHA-256 hex của token; đọc từ biến môi trường JSON), `mcp_rate_per_min: int = 30`, `mcp_rate_per_day: int = 1000`. `backend/src/hoicon/domain/pii.py`: thêm `candidate_hmacs(h1) -> list[tuple[int, str]]` dùng lại `hmac_h1`/`_pepper` — FR-003, FR-005, FR-006 · Verify: `uv run --directory backend pytest tests/unit/test_pii_kids.py tests/unit/test_pii.py -q`

**Checkpoint**: bảng + cấu hình + HMAC nhiều kid sẵn, test xanh.

---

## Phase 3: User Story 1 — danh sách đe dọa trong Postgres dạng HMAC (P1) 🎯 MVP

**Độc lập kiểm được bằng**: nạp seed demo ⇒ `lookup` số gắn cờ = `flagged`, số khác = `unknown`; quét byte bảng không có h1.

- [x] T008 [US1] Thêm vào `backend/tests/integration/conftest.py` fixture `fake_pepper` (khóa GIẢ lặp `11`×32 cho biến pepper kid 1 + xóa cache cấu hình, như `zalo_env`) và `seeded_threat` (dùng `fake_pepper`, gọi `load_seed` với `data/threat_seed.demo.json`, xóa các dòng `is_demo` đã nạp khi xong). Rồi test trước `backend/tests/integration/test_threat_indicators.py` (dùng hai fixture này; dọn dòng test sau mỗi ca): (a) nạp seed demo ⇒ 1 dòng `is_demo=true`, `value_hmac` 64 hex, chạy lại ⇒ thêm 0 / cập nhật 1, vẫn 1 dòng; (b) quét byte toàn bảng (`SELECT t::text`) không chứa h1 demo; (c) h1 sai định dạng trong lô ⇒ từ chối, không ghi dòng nào (kể cả các dòng hợp lệ đứng trước); (d) `env=prod` + `is_demo` ⇒ exit 2, không ghi; (e) tra `flagged` (đủ `source`, `confidence`, `tactic`, `list_version`) / `unknown` / dòng đã `expires_at` ⇒ `unknown` / dòng kid 1 tra được khi kid hiện hành = 2; (f) lệnh in chỉ số lượng, không in h1/HMAC (capsys) — FR-002, FR-003, FR-013, SC-001 · Verify: `uv run --directory backend pytest tests/integration/test_threat_indicators.py -q` (đỏ)
- [x] T009 [US1] `backend/src/hoicon/ops/threat_list.py` (theo mẫu `ops/pairing_code.py`; `python -m hoicon.ops.threat_list load <tệp>`): hàm `load_seed(sessions, doc, env)` dùng chung với eval — kiểm TOÀN BỘ lô (h1 hợp lệ, `confidence` 0–1) trước khi ghi, một giao dịch, `INSERT … ON CONFLICT (kind, value_kid, value_hmac) DO UPDATE SET source, confidence, tactic, list_version, last3, expires_at, last_seen = now()`, đếm thêm/cập nhật bằng `xmax = 0`; `env in ("prod","production") and is_demo` ⇒ exit 2; chỉ in `thêm N · cập nhật M`; `asyncio.run(..., loop_factory=asyncio.SelectorEventLoop)` — FR-002 · Verify: `uv run --directory backend pytest tests/integration/test_threat_indicators.py -q -k "load or seed or prod or batch or print"`
- [x] T010 [US1] Test trước: tách phần tra cứu của `backend/tests/unit/test_texts_and_threat.py` (2 test dùng `lookup_h1`/MCP in-process) sang `backend/tests/integration/test_threat_lookup.py` dùng `seeded_threat` (phần luật 6 công khai AI giữ ở unit): `lookup_h1(sessions, h1)` async; h1 thô ⇒ `ValueError`; ca "lỗi tra cứu": `IncidentRuntime.start` với `lookup_h1` ném `OperationalError` ⇒ `threat == {"verdict":"unknown","error":"OperationalError"}`, sự cố vẫn chạy tới `ask_elder`, mức ≥ `rule_floor`, checkpoint không chứa h1/package; thêm vào `tests/integration/test_incident_graph.py` (dọn thread bằng fixture `threads`) — FR-003, FR-004, FR-013 · Verify: `uv run --directory backend pytest tests/unit/test_texts_and_threat.py tests/integration/test_threat_lookup.py tests/integration/test_incident_graph.py -q` (đỏ)
- [x] T011 [US1] `backend/src/hoicon/mcp_servers/threat.py`: bỏ `_seed`/`SEED`; `async def lookup_h1(sessions, h1)` tra `WHERE kind='phone' AND (value_kid, value_hmac) IN (candidate_hmacs…) AND (expires_at IS NULL OR expires_at > now()) ORDER BY confidence DESC LIMIT 1`; `list_version` của `unknown` lấy `MAX(list_version)` hoặc `"none"` khi bảng trống; tool `lookup_phone` thành `async` dùng `get_sessionmaker()`; `ValueError` giữ nguyên. `agents/runtime.py:122` → `await lookup_h1(self._sessions, …)` bọc `try/except Exception` ⇒ `{"verdict":"unknown","error": type(exc).__name__}` (không ghi thông điệp lỗi). Cập nhật `spike.py` (chú thích `DEMO_H1`), `api/main.py` chỉ import — FR-003, FR-004 · Verify: `uv run --directory backend pytest tests/unit tests/integration/test_threat_lookup.py tests/integration/test_incident_graph.py -q` (test eval `test_eval_*.py` đỏ có chủ đích tới hết T012 — đừng chạy cả `tests/integration` ở bước này)
- [x] T012 [US1] Test trước + code nạp seed cho eval: `backend/tests/integration/test_eval_smoke.py` và `test_eval_mutations.py` dùng thêm `fake_pepper` (runner đọc pepper từ cấu hình) và vẫn ĐẠT khi DB eval trống (runner tự nạp `data/threat_seed.demo.json`, idempotent); `backend/src/hoicon/eval/runner.py` gọi `load_seed` (T009) ngay sau khi kiểm cách ly, trước ca đầu, `env` lấy từ cấu hình (eval từ chối prod sẵn). `.github/workflows/backend.yml`: bước `eval smoke` thêm `HOICON_PHONE_PEPPER_1: ${{ ... }}` bằng chuỗi giả cố định công khai (như conftest, ghi chú "không phải bí mật"); nếu thiếu pepper khi chạy CLI ⇒ exit 2 + thông báo rõ (không traceback; test thêm vào `tests/unit/test_eval_cli.py`); máy dev không có pepper (agent không đọc `.env`) ⇒ ghi SKIPPED + dựa CI — FR-012 · Verify: `uv run --directory backend pytest tests/unit tests/integration -q` (toàn bộ xanh) và `hoicon-eval --suite smoke --compare baseline` với `HOICON_EVAL_DATABASE_URL` + pepper giả đặt trên dòng lệnh (exit 0, so baseline +0 điểm %)
- [x] T013 [US1] Đo SC-005: test/bench `tests/integration/test_threat_indicators.py::test_lookup_p95` — 200 lượt `lookup_h1` trên DB dev, in p95, chỉ chặn ở ≤ 100 ms (tránh flaky khi máy dev bị swap), SỐ p95 thật + máy ghi vào evidence để đối chiếu mục tiêu 20 ms — SC-005 · Verify: `uv run --directory backend pytest tests/integration/test_threat_indicators.py -q -k p95`

**Checkpoint US1**: MVP — danh sách trong DB, đồ thị + eval dùng được, 0 h1 trong bảng.

---

## Phase 4: User Story 2 — `/mcp/threat` có token + giới hạn tần suất (P1)

**Độc lập kiểm được bằng**: HTTP qua ASGI: không token / sai token / không cấu hình ⇒ 401; đúng ⇒ 200; vượt ⇒ 429.

- [x] T014 [US2] Test trước `backend/tests/unit/test_mcp_auth.py` (các ca 401/429/log/hạn mức dựng `McpGuard` quanh một app ASGI giả; riêng ca streamable HTTP `initialize` + `tools/call` dùng app thật `hoicon.api.main:app` qua `TestClient` một lần/mô-đun (lifespan MCP chỉ chạy được một lần mỗi tiến trình) và cần `seeded_threat`; mỗi ca dùng tên client duy nhất vì hạn mức nằm trong guard; cấu hình qua `monkeypatch` + xóa cache `get_settings`; token giả ngẫu nhiên trong test): không header ⇒ 401 + `WWW-Authenticate: Bearer`, tool không chạy; sai token ⇒ 401; `Authorization: Basic …` ⇒ 401; không cấu hình client nào ⇒ 401 (kể cả khi có header); token đúng ⇒ `initialize` 200 rồi `tools/call lookup_phone` 200 `flagged` (streamable HTTP thật, không bị middleware phá); vượt `mcp_rate_per_min` ⇒ 429 + `Retry-After` ≥ 1 và tool không chạy (n = hạn mức + 1); client B không bị ảnh hưởng bởi client A; hết ngày VN ⇒ đếm lại (đồng hồ giả qua tham số `clock`); caplog: có tên client + mã + tool + verdict, KHÔNG chứa h1, token, hash token — FR-005, FR-006, FR-009, FR-013, SC-002 · Verify: `uv run --directory backend pytest tests/unit/test_mcp_auth.py -q` (đỏ)
- [x] T015 [US2] `backend/src/hoicon/mcp_servers/auth.py`: `McpGuard` ASGI thuần (KHÔNG `BaseHTTPMiddleware`), nhận `app` và `clock`; đọc `mcp_threat_clients`, `mcp_rate_per_min`, `mcp_rate_per_day` từ `get_settings()` MỖI yêu cầu (test đổi cấu hình bằng `monkeypatch` + `cache_clear`, không dựng lại app); `sha256(token)` so với MỌI hash bằng `hmac.compare_digest` (không dừng sớm); hạn mức cửa sổ cố định phút + ngày `Asia/Ho_Chi_Minh` theo client, vượt ⇒ 429 + `Retry-After` (giây tới hết cửa sổ); chỉ xử lý `scope["type"] == "http"` (lifespan đi thẳng); gói `send` lấy mã trạng thái; verdict qua `contextvars` do tool đặt (không đọc body); log một dòng `mcp client=<tên> status=<mã> tool=<tên> verdict=<…> ms=<n>` — không IP, h1, token. Tool `lookup_phone` đặt biến ngữ cảnh verdict — FR-005, FR-006, FR-009 · Verify: `uv run --directory backend pytest tests/unit/test_mcp_auth.py -q`
- [x] T016 [US2] `backend/src/hoicon/api/main.py`: bỏ `MOUNT_MCP`; luôn chạy `threat.mcp.session_manager.run()` trong lifespan và mount `McpGuard(threat.mcp.streamable_http_app(...))` tại `/mcp/threat` (đọc `get_settings()` lúc dựng app); chuyển `tests/unit/test_mcp_http.py` sang `tests/integration/test_mcp_http.py` (cần DB + `seeded_threat` + token đúng) (kiểm Host lạ vẫn 421 — đi kèm token đúng; không token ⇒ 401 trước cả kiểm Host); cập nhật chú thích đầu file — FR-007 · Verify: `uv run --directory backend pytest tests/integration/test_mcp_http.py tests/unit/test_mcp_auth.py tests/unit/test_healthz.py -q`
- [x] T017 [P] [US2] Test trước + code `backend/src/hoicon/ops/mcp_token.py` (`python -m hoicon.ops.mcp_token new --client <tên>`): test `backend/tests/unit/test_mcp_token.py` — token ≥ 32 byte (`secrets.token_urlsafe(32)`), in token MỘT lần, dòng cấu hình `HOICON_MCP_THREAT_CLIENTS={"<tên>":"<sha256>"}` có hash khớp token, tên client rỗng/ký tự lạ bị từ chối (`[a-z0-9_-]{1,32}`), hai lần chạy cho hai token khác nhau, không đọc/ghi tệp nào — FR-008, FR-013 · Verify: `uv run --directory backend pytest tests/unit/test_mcp_token.py -q`

**Checkpoint US2**: MCP gắn mọi môi trường, đóng mặc định, có hạn mức.

---

## Phase 5: User Story 3 — bench so model (P2)

**Độc lập kiểm được bằng**: bench với client giả/không khóa ⇒ JSON đúng hợp đồng, `llm_mode` đúng.

- [x] T018 [US3] Test trước `backend/tests/integration/test_bench_json.py` (không khóa API): `bench(n=3, model="claude-haiku-4-5", json_path=…)` ⇒ JSON hợp lệ theo `bench_report.v1.json` (T002), `llm_mode == "fallback"`, `fallback_rate == 1.0`, `n == 3`, 3 lượt đo mỗi bước; chỉ tính run của thread do bench tạo (có thêm run khác trong DB cũng không lẫn); model không có trong `MODELS` ⇒ `SystemExit` mã 2 với thông điệp "chưa có giá"; chỉ đổi model của router, không đổi `Settings` toàn cục; `host` không chứa tên người dùng/hostname — FR-010, FR-013 · Verify: `uv run --directory backend pytest tests/integration/test_bench_json.py -q` (đỏ)
- [x] T019 [US3] `backend/src/hoicon/agents/spike.py`: `bench --n --model <id> --json <tệp>`; `--model` kiểm trong `MODELS` rồi ghi đè `llm_fast_model` qua `model_copy`; lọc run theo `thread_id` đã tạo (bỏ `order_by(started_at).limit(n)`); `fallback_rate` = tỷ lệ `agent_steps.fallback_used` (chỉ node LLM) của các run bench; `llm_mode` = `live` nếu có khóa và `fallback_rate < 1`; `host` = `platform.system()` + `platform.machine()` + `os.cpu_count()` lõi (không hostname); `measured_at` UTC; in bảng như cũ — FR-010 · Verify: `uv run --directory backend pytest tests/integration/test_bench_json.py tests/integration/test_spike_family.py -q`
- [x] T020 [US3] Chạy bench không khóa 2 model, lưu JSON ra scratchpad, kiểm theo schema; ghi vào evidence; phần có khóa ⇒ `BLOCKED: chờ khóa API (P0-08)` + lệnh chạy sẵn `uv run --directory backend python -m hoicon.agents.spike bench --model claude-haiku-4-5 --n 20 --json <tệp>` (và `claude-haiku-5-5`) — FR-015, SC-006 · Verify: `uv run --directory backend python -m hoicon.agents.spike bench --model claude-haiku-5-5 --n 3 --json $SCRATCH/bench.json`

---

## Phase 6: User Story 4 — trần chi tiêu bền (P3, cắt được)

**Độc lập kiểm được bằng**: ghi sẵn `agent_steps.cost_usd` = trần ⇒ router mới trả `budget_exhausted`, không gọi client.

- [x] T021 [US4] Test trước `backend/tests/unit/test_llm_budget.py` (client giả đếm số lần gọi; DB dev + dọn dòng test): `agent_steps` hôm nay cộng = trần ⇒ fallback `budget_exhausted`, 0 lần gọi client; chi tiêu hôm qua (giờ VN, `at` = 23:59 hôm qua) = trần, hôm nay 0 ⇒ được gọi; ranh giới 00:00 VN; lỗi đọc DB ⇒ fallback `budget_unknown`, không gọi client; router không `sessions` ⇒ hành vi cũ (các test `test_llm_router.py` không đổi); giữ chỗ đang bay cộng vào phần đọc từ DB — FR-011, FR-013 · Verify: `uv run --directory backend pytest tests/unit/test_llm_budget.py -q` (đỏ)
- [x] T022 [US4] `backend/src/hoicon/agents/llm_router.py`: `LlmRouter(client, fast_model, budget, sessions=None)`; có `sessions` ⇒ trước khi giữ chỗ đọc `COALESCE(SUM(cost_usd),0)` từ `agent_steps WHERE at >= <00:00 hôm nay giờ Asia/Ho_Chi_Minh>`, `spent = spent_db + tổng giữ chỗ đang bay` (giữ chỗ trừ khi lời gọi xong); lỗi đọc ⇒ `_fallback(result, "budget_unknown")`; `from_settings(sessions=None)`; `spike.deps()` truyền `get_sessionmaker()`; không đổi thứ tự bảo vệ khác (PII, `<untrusted>`, timeout 4 s) — FR-011 · Verify: `uv run --directory backend pytest tests/unit/test_llm_budget.py tests/unit/test_llm_router.py tests/integration -q`

---

## Phase 7: Polish & cross-cutting

- [x] T023 [P] Tài liệu FR-014: `docs/adr/ADR-009*.md` (§9: token + hạn mức đã có, chưa mở Internet tới khi 012 chốt Caddy; §10: công cụ so model sẵn, số chờ khóa — không đổi quyết định mặc định), `docs/DATA-MODEL.md` (dòng `threat_indicators` theo bảng thật, ghi "chỉ HMAC — chưa đồng bộ xuống máy"), `docs/AGENTS.md` (mục MCP: token + hạn mức), `docs/spikes/P1-S4-loi-tac-tu.md` §4, `backend/README.md` (lệnh nạp, tạo token, bench), `docs/MASTER-PLAN.md` §3 (003 spec đầy đủ, 026 bớt phần token) nếu chưa đúng — FR-014 · Verify: review + `python3 scripts/check-spec-trace.py`
- [x] T024 [P] `specs/003-agent-core-mcp-threat/data-model.md` (delta `threat_indicators`, trỏ `docs/DATA-MODEL.md`) và `quickstart.md` (lệnh dựng: nạp seed, tạo token, gọi `curl` tới `/mcp/threat`, bench) — FR-001, FR-014 · Verify: review
- [x] T025 Cổng chất lượng: `uv run --directory backend ruff check . && uv run --directory backend ruff format --check .` · `alembic upgrade head` → `downgrade -1` → `upgrade head` · `uv run --directory backend pytest -q` (≥ 507 + test mới, 0 lỗi) · `time uv run --directory backend hoicon-eval --suite smoke --compare baseline` (so +0 điểm %; thiếu `HOICON_EVAL_DATABASE_URL` ⇒ SKIPPED) · quét `git diff` không có số điện thoại thô/khóa/token; gitleaks file mới (nếu có) — SC-003, SC-004 · Verify: lệnh nêu trên
- [x] T026 Phiên `curl` thật tới `/mcp/threat` (uvicorn dev, token sinh bằng T017, **không** ghi token vào repo/evidence): 401 / 200 / 429 + dòng log tương ứng, kiểm log không chứa h1/token — FR-005, FR-006, FR-009, SC-002 · Verify: ghi output (đã che token) vào evidence.md
- [x] T027 `/speckit-converge` tới 0 finding; `security-privacy-reviewer` + skill `privacy-audit` (sửa hết Critical/High; ghi Medium/Low còn lại); `specs/003-agent-core-mcp-threat/evidence.md` (bảng FR/SC ↔ bằng chứng, BLOCKED: SC-006 chờ P0-08, đo p95 VPS chờ P1-09, Windows chưa chạy); cập nhật dòng P1-S4 trong `docs/ROADMAP.md` + mục "Ghi chú" nếu có ý tưởng ngoài phạm vi; `.handover/LATEST.md` — FR-013, FR-015 · Verify: `python3 scripts/check-spec-trace.py`

---

## Dependencies & thứ tự

- Phase 1 → Phase 2 → US1 (MVP) → US2 → US3 → US4 → Polish. US2 cần US1 (tool tra DB); US3/US4 độc lập với US2 nhưng chạy sau để
  giữ cổng pytest xanh từng bước. Trong Phase 1: T001 ∥ T002. Phase 2: T006 ∥ T004. T017 ∥ T015–T016. T023 ∥ T024.
- Mỗi task: thấy test đỏ → code → chạy `Verify:` → chạy cả `pytest -q` trước khi sang phase kế (rủi ro (a) của plan).
- Cắt trước nếu trễ: US4 (T021–T022) → phần `host`/`--json` của T019. Không cắt T004–T017.

## Implementation strategy

MVP = Phase 1–3 (danh sách trong DB + đồ thị + eval giữ nguyên). Mỗi phase dừng ở checkpoint với pytest xanh và ruff sạch.
