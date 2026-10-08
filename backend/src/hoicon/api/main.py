"""Ứng dụng FastAPI. Chạy dev (Windows cần SelectorEventLoop cho psycopg async):

uv run --directory backend uvicorn hoicon.api.main:app --port 18000 --reload --loop asyncio:SelectorEventLoop
"""

import logging

from fastapi import FastAPI, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from hoicon import __version__
from hoicon.db.session import get_engine

logger = logging.getLogger(__name__)

app = FastAPI(title="HỏiCon API", version=__version__)


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict[str, str]:
    """Liveness: tiến trình còn sống (không chạm DB)."""
    return {"status": "ok", "version": __version__}


@app.get("/readyz", tags=["ops"])
async def readyz(response: Response) -> dict[str, str]:
    """Readiness: kết nối được Postgres."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("select 1"))
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("readyz: database unreachable (%s)", type(exc).__name__)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable", "db": "down"}
    return {"status": "ok", "db": "up"}
