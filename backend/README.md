# HỏiCon backend

FastAPI + SQLAlchemy 2 (async, psycopg 3) + Alembic, một dự án `uv` (Python 3.12). Kiến trúc: `docs/ARCHITECTURE.md` §4,
ADR-002, ADR-004. LangGraph/MCP được thêm ở spike P1-S4.

```bash
docker compose -f infra/compose.dev.yml up -d          # Postgres 17 + pgvector, 127.0.0.1:15432 (từ gốc repo)
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
uv run pytest                                          # unit + contract + integration (integration tự skip nếu DB tắt)
uv run pytest tests/unit                               # nhanh, không cần DB (hook stop-check dùng lệnh này)
uv run ruff check . && uv run ruff format --check .
```

- `--loop asyncio:SelectorEventLoop`: psycopg async không chạy trên `ProactorEventLoop` mặc định của Windows (Linux
  không ảnh hưởng). Test dùng hook `pytest_asyncio_loop_factories` trong `tests/conftest.py`; Alembic xử lý trong
  `migrations/env.py`.
- Cấu hình: biến môi trường tiền tố `HOICON_` (xem `.env.example`).
- `GET /healthz` (sống) · `GET /readyz` (kết nối DB) · OpenAPI tại `/docs`.
- Migration đặt tên `YYYYMMDD_<rev>_<slug>.py`; đã lên `main` là bất biến (hook `guard-migrations`).
