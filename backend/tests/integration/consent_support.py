"""Dọn dữ liệu test của spec 020. `consents` chặn DELETE bằng trigger nên chỉ tắt trigger TRONG giao dịch dọn."""

from typing import Any
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from hoicon.api.main import app
from hoicon.db.session import get_engine

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


async def call(method: str, path: str, *, token: str | None = None, json: Any = None, host: str = "203.0.113.7") -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with AsyncClient(transport=ASGITransport(app=app, client=(host, 50000)), base_url="http://test") as client:
        return await client.request(method, path, json=json, headers=headers)


async def pair_device(code: str, **changes: Any) -> dict[str, Any]:
    """Ghép một thiết bị bằng `POST /v1/pair` thật; ⇒ phản hồi JSON (có `access_token`)."""
    payload = {"code": code, "app_version": "0.2.0", "rules_version": "r1", "platform": "android", **changes}
    resp = await call("POST", "/v1/pair", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def item(purpose: str = "core_protection", granted: bool = True, **changes: Any) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "granted": granted,
        "consent_version": "v1.0",
        "text_sha256": SHA,
        "channel": "app",
        **changes,
    }


async def purge_family(family_id: UUID) -> None:
    async with get_engine().begin() as conn:
        await conn.execute(text("alter table consents disable trigger trg_consents_immutable"))
        await conn.execute(text("delete from consents where family_id = :id"), {"id": family_id})
        await conn.execute(text("alter table consents enable always trigger trg_consents_immutable"))
        await conn.execute(text("delete from families where id = :id"), {"id": family_id})
