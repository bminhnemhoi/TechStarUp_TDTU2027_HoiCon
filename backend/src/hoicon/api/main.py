"""Ứng dụng FastAPI. Chạy dev (Windows cần SelectorEventLoop cho psycopg async):

uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from hoicon import __version__
from hoicon.api import webhooks
from hoicon.config import get_settings
from hoicon.db.session import get_engine
from hoicon.mcp_servers import threat

logger = logging.getLogger(__name__)
READYZ_TIMEOUT_S = 6


# /mcp/threat chỉ gắn ở dev: chưa có bên nào cần gọi qua HTTP (đồ thị gọi thẳng `lookup_h1`), và kiểm Host localhost
# của MCP SDK chỉ chống DNS rebinding — KHÔNG phải xác thực (proxy đổi Host là lọt). Prod: token + giới hạn tần suất
# (P2-11).
MOUNT_MCP = get_settings().env == "dev"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    if not MOUNT_MCP:
        yield
        return
    # MCP gắn bằng mount ⇒ app chủ phải chạy session manager của từng server (MCP SDK v2).
    async with threat.mcp.session_manager.run():
        yield


app = FastAPI(title="HỏiCon API", version=__version__, lifespan=lifespan)
app.include_router(webhooks.router)  # cùng route với ứng dụng con `hoicon.api.webhooks:app` (chỉ nó ra đường hầm)
if MOUNT_MCP:
    app.mount(
        "/mcp/threat",
        threat.mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True),
    )


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict[str, str]:
    """Liveness: tiến trình còn sống (không chạm DB)."""
    return {"status": "ok", "version": __version__}


@app.get("/readyz", tags=["ops"])
async def readyz(response: Response) -> dict[str, str]:
    """Readiness: kết nối được Postgres (trả lời trong ≤ READYZ_TIMEOUT_S kể cả khi DB treo)."""
    try:
        async with asyncio.timeout(READYZ_TIMEOUT_S):
            async with get_engine().connect() as conn:
                await conn.execute(text("select 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        logger.warning("readyz: database unreachable (%s)", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "db": "down"}
    # Chế độ gửi Zalo để ops thấy ngay nếu prod lỡ chạy mock (tin "gửi" bằng mock không tới người nhận).
    return {"status": "ok", "db": "up", "zalo_mode": get_settings().zalo_mode}
