from httpx import ASGITransport, AsyncClient

from hoicon import __version__
from hoicon.api.main import app


async def test_healthz_ok_without_database() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}
