import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from hoicon.api.main import app
from hoicon.db.session import get_engine

pytestmark = pytest.mark.integration


async def _db_up() -> bool:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("select 1"))
    except Exception:
        return False
    return True


async def test_readyz_reports_db_up() -> None:
    if not await _db_up():
        pytest.skip("Postgres dev chưa chạy (docker compose -f infra/compose.dev.yml up -d)")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/readyz")
    assert resp.status_code == 200
    assert resp.json()["db"] == "up"


async def test_pgvector_extension_available() -> None:
    if not await _db_up():
        pytest.skip("Postgres dev chưa chạy")
    async with get_engine().connect() as conn:
        ext = await conn.scalar(text("select extname from pg_extension where extname = 'vector'"))
    assert ext == "vector"
