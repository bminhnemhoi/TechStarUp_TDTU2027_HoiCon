"""Spec 050 FR-007 (T012): mã tham gia gian — `POST /v1/booth/codes` (console) và `POST /v1/booth/join` (khách).

Mã chỉ lưu dạng băm; hạn ≤ 10 phút; ≤ 50 khách/mã; vô hiệu khi đặt lại; thử sai bị giới hạn; phiên khách chỉ xem và
quyết định. Mọi định danh hư cấu, khóa JWT là khóa GIẢ của test."""

import json
import re
import secrets
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from consent_support import call, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import delete, select, text, update

from hoicon.api.auth import GUARDIAN_COOKIE, issue_guardian_access_token
from hoicon.api.routers import booth
from hoicon.config import get_settings
from hoicon.db.models import BoothJoinCode, Family, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services import sim_service

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Sec-Fetch-Site": "same-origin"}
INVALID = {"detail": "join_code_invalid"}
CODE_RE = re.compile(r"^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$")


def _defs(name: str) -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    base = next(d["$id"] for d in docs if d["$id"].endswith("booth_join.v1.json"))
    return Draft202012Validator({"$ref": f"{base}#/$defs/{name}"}, registry=registry, format_checker=FormatChecker())


CODE, SESSION, REQUEST = _defs("code"), _defs("session"), _defs("request")


@pytest.fixture
async def world(require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[SimpleNamespace]:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    monkeypatch.setenv("HOICON_SIM_ENABLED", "true")
    get_settings.cache_clear()
    booth.reset_limits()
    sim_service.reset()
    w = SimpleNamespace(families=[])
    async with get_sessionmaker().begin() as session:
        for tag, demo in (("demo", True), ("real", False)):
            family = Family(display_name=f"Gia đình Mẫu {tag} {secrets.token_hex(2)}", region="nam", is_demo=demo)
            session.add(family)
            await session.flush()
            guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
            session.add_all([guardian, Member(family_id=family.id, role="protected", alias="Mẹ")])
            await session.flush()
            token = issue_guardian_access_token(guardian.id, family.id)
            setattr(w, tag, SimpleNamespace(family=family.id, guardian=guardian.id, token=token))
            w.families.append(family.id)
    yield w
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(BoothJoinCode).where(BoothJoinCode.family_id.in_(w.families)))
    for family_id in w.families:
        await purge_family(family_id)
    booth.reset_limits()
    get_settings.cache_clear()


async def new_code(w: SimpleNamespace) -> dict[str, Any]:
    res = await call("POST", "/v1/booth/codes", token=w.demo.token, headers=ORIGIN)
    assert res.status_code == 201, res.text
    body = res.json()
    CODE.validate(body)
    return body


async def join(code: str, **kw: Any) -> Any:
    kw.setdefault("headers", ORIGIN)
    return await call("POST", "/v1/booth/join", json={"code": code}, **kw)


def guest_cookie(res: Any) -> dict[str, str]:
    value = res.cookies.get(GUARDIAN_COOKIE)
    assert value, "thiếu cookie phiên khách"
    return {GUARDIAN_COOKIE: value}


# --- tạo mã (console) -------------------------------------------------------------------------------------------------


async def test_a_demo_guardian_creates_a_short_lived_code_in_the_contract(world: SimpleNamespace) -> None:
    body = await new_code(world)
    assert CODE_RE.fullmatch(body["code"]) and body["max_guests"] == 50 and body["is_demo"] is True
    expires = datetime.fromisoformat(body["expires_at"])
    assert timedelta(minutes=9) < expires - datetime.now(UTC) <= timedelta(minutes=10)


async def test_only_a_demo_session_can_create_a_code(world: SimpleNamespace) -> None:
    assert (await call("POST", "/v1/booth/codes", headers=ORIGIN)).status_code == 401
    assert (await call("POST", "/v1/booth/codes", token=world.real.token, headers=ORIGIN)).status_code == 404
    evil = await call("POST", "/v1/booth/codes", token=world.demo.token, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403


async def test_the_database_keeps_only_a_hash_never_the_code(world: SimpleNamespace) -> None:
    body = await new_code(world)
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(BoothJoinCode).where(BoothJoinCode.family_id == world.demo.family))).one()
        dump = json.dumps({c.name: str(getattr(row, c.name)) for c in BoothJoinCode.__table__.columns})
        raw = await session.scalar(
            text("select to_jsonb(b)::text from booth_join_codes b where id = :i"), {"i": row.id}
        )
    assert body["code"] not in dump and body["code"] not in (raw or "")
    assert re.fullmatch(r"[0-9a-f]{64}", row.code_hash)


# --- đổi mã lấy phiên (khách) ---------------------------------------------------------------------------------------


async def test_a_guest_joins_with_the_code_and_gets_a_view_only_demo_session(world: SimpleNamespace) -> None:
    code = (await new_code(world))["code"]
    assert list(REQUEST.iter_errors({"code": code})) == []
    res = await join(code)  # công khai: không cần phiên
    assert res.status_code == 200, res.text
    body = res.json()
    SESSION.validate(body)
    assert body["is_demo"] is True and body["family_alias"].startswith("Gia đình Mẫu")
    assert res.headers["cache-control"] == "no-store"
    cookie = guest_cookie(res)
    assert (await call("GET", "/v1/guardian/me", cookies=cookie)).status_code == 200  # xem được
    assert (await call("GET", "/v1/guardian/incidents", cookies=cookie)).status_code == 200


