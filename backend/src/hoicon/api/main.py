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
from hoicon.api.auth import MIN_KEY_LEN
from hoicon.api.body_limit import BodyLimitMiddleware
from hoicon.api.routers import (
    actions,
    booth,
    consents,
    devices,
    drills,
    elder,
    eval_summary,
    events,
    graphs,
    guardian,
    guardian_drills,
    incidents,
    lookups,
    pairing,
    runs,
    sim,
)
from hoicon.channels.zalo import mock_allowed
from hoicon.config import get_settings
from hoicon.db.session import get_engine
from hoicon.mcp_servers import threat
from hoicon.mcp_servers.auth import McpGuard
from hoicon.services.case_file_service import load_guidance
from hoicon.services.runtime_service import background_worker

logger = logging.getLogger(__name__)
READYZ_TIMEOUT_S = 6


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # MCP gắn bằng mount ⇒ app chủ phải chạy session manager của từng server (MCP SDK v2). Worker job (đồ thị tác
    # tử, bộ hẹn giờ, gửi tin) là task nền cùng tiến trình (ADR-002, spec 024).
    settings = get_settings()
    load_guidance()  # tệp hướng dẫn trình báo sai cấu trúc ⇒ dừng ngay lúc khởi động (spec 031 FR-015)
    if settings.is_dev_env and settings.web_base_url.lower().startswith("https://"):
        # Cookie phiên web chỉ có cờ Secure khi HOICON_ENV ∉ {dev, test, ci}: quên đặt HOICON_ENV ở prod là fail-open.
        logger.warning(
            "HOICON_ENV=%s nhưng HOICON_WEB_BASE_URL là https: cookie phiên người giám hộ KHÔNG có cờ Secure. "
            "Ở máy chủ thật hãy đặt HOICON_ENV=prod.",
            settings.env,
        )
    async with threat.mcp.session_manager.run(), background_worker(settings.run_worker):
        yield


app = FastAPI(title="HỏiCon API", version=__version__, lifespan=lifespan)
# Spec 034: thân yêu cầu tối đa 256 KB cho mọi route (kiểm trước khi router phân tích).
app.add_middleware(BodyLimitMiddleware)


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
app.include_router(runs.router)
app.include_router(guardian.router)
app.include_router(lookups.router)
app.include_router(drills.router)
app.include_router(booth.router)
app.include_router(guardian_drills.router)
app.include_router(actions.router)
app.include_router(elder.router)
app.include_router(graphs.router)
app.include_router(eval_summary.router)
app.include_router(sim.router)  # spec 033: 404 hết khi HOICON_SIM_ENABLED=false
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


def missing_keys() -> list[str]:
    """Tên (không bao giờ giá trị) các khóa bắt buộc đang thiếu: pepper `kid` hiện hành, khóa dữ liệu `kid` hiện hành,
    khóa JWT thiết bị đủ dài. Thiếu chúng ⇒ băm số, mã hóa Zalo ID hoặc ký token hỏng âm thầm (spec 034 FR-006)."""
    settings = get_settings()
    missing: list[str] = []
    pepper = getattr(settings, f"phone_pepper_{settings.phone_pepper_kid}", None)
    if pepper is None or not pepper.get_secret_value():
        missing.append("phone_pepper")
    data_key = getattr(settings, f"data_key_{settings.data_key_kid}", None)
    if data_key is None or not data_key.get_secret_value():
        missing.append("data_key")
    signing = settings.device_jwt_secret
    if signing is None or len(signing.get_secret_value()) < MIN_KEY_LEN:
        missing.append("device_jwt_secret")
    if settings.sim_enabled and not settings.is_dev_env:  # mã gian trưng bày cần khóa riêng (spec 050 T017)
        booth_key = settings.booth_code_key
        if booth_key is None or len(booth_key.get_secret_value()) < MIN_KEY_LEN:
            missing.append("booth_code_key")
    return missing


@app.get("/readyz", tags=["ops"])
async def readyz(response: Response) -> dict[str, object]:
    """Readiness: kết nối được Postgres (trả lời trong ≤ READYZ_TIMEOUT_S kể cả khi DB treo) và đủ khóa bắt buộc."""
    try:
        async with asyncio.timeout(READYZ_TIMEOUT_S):
            async with get_engine().connect() as conn:
                await conn.execute(text("select 1"))
    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        logger.warning("readyz: database unreachable (%s)", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "db": "down"}
    missing = missing_keys()
    if missing:
        logger.error("readyz: thiếu khóa bắt buộc: %s", ", ".join(missing))  # chỉ tên, không giá trị
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "db": "up", "missing": missing}
    settings = get_settings()
    if settings.zalo_mode == "mock" and not mock_allowed(settings):
        # Worker không dựng được kênh gửi ⇒ cảnh báo, xóa dữ liệu, hạn lưu đều đứng: phải thấy ngay ở /readyz.
        logger.error("readyz: HOICON_ENV=%s nhưng HOICON_ZALO_MODE=mock", settings.env)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "db": "up", "misconfigured": ["zalo_mode"]}
    # Chế độ gửi Zalo để ops thấy ngay nếu prod lỡ chạy mock (tin "gửi" bằng mock không tới người nhận).
    return {"status": "ok", "db": "up", "zalo_mode": settings.zalo_mode}
