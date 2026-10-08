import asyncio
import time
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from hoicon import __version__
from hoicon.api import main
from hoicon.api.main import app


async def test_healthz_ok_without_database() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}


class _HangingEngine:
    """Giả lập DB không trả lời (driver kẹt khi kết nối) — lỗi đã gặp với psycopg async trên Windows."""

    @asynccontextmanager
    async def connect(self):
        await asyncio.sleep(3600)
        yield


async def test_readyz_returns_503_quickly_when_db_hangs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "get_engine", lambda: _HangingEngine())
    monkeypatch.setattr(main, "READYZ_TIMEOUT_S", 0.2)
    started = time.monotonic()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable", "db": "down"}
    assert time.monotonic() - started < 2
