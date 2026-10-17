"""Dọn dữ liệu test của spec 020. `consents` chặn DELETE bằng trigger nên chỉ tắt trigger TRONG giao dịch dọn."""

from typing import Any
from uuid import UUID

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from hoicon.api.main import app
from hoicon.db.session import get_engine

SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


async def call(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json: Any = None,
    host: str = "203.0.113.7",
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
) -> Any:
    """`headers`/`cookies` (spec 027): thêm `Origin`, `Sec-Fetch-Site`, cookie phiên `hc_guardian`."""
    merged = {"Authorization": f"Bearer {token}"} if token else {}
    merged.update(headers or {})
    async with AsyncClient(
        transport=ASGITransport(app=app, client=(host, 50000)), base_url="http://test", cookies=cookies
    ) as client:
        return await client.request(method, path, json=json, headers=merged)


async def pair_device(code: str, *, consent: bool = True, **changes: Any) -> dict[str, Any]:
    """Ghép một thiết bị bằng `POST /v1/pair` thật; ⇒ phản hồi JSON (có `access_token`).

    `consent=True` (mặc định): ghi `core_protection` + `guardian_alerts` qua `POST /v1/consents` thật, như app làm sau
    khi ghép đôi. Spec 034: máy chủ từ chối `POST /v1/events` của người chưa đồng ý `core_protection`."""
    payload = {"code": code, "app_version": "0.2.0", "rules_version": "r1", "platform": "android", **changes}
    resp = await call("POST", "/v1/pair", json=payload)
    assert resp.status_code == 200, resp.text
    paired = resp.json()
    if consent:
        recorded = await call(
            "POST",
            "/v1/consents",
            token=paired["access_token"],
            json={"items": [item("core_protection"), item("guardian_alerts")]},
        )
        assert recorded.status_code == 200, recorded.text
    return paired


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
        # Job của sự cố trong gia đình (đồ thị, hẹn giờ, tin, FCM — spec 024): không có FK, khóa bắt đầu bằng id sự cố.
        await conn.execute(
            text(
                "delete from jobs j using incidents i where i.family_id = :id"
                " and j.idempotency_key like i.id::text || ':%'"
            ),
            {"id": family_id},
        )
        await conn.execute(text("delete from families where id = :id"), {"id": family_id})