async def test_the_guest_session_cannot_configure_schedule_start_runs_or_mint_codes(world: SimpleNamespace) -> None:
    cookie = guest_cookie(await join((await new_code(world))["code"]))
    for method, path, body in [
        ("POST", "/v1/booth/codes", None),
        ("POST", "/v1/sim/reset", None),
        ("POST", "/v1/sim/runs", {"scenario_id": "fake_police_safe_account_002"}),
        ("POST", "/v1/guardian/drills", {"member_id": str(world.demo.guardian), "script_id": "drill_x_yyy"}),
    ]:
        res = await call(method, path, json=body, cookies=cookie, headers=ORIGIN)
        assert res.status_code == 403, (path, res.status_code)


@pytest.mark.parametrize("make_bad", ["unknown", "expired", "revoked", "full"])
async def test_a_bad_code_is_always_the_same_404(world: SimpleNamespace, make_bad: str) -> None:
    code = (await new_code(world))["code"]
    probe = code
    async with get_sessionmaker().begin() as session:
        if make_bad == "unknown":
            probe = "AAAAAA" if code != "AAAAAA" else "BBBBBB"
        elif make_bad == "expired":
            await session.execute(update(BoothJoinCode).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        elif make_bad == "revoked":
            await session.execute(update(BoothJoinCode).values(revoked_at=datetime.now(UTC)))
        else:
            await session.execute(update(BoothJoinCode).values(guests=50))
    res = await join(probe)
    assert res.status_code == 404 and res.json() == INVALID  # không phân biệt hạn/hủy/đầy/không có


async def test_each_join_counts_one_guest_up_to_the_limit(world: SimpleNamespace) -> None:
    code = (await new_code(world))["code"]
    async with get_sessionmaker().begin() as session:
        await session.execute(update(BoothJoinCode).values(guests=48))
    assert (await join(code)).status_code == 200 and (await join(code)).status_code == 200  # khách 49 và 50
    assert (await join(code)).status_code == 404  # khách 51 bị từ chối
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(BoothJoinCode.guests)) == 50


async def test_reset_revokes_every_live_code(world: SimpleNamespace) -> None:
    code = (await new_code(world))["code"]
    assert (await call("POST", "/v1/sim/reset", token=world.demo.token, headers=ORIGIN)).status_code == 200
    assert (await join(code)).json() == INVALID


async def test_wrong_attempts_are_rate_limited_but_good_joins_are_not_counted(world: SimpleNamespace) -> None:
    code = (await new_code(world))["code"]
    for _ in range(5):
        assert (await join(code)).status_code == 200  # nhiều khách thật cùng một nguồn (Wi-Fi gian) không bị tính
    statuses = [(await join("ZZZZZZ")).status_code for _ in range(booth.MAX_FAILURES_PER_CLIENT + 2)]
    assert statuses[: booth.MAX_FAILURES_PER_CLIENT] == [404] * booth.MAX_FAILURES_PER_CLIENT
    assert statuses[-1] == 429
    blocked = await join("ZZZZZZ")
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) >= 1
    assert (await join(code)).status_code == 429  # đang bị khóa: kể cả mã đúng cũng phải đợi (chống dò)


async def test_a_malformed_code_is_422_and_does_not_count_as_a_guess(world: SimpleNamespace) -> None:
    for bad in ("abc", "OOOOOO", "ABCDE", "ABCDEFG"):  # chữ thường, ký tự dễ nhầm (O), sai độ dài
        assert (await join(bad)).status_code == 422
    extra = await call("POST", "/v1/booth/join", json={"code": "ABCDEF", "x": 1}, headers=ORIGIN)
    assert extra.status_code == 422


async def test_join_needs_the_same_origin_and_the_gate_open(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    code = (await new_code(world))["code"]
    assert (await join(code, headers={"Origin": "https://evil.example"})).status_code == 403
    monkeypatch.setenv("HOICON_SIM_ENABLED", "false")
    get_settings.cache_clear()
    assert (await join(code)).status_code == 404
    assert (await call("POST", "/v1/booth/codes", token=world.demo.token, headers=ORIGIN)).status_code == 404


async def test_retention_drops_codes_long_after_they_expired(world: SimpleNamespace) -> None:
    from hoicon.services import retention_service as rs

    await new_code(world)
    async with get_sessionmaker().begin() as session:
        await session.execute(update(BoothJoinCode).values(expires_at=datetime.now(UTC) - timedelta(hours=2)))
    assert await rs.purge_booth_codes(get_sessionmaker(), now=datetime.now(UTC)) >= 1
    async with get_sessionmaker()() as session:
        assert (
            await session.scalars(select(BoothJoinCode.id).where(BoothJoinCode.family_id == world.demo.family))
        ).all() == []
