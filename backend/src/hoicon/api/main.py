"""Ứng dụng FastAPI. Chạy dev (Windows cần SelectorEventLoop cho psycopg async):

uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from hoicon import __version__
from hoicon.api import webhooks
from hoicon.api.routers import actions, consents, devices, elder, events, incidents, pairing
from hoicon.config import get_settings
from hoicon.db.session import get_engine
from hoicon.mcp_servers import threat
from hoicon.mcp_servers.auth import McpGuard
from hoicon.services.runtime_service import background_worker

logger = logging.getLogger(__name__)
READYZ_TIMEOUT_S = 6


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # MCP gắn bằng mount ⇒ app chủ phải chạy session manager của từng server (MCP SDK v2). Worker job (đồ thị tác
    # tử, bộ hẹn giờ, gửi tin) là task nền cùng tiến trình (ADR-002, spec 024).
    async with threat.mcp.session_manager.run(), background_worker(get_settings().run_worker):
        yield


app = FastAPI(title="HỏiCon API", version=__version__, lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    """422 chỉ nêu VỊ TRÍ và loại lỗi, không lặp lại giá trị đã gửi (FastAPI mặc định có `input`): thân yêu cầu có thể
    mang số điện thoại thô/mã ghép bị gửi nhầm, và phản hồi có thể bị log ở proxy (CLAUDE.md luật 1)."""
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors})


app.include_router(pairing.router)
app.include_router(consents.router)
app.include_router(devices.router)
app.include_router(events.router)
app.include_router(incidents.router)
app.include_router(actions.router)
app.include_router(elder.router)
app.include_router(webhooks.router)  # cùng route với ứng dụng con `hoicon.api.webhooks:app` (chỉ nó ra đường hầm)
# /mcp/threat gắn ở MỌI môi trường nhưng đóng mặc định: `McpGuard` đòi token Bearer (chưa cấu hình client nào ⇒ 401)
# và giới hạn tần suất theo client (spec 003, ADR-009 §9). Kiểm Host localhost của MCP SDK chỉ chống DNS rebinding,
# KHÔNG phải xác thực. Có mở ra Internet hay không do Caddy/012 quyết; hạn mức đếm trong bộ nhớ ⇒ chỉ đúng với một
# tiến trình (ADR-002).
app.mount(
    "/mcp/threat",
    McpGuard(threat.mcp.streamable_http_app(streamable_http_path="/", stateless_http=True, json_response=True)),
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
