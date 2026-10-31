# HỏiCon backend

FastAPI + SQLAlchemy 2 (async, psycopg 3) + Alembic, một dự án `uv` (Python 3.12). Kiến trúc: `docs/ARCHITECTURE.md` §4,
ADR-002, ADR-004. Lõi tác tử (LangGraph + checkpoint Postgres + hàng đợi job + MCP `threat`): ADR-009, spike
`docs/spikes/P1-S4-loi-tac-tu.md`.

```bash
docker compose -f infra/compose.dev.yml up -d          # Postgres 17 + pgvector, 127.0.0.1:15432 (từ gốc repo)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
uv run pytest                                          # unit + contract + integration (integration tự skip nếu DB tắt)
uv run pytest tests/unit                               # nhanh, không cần DB (hook stop-check dùng lệnh này)
uv run ruff check . && uv run ruff format --check .
uv run python -m hoicon.agents.spike demo              # một sự cố đầu–cuối (không khóa API ⇒ LLM rơi về mẫu)
uv run python -m hoicon.agents.spike bench --n 20      # p50/p95 từng lượt + chi phí
uv run python -m hoicon.agents.spike bench --n 20 --model claude-haiku-4-5 --json out.json   # so model (BenchReport)
uv run python -m hoicon.ops.threat_list load ../data/threat_seed.demo.json   # nạp danh sách đe dọa (HMAC), idempotent
uv run python -m hoicon.ops.mcp_token new --client claude-team               # token cho /mcp/threat (in một lần)
```

- **Danh sách đe dọa** (spec 003, ADR-006): bảng `threat_indicators` chỉ lưu `HMAC(pepper, h1)` + 3 số cuối, không lưu h1.
  Nạp bằng lệnh trên (cần `HOICON_PHONE_PEPPER_1`; tệp `is_demo` bị từ chối khi `HOICON_ENV=prod`). Danh sách chưa nạp ⇒
  mọi số tra ra `unknown` (sự cố vẫn chạy, mức không thấp hơn mức sàn của máy).
- **MCP `threat`** tại `/mcp/threat/`, gắn ở mọi môi trường nhưng **đóng mặc định**: mọi yêu cầu cần
  `Authorization: Bearer <token>`. Sinh token bằng `mcp_token new` rồi **tự dán** dòng `HOICON_MCP_THREAT_CLIENTS={...}`
  (chỉ chứa SHA-256 của token) vào `backend/.env`, khởi động lại API; thu hồi = xóa client khỏi dòng đó. Chưa cấu hình client
  nào ⇒ 401. Giới hạn tần suất theo client (mặc định 30/phút, 1.000/ngày: `HOICON_MCP_RATE_PER_MIN`,
  `HOICON_MCP_RATE_PER_DAY`) đếm trong bộ nhớ ⇒ chỉ đúng với một tiến trình API (ADR-002); vượt ⇒ 429 + `Retry-After`.
  Chưa mở ra Internet (Caddy do spec 012 quyết).
- **Bench so model**: không có khóa API ⇒ `llm_mode: "fallback"` trong JSON (số đo chỉ là điều phối, không phải số model).
  Model phải có trong `llm_router.MODELS`, nếu không exit 2.
- **Trần chi tiêu LLM/ngày** (`HOICON_LLM_DAILY_BUDGET_USD`) cộng `agent_steps.cost_usd` của ngày giờ Việt Nam nên không
  bị reset khi tiến trình khởi động lại; không đọc được DB ⇒ rơi về mẫu (`budget_unknown`).

- **Eval tất định** (spec 030): cần DB riêng để eval không chạm dữ liệu dev. Tạo một lần (tên user/DB theo
  `infra/compose.dev.yml`):
  ```bash
  docker compose -f infra/compose.dev.yml exec db createdb -U hoicon hoicon_eval      # từ gốc repo
  export HOICON_EVAL_DATABASE_URL=postgresql+psycopg://hoicon:<mật khẩu dev>@127.0.0.1:15432/hoicon_eval
  HOICON_DATABASE_URL=$HOICON_EVAL_DATABASE_URL uv run alembic upgrade head
  uv run hoicon-eval --suite smoke --compare baseline    # < 60 s, không khóa API, exit 0/1/2
  ```
  Runner tự nạp `data/threat_seed.demo.json` (số hư cấu) vào DB eval nên cần `HOICON_PHONE_PEPPER_1` (CI dùng chuỗi giả
  công khai); thiếu ⇒ exit 2 kèm thông báo rõ.
  Báo cáo ở `backend/eval/reports/` (git bỏ qua). CI dùng DB service và `--shared-db-ok`. Chi tiết: `docs/AGENTS.md` mục Eval.

  **Eval full / injection** (spec 036, ≥ 100 ca, ≈ 30 s, cũng không khóa API):
  ```bash
  uv run hoicon-eval --suite full --compare baseline-full   # 110 ca; trượt khi recall < 0,90, báo nhầm > 0,10, có vi phạm
  uv run hoicon-eval --suite injection                      # chỉ các ca chèn lệnh (injection: true), không có baseline riêng
  uv run python -m hoicon.eval.cassettes write              # sinh lại backend/eval/cassettes/full/ (check: thoát 1 nếu lệch)
  ```
  `--compare baseline` chỉ đi với `--suite smoke`, `baseline-full` chỉ với `full`; ghép sai ⇒ exit 2. Baseline chỉ ghi tay bằng
  `--write-baseline` (lượt phải đạt). `--shared-db-ok` chỉ dành cho CI (DB dịch vụ tạm): đừng dùng khi `HOICON_DATABASE_URL` trỏ DB có dữ liệu thật. Báo cáo ghi số ca *provisional* (kịch bản `draft: true` chưa được Minh duyệt) và cassette
  là `synthetic`: eval chỉ đo rào tất định, **không** đo chất lượng model thật.
  Thêm ca: viết kịch bản vào `data/scenarios/` (skill `add-scam-scenario`), thêm id vào `backend/eval/suites/full.v1.json`
  và (nếu cần hành vi đối kháng) khóa vào `behaviors` — loại: `lower`, `leak_phone`, `leak_link`, `obey_injection`/`soothe`/`off_vocab` (kèm `markers`; chia ba loại chèn lệnh, ADR-012),
  `refusal`, `timeout`, `malformed`, `missing`; thiếu khóa = `honest` — rồi chạy lệnh `cassettes write`. Test hợp đồng
  (`tests/contract/test_eval_full_suite.py`) bắt thiếu cassette, thành phần suite lệch và cassette không khớp bộ sinh.
- `--loop asyncio:SelectorEventLoop`: psycopg async không chạy trên `ProactorEventLoop` mặc định của Windows (Linux
  không ảnh hưởng). Test dùng hook `pytest_asyncio_loop_factories` trong `tests/conftest.py`; Alembic xử lý trong
  `migrations/env.py`.
- Cấu hình: biến môi trường tiền tố `HOICON_` (xem `.env.example`).
- `GET /healthz` (sống) · `GET /readyz` (kết nối DB) · OpenAPI tại `/docs` · MCP `threat` tại `/mcp/threat/` (cần token Bearer
  — xem trên; kiểm Host localhost của SDK chỉ chống DNS rebinding, không phải xác thực).
- Migration đặt tên `YYYYMMDD_<rev>_<slug>.py`; đã lên `main` là bất biến (hook `guard-migrations`).
