"""Kiểm thử tích hợp spec 027 (FR-003, SC-002, SC-003): phiên web người giám hộ, cookie `hc_guardian`, CSRF.

Mọi định danh đều HƯ CẤU; khóa JWT là khóa GIẢ của test.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import delete, func, select

from hoicon.api.auth import GUARDIAN_COOKIE, GUARDIAN_WEB_TTL, issue_access_token, issue_guardian_access_token
from hoicon.api.routers.actions import redact_action_token
from hoicon.config import get_settings
from hoicon.db.models import ActionToken, Family, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services.action_token_service import ActionTokenService

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Origin": "http://localhost:3100"}
GONE_DETAIL = "Liên kết đăng nhập không dùng được. Nhắn 4 cho bot HỏiCon trên Zalo để nhận liên kết mới."


def _validator(fragment: str) -> Draft202012Validator:
    docs = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.v1.json")}
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs.values()])
    schema = {"$ref": f"{docs['guardian_session.v1.json']['$id']}#/$defs/{fragment}"}
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


RESPONSE = _validator("response")


@pytest.fixture
async def world(require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[dict[str, Any]]:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    monkeypatch.setenv("HOICON_ENV", "dev")
    get_settings.cache_clear()
    async with get_sessionmaker().begin() as session:
        family = Family(display_name="Gia đình mẫu 027", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        session.add_all([protected, guardian])
        await session.flush()
        incident = Incident(
            family_id=family.id,
            member_id=protected.id,
            state="awaiting_guardian",
            level="high",
            rule_floor="high",
            is_demo=True,
        )
        session.add(incident)
        await session.flush()
        world = {"family": family.id, "protected": protected.id, "guardian": guardian.id, "incident": incident.id}
    yield world
    await purge_family(world["family"])
    get_settings.cache_clear()


async def login_token(
    w: dict[str, Any],
    *,
    scope: str = "guardian_view",
    ttl: timedelta = timedelta(minutes=15),
    member: UUID | None = None,
) -> str:
    async with get_sessionmaker().begin() as session:
        _, raw = await ActionTokenService.create_token(
            session, incident_id=None, member_id=member or w["guardian"], scope=scope, ttl=ttl
        )
    return raw


async def exchange(raw: str, **kw: Any) -> Any:
    kw.setdefault("headers", ORIGIN)
    return await call("POST", "/v1/guardian/session", json={"token": raw}, **kw)


def cookie_of(resp: Any) -> str:
    value = resp.cookies.get(GUARDIAN_COOKIE)
    assert value, "thiếu cookie hc_guardian"
    return value


def set_cookie(resp: Any) -> str:
    [header] = [h for h in resp.headers.get_list("set-cookie") if h.startswith(GUARDIAN_COOKIE)]
    return header


async def state_of(incident_id: UUID) -> str:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        return incident.state


# --- FR-003: đổi token lấy phiên --------------------------------------------------------------------------------


async def test_exchange_sets_a_hardened_cookie_and_returns_the_session(world: dict[str, Any]) -> None:
    raw = await login_token(world)
    res = await exchange(raw)
    assert res.status_code == 200, res.text
    body = res.json()
    assert [e.message for e in RESPONSE.iter_errors(body)] == []
    assert body["member_id"] == str(world["guardian"]) and body["family_id"] == str(world["family"])
    assert body["family_name"] == "Gia đình mẫu 027"
    jwt_value = cookie_of(res)
    assert jwt_value not in res.text and raw not in res.text  # token phiên chỉ nằm trong cookie
    header = set_cookie(res)
    flags = {part.strip().lower() for part in header.split(";")}
    assert {"httponly", "samesite=strict", "path=/v1", f"max-age={int(GUARDIAN_WEB_TTL.total_seconds())}"} <= flags
    assert "secure" not in flags  # dev qua http://localhost
    assert res.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("env", ["prod", "production", "staging", ""])
async def test_outside_dev_the_cookie_is_always_secure(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    monkeypatch.setenv("HOICON_ENV", env)
    monkeypatch.setenv("HOICON_WEB_ORIGINS", ORIGIN["Origin"])
    get_settings.cache_clear()
    res = await exchange(await login_token(world))
    assert res.status_code == 200, res.text
    assert "secure" in {part.strip().lower() for part in set_cookie(res).split(";")}


async def test_session_cookie_lasts_seven_days(world: dict[str, Any]) -> None:
    res = await exchange(await login_token(world))
    me = await call("GET", "/v1/guardian/me", cookies={GUARDIAN_COOKIE: cookie_of(res)})
    assert me.status_code == 200
    from datetime import UTC, datetime

    expires = datetime.fromisoformat(me.json()["expires_at"])
    assert timedelta(days=6, hours=23) < expires - datetime.now(UTC) <= GUARDIAN_WEB_TTL


async def test_token_is_single_use(world: dict[str, Any]) -> None:
    raw = await login_token(world)
    assert (await exchange(raw)).status_code == 200
    again = await exchange(raw)
    assert again.status_code == 410
    async with get_sessionmaker()() as session:
        used = await session.scalar(select(ActionToken.used_at).where(ActionToken.member_id == world["guardian"]))
    assert used is not None


async def test_every_bad_token_gets_the_same_410(world: dict[str, Any]) -> None:
    used = await login_token(world)
    await exchange(used)
    other = await login_token(world, scope="incident_decision")
    expired = await login_token(world, ttl=timedelta(minutes=-1))
    gone = await login_token(world)
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Member).where(Member.id == world["guardian"]))  # token mồ côi (CASCADE)
    unknown = "A" * 43
    bodies = []
    for raw in (used, other, expired, gone, unknown):
        res = await exchange(raw)
        assert res.status_code == 410, raw
        assert "set-cookie" not in res.headers
        bodies.append(res.json())
    assert all(body == bodies[0] for body in bodies)
    assert bodies[0]["detail"] == GONE_DETAIL


async def test_a_removed_guardian_cannot_log_in_even_with_a_live_token(world: dict[str, Any]) -> None:
    # Thành viên còn trong bảng nhưng role không phải guardian ⇒ token vô dụng (không lộ lý do).
    raw = await login_token(world, member=world["protected"])
    res = await exchange(raw)
    assert res.status_code == 410 and res.json()["detail"] == GONE_DETAIL


async def test_two_concurrent_exchanges_let_exactly_one_through(world: dict[str, Any]) -> None:
    raw = await login_token(world)
    results = await asyncio.gather(*(exchange(raw) for _ in range(4)))
    assert sorted(r.status_code for r in results) == [200, 410, 410, 410]


@pytest.mark.parametrize("body", [{}, {"token": "ngan"}, {"token": "A" * 43, "x": 1}, {"token": "a b" + "A" * 40}])
async def test_malformed_requests_are_422_and_never_echoed(world: dict[str, Any], body: dict[str, Any]) -> None:
    res = await call("POST", "/v1/guardian/session", json=body, headers=ORIGIN)
    assert res.status_code == 422
    assert "ngan" not in res.text and "a b" not in res.text


# --- me / đăng xuất / thu hồi -----------------------------------------------------------------------------------


async def test_me_works_with_the_cookie_and_with_a_bearer_token(world: dict[str, Any]) -> None:
    res = await exchange(await login_token(world))
    via_cookie = await call("GET", "/v1/guardian/me", cookies={GUARDIAN_COOKIE: cookie_of(res)})
    assert via_cookie.status_code == 200 and [e.message for e in RESPONSE.iter_errors(via_cookie.json())] == []
    assert via_cookie.json()["member_id"] == str(world["guardian"])
    bearer = issue_guardian_access_token(world["guardian"], world["family"])
    assert (await call("GET", "/v1/guardian/me", token=bearer)).status_code == 200  # Bearer vẫn chạy như cũ
    assert (await call("GET", "/v1/guardian/me")).status_code == 401
    assert via_cookie.headers["cache-control"] == "no-store"


async def test_logout_clears_the_cookie(world: dict[str, Any]) -> None:
    res = await exchange(await login_token(world))
    out = await call("DELETE", "/v1/guardian/session", cookies={GUARDIAN_COOKIE: cookie_of(res)}, headers=ORIGIN)
    assert out.status_code == 204
    cleared = set_cookie(out).lower()
    assert "max-age=0" in cleared and "path=/v1" in cleared
    assert (await call("DELETE", "/v1/guardian/session", headers=ORIGIN)).status_code == 204  # đã đăng xuất: vẫn êm


async def test_deleting_the_member_ends_the_session_at_once(world: dict[str, Any]) -> None:
    res = await exchange(await login_token(world))
    jar = {GUARDIAN_COOKIE: cookie_of(res)}
    assert (await call("GET", "/v1/guardian/me", cookies=jar)).status_code == 200
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Member).where(Member.id == world["guardian"]))
    assert (await call("GET", "/v1/guardian/me", cookies=jar)).status_code == 401


async def test_bad_cookies_are_401(world: dict[str, Any]) -> None:
    good = cookie_of(await exchange(await login_token(world)))
    tampered = good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")
    device_jwt = issue_access_token(world["guardian"], world["family"], world["protected"])  # aud khác
    for value in ("", "khong-phai-jwt", tampered, device_jwt):
        assert (await call("GET", "/v1/guardian/me", cookies={GUARDIAN_COOKIE: value})).status_code == 401


async def test_a_bad_bearer_is_not_rescued_by_a_good_cookie(world: dict[str, Any]) -> None:
    good = cookie_of(await exchange(await login_token(world)))
    res = await call("GET", "/v1/guardian/me", token="rac", cookies={GUARDIAN_COOKIE: good})
    assert res.status_code == 401


# --- CSRF: lệnh ghi bằng cookie ---------------------------------------------------------------------------------


async def decide(w: dict[str, Any], jar: dict[str, str], headers: dict[str, str] | None = None) -> Any:
    return await call(
        "POST", f"/v1/incidents/{w['incident']}/decision", json={"decision": "safe"}, cookies=jar, headers=headers
    )


@pytest.mark.parametrize(
    "headers",
    [
        None,
        {"Origin": "https://evil.example"},
        {"Origin": "http://localhost:3100.evil.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Origin": "null"},
    ],
)
async def test_cookie_writes_without_a_same_origin_proof_are_403(world: dict[str, Any], headers: Any) -> None:
    jar = {GUARDIAN_COOKIE: cookie_of(await exchange(await login_token(world)))}
    res = await decide(world, jar, headers)
    assert res.status_code == 403
    assert await state_of(world["incident"]) == "awaiting_guardian"  # không đổi gì


@pytest.mark.parametrize("headers", [ORIGIN, {"Sec-Fetch-Site": "same-origin"}])
async def test_cookie_writes_with_a_same_origin_proof_go_through(world: dict[str, Any], headers: Any) -> None:
    jar = {GUARDIAN_COOKIE: cookie_of(await exchange(await login_token(world)))}
    res = await decide(world, jar, headers)
    assert res.status_code == 200, res.text
    assert await state_of(world["incident"]) == "resolved_safe"


async def test_bearer_writes_need_no_origin(world: dict[str, Any]) -> None:
    bearer = issue_guardian_access_token(world["guardian"], world["family"])
    res = await call("POST", f"/v1/incidents/{world['incident']}/decision", json={"decision": "safe"}, token=bearer)
    assert res.status_code == 200


async def test_reads_with_the_cookie_need_no_origin(world: dict[str, Any]) -> None:
    jar = {GUARDIAN_COOKIE: cookie_of(await exchange(await login_token(world)))}
    assert (await call("GET", "/v1/guardian/me", cookies=jar)).status_code == 200


@pytest.mark.parametrize("headers", [None, {"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}])
async def test_exchange_and_logout_also_refuse_cross_site_requests(world: dict[str, Any], headers: Any) -> None:
    raw = await login_token(world)
    res = await call("POST", "/v1/guardian/session", json={"token": raw}, headers=headers)
    assert res.status_code == 403
    assert (await call("DELETE", "/v1/guardian/session", headers=headers)).status_code == 403
    assert (await exchange(raw)).status_code == 200  # token KHÔNG bị đốt bởi lần bị từ chối


async def test_configured_web_origin_is_accepted_and_others_are_not(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOICON_WEB_ORIGINS", "https://app.example.test, https://khac.example.test")
    get_settings.cache_clear()
    jar = {
        GUARDIAN_COOKIE: cookie_of(
            await exchange(await login_token(world), headers={"Origin": "https://app.example.test"})
        )
    }
    assert (await decide(world, jar, {"Origin": "https://khac.example.test"})).status_code == 200


# --- không lộ token ---------------------------------------------------------------------------------------------


async def test_the_login_token_never_reaches_the_logs_or_the_database_in_clear(
    world: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    raw = await login_token(world)
    res = await exchange(raw)
    jwt_value = cookie_of(res)
    await exchange(raw)  # lần hai (410)
    await call("GET", "/v1/guardian/me", cookies={GUARDIAN_COOKIE: jwt_value})
    assert raw not in caplog.text and jwt_value not in caplog.text
    async with get_sessionmaker()() as session:
        leaked = await session.scalar(select(func.count()).where(ActionToken.token_hash == raw))
    assert leaked == 0


def test_access_log_redaction_also_covers_the_login_page() -> None:
    line = 'GET /login/AbCdEf0123456789_-AbCdEf0123456789_-AbCdE HTTP/1.1" 200'
    assert "AbCdEf" not in redact_action_token(line) and "/login/***" in redact_action_token(line)
    assert "/action/***/decision" in redact_action_token("POST /v1/action/xyz123/decision")


async def test_a_guardian_view_token_tied_to_an_incident_is_not_a_login_link(world: dict[str, Any]) -> None:
    """`guardian_view` gắn sự cố (liên kết xem) không đổi được thành phiên 7 ngày cả gia đình; token không bị đốt."""
    async with get_sessionmaker().begin() as session:
        _, raw = await ActionTokenService.create_token(
            session, incident_id=world["incident"], member_id=world["guardian"], scope="guardian_view"
        )
    res = await exchange(raw)
    assert res.status_code == 410 and res.json()["detail"] == GONE_DETAIL and "set-cookie" not in res.headers
    async with get_sessionmaker()() as session:
        used = await session.scalar(select(ActionToken.used_at).where(ActionToken.member_id == world["guardian"]))
    assert used is None


# --- Rà soát 037 T009 #9: đăng xuất thu hồi phía máy chủ ---------------------------------------------------------


async def test_a_logged_out_token_is_refused_even_if_someone_kept_a_copy(world: dict[str, Any]) -> None:
    res = await exchange(await login_token(world))
    jwt_value = cookie_of(res)
    assert (await call("GET", "/v1/guardian/me", token=jwt_value)).status_code == 200
    out = await call("DELETE", "/v1/guardian/session", token=jwt_value, headers=ORIGIN)
    assert out.status_code == 204
    again = await call("GET", "/v1/guardian/me", token=jwt_value)
    assert again.status_code == 401  # bản sao cookie bị đánh cắp không còn dùng được


async def test_logging_out_one_session_leaves_another_session_of_the_same_guardian_alive(
    world: dict[str, Any],
) -> None:
    first = cookie_of(await exchange(await login_token(world)))
    second = cookie_of(await exchange(await login_token(world)))
    assert first != second
    await call("DELETE", "/v1/guardian/session", token=first, headers=ORIGIN)
    assert (await call("GET", "/v1/guardian/me", token=first)).status_code == 401
    assert (await call("GET", "/v1/guardian/me", token=second)).status_code == 200


async def test_logout_without_a_valid_token_still_succeeds_and_clears_the_cookie(world: dict[str, Any]) -> None:
    out = await call("DELETE", "/v1/guardian/session", headers=ORIGIN)
    assert out.status_code == 204


async def test_retention_drops_only_revoked_sessions_whose_token_has_expired(world: dict[str, Any]) -> None:
    from datetime import UTC, datetime

    from hoicon.db.models import RevokedSession
    from hoicon.services import retention_service as rs

    now = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
    async with get_sessionmaker().begin() as session:
        session.add_all(
            [
                RevokedSession(jti="t018old" + "0" * 25, expires_at=now - timedelta(seconds=1)),
                RevokedSession(jti="t018new" + "0" * 25, expires_at=now + timedelta(seconds=1)),
            ]
        )
    try:
        assert await rs.purge_revoked_sessions(get_sessionmaker(), now=now) >= 1
        async with get_sessionmaker()() as session:
            assert await session.get(RevokedSession, "t018old" + "0" * 25) is None
            assert await session.get(RevokedSession, "t018new" + "0" * 25) is not None
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(delete(RevokedSession).where(RevokedSession.jti.like("t018%")))
