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
```

- **Eval tất định** (spec 030): cần DB riêng để eval không chạm dữ liệu dev. Tạo một lần (tên user/DB theo
  `infra/compose.dev.yml`):
  ```bash
  docker compose -f infra/compose.dev.yml exec db createdb -U hoicon hoicon_eval      # từ gốc repo
  export HOICON_EVAL_DATABASE_URL=postgresql+psycopg://hoicon:<mật khẩu dev>@127.0.0.1:15432/hoicon_eval
  HOICON_DATABASE_URL=$HOICON_EVAL_DATABASE_URL uv run alembic upgrade head
  uv run hoicon-eval --suite smoke --compare baseline    # < 60 s, không khóa API, exit 0/1/2
  ```
  Báo cáo ở `backend/eval/reports/` (git bỏ qua). CI dùng DB service và `--shared-db-ok`. Chi tiết: `docs/AGENTS.md` mục Eval.
- `--loop asyncio:SelectorEventLoop`: psycopg async không chạy trên `ProactorEventLoop` mặc định của Windows (Linux
  không ảnh hưởng). Test dùng hook `pytest_asyncio_loop_factories` trong `tests/conftest.py`; Alembic xử lý trong
  `migrations/env.py`.
- Cấu hình: biến môi trường tiền tố `HOICON_` (xem `.env.example`).
- `GET /healthz` (sống) · `GET /readyz` (kết nối DB) · OpenAPI tại `/docs` · MCP `threat` tại `/mcp/threat/` (chỉ gắn khi
  `HOICON_ENV=dev`; kiểm Host localhost chỉ chống DNS rebinding, không phải xác thực — token + giới hạn tần suất ở P2-11).
- Migration đặt tên `YYYYMMDD_<rev>_<slug>.py`; đã lên `main` là bất biến (hook `guard-migrations`).
