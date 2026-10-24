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


# --- Sửa theo rà soát bảo mật T012/T013 (High #1, #2; Medium #3, #6) ---------------------------------------------


async def sim_incident(w: SimpleNamespace, *, sim: bool) -> Any:
    """Sự cố đang chờ người giám hộ của gia đình demo; `sim=True` ⇒ gắn thiết bị nhãn `sim:`."""
    from hoicon.db.models import Device, Incident

    async with get_sessionmaker().begin() as session:
        member = await session.scalar(
            select(Member.id).where(Member.family_id == w.demo.family, Member.role == "protected")
        )
        device = Device(
            family_id=w.demo.family, member_id=member, platform="web", label="sim:fake_police_001" if sim else None,
            app_version="sim-1", rules_version="sim-1", device_secret_hash=secrets.token_hex(32),
        )  # fmt: skip
        session.add(device)
        await session.flush()
        incident = Incident(
            family_id=w.demo.family, member_id=member, device_id=device.id, state="awaiting_guardian",
            level="high", rule_floor="high", is_demo=True,
        )  # fmt: skip
        session.add(incident)
        await session.flush()
        return incident.id


async def test_a_guest_cannot_write_the_case_file(world: SimpleNamespace) -> None:
    cookie = guest_cookie(await join((await new_code(world))["code"]))
    incident = await sim_incident(world, sim=True)
    res = await call(
        "POST",
        f"/v1/guardian/incidents/{incident}/case-file",
        json={"action": "discard"},
        cookies=cookie,
        headers=ORIGIN,
    )
    assert res.status_code == 403


async def test_a_guest_decides_only_on_simulated_incidents(world: SimpleNamespace) -> None:
    cookie = guest_cookie(await join((await new_code(world))["code"]))
    real_demo = await sim_incident(world, sim=False)  # sự cố demo thường: khách KHÔNG được đụng
    res = await call(
        "POST", f"/v1/incidents/{real_demo}/decision", json={"decision": "safe"}, cookies=cookie, headers=ORIGIN
    )
    assert res.status_code == 403
    simulated = await sim_incident(world, sim=True)
    res = await call(
        "POST", f"/v1/incidents/{simulated}/decision", json={"decision": "safe"}, cookies=cookie, headers=ORIGIN
    )
    assert res.status_code == 200, res.text


async def test_a_guest_session_dies_with_the_gate_and_with_a_reset(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    cookie = guest_cookie(await join((await new_code(world))["code"]))
    assert (await call("GET", "/v1/guardian/me", cookies=cookie)).status_code == 200
    monkeypatch.setenv("HOICON_SIM_ENABLED", "false")
    get_settings.cache_clear()
    assert (await call("GET", "/v1/guardian/me", cookies=cookie)).status_code == 401  # cổng tắt ⇒ phiên khách vô hiệu
    monkeypatch.setenv("HOICON_SIM_ENABLED", "true")
    get_settings.cache_clear()
    assert (await call("GET", "/v1/guardian/me", cookies=cookie)).status_code == 200
    assert (await call("POST", "/v1/sim/reset", token=world.demo.token, headers=ORIGIN)).status_code == 200
    assert (
        await call("GET", "/v1/guardian/me", cookies=cookie)
    ).status_code == 401  # đặt lại ⇒ phiên khách của mã đó chết ngay
    assert (
        await call("GET", "/v1/guardian/me", token=world.demo.token)
    ).status_code == 200  # người trình bày không bị ảnh hưởng


async def test_scanning_a_revoked_or_expired_code_is_not_counted_as_a_guess(world: SimpleNamespace) -> None:
    code = (await new_code(world))["code"]
    assert (
        await call("POST", "/v1/sim/reset", token=world.demo.token, headers=ORIGIN)
    ).status_code == 200  # thu hồi mã
    statuses = {(await join(code)).status_code for _ in range(booth.MAX_FAILURES_PER_CLIENT + 5)}
    assert statuses == {404}  # QR cũ dán sẵn không khóa cả Wi-Fi gian
    fresh = (await new_code(world))["code"]
    assert (await join(fresh)).status_code == 200  # khách có mã mới vẫn vào được


# --- T017: Medium còn lại của rà soát T013 -----------------------------------------------------------


async def guests_of() -> int:
    async with get_sessionmaker()() as session:
        return int(await session.scalar(select(BoothJoinCode.guests)) or 0)


async def test_a_guest_who_rejoins_with_a_live_session_does_not_use_up_the_50(world: SimpleNamespace) -> None:
    """#4: một khách bấm "Vào xem" lặp lại (cookie còn sống, cùng mã) không được làm đầy mã của người khác."""
    code = (await new_code(world))["code"]
    first = await join(code)
    cookie = guest_cookie(first)
    for _ in range(3):
        again = await join(code, cookies=cookie)
        assert again.status_code == 200
        guest_cookie(again)  # vẫn được cấp phiên mới
    assert await guests_of() == 1
    assert (await join(code)).status_code == 200  # không có cookie ⇒ khách mới
    assert await guests_of() == 2


async def test_a_rejoining_guest_is_let_in_even_when_the_code_is_full_but_a_stranger_is_not(
    world: SimpleNamespace,
) -> None:
    code = (await new_code(world))["code"]
    cookie = guest_cookie(await join(code))
    async with get_sessionmaker().begin() as session:
        await session.execute(update(BoothJoinCode).values(guests=50))
    assert (await join(code, cookies=cookie)).status_code == 200
    assert (await join(code)).status_code == 404
    assert await guests_of() == 50


async def test_a_session_of_another_or_revoked_code_does_not_skip_the_count(world: SimpleNamespace) -> None:
    old = (await new_code(world))["code"]
    stale = guest_cookie(await join(old))
    assert (await call("POST", "/v1/sim/reset", token=world.demo.token, headers=ORIGIN)).status_code == 200
    fresh = (await new_code(world))["code"]
    assert (await join(fresh, cookies=stale)).status_code == 200  # cookie của mã cũ không miễn đếm cho mã mới
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(BoothJoinCode.guests).where(BoothJoinCode.revoked_at.is_(None))) == 1


async def test_the_code_hash_uses_its_own_key_not_the_jwt_key(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """#8: khóa HMAC của mã tách khỏi khóa ký JWT."""
    monkeypatch.setenv("HOICON_BOOTH_CODE_KEY", "booth-test-key-" + "b" * 32)  # gitleaks:allow — khóa GIẢ cho test
    get_settings.cache_clear()
    base = booth.code_hash("ABCDEF")
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "another-jwt-key-" + "j" * 32)  # gitleaks:allow
    get_settings.cache_clear()
    assert booth.code_hash("ABCDEF") == base  # đổi khóa JWT không đổi băm mã
    monkeypatch.setenv("HOICON_BOOTH_CODE_KEY", "other-booth-key-" + "c" * 32)  # gitleaks:allow
    get_settings.cache_clear()
    assert booth.code_hash("ABCDEF") != base


def hmac_with_jwt_key(code: str) -> str:
    import hashlib
    import hmac

    return hmac.new(JWT_KEY.encode(), f"hoicon:booth-join:v1:{code}".encode(), hashlib.sha256).hexdigest()


async def test_in_dev_the_booth_key_falls_back_to_a_subkey_of_the_jwt_key(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("HOICON_BOOTH_CODE_KEY", raising=False)
    get_settings.cache_clear()
    assert get_settings().is_dev_env
    assert booth.code_hash("ABCDEF") != hmac_with_jwt_key("ABCDEF")  # khóa con, không phải chính khóa JWT
    assert (await join((await new_code(world))["code"])).status_code == 200


async def test_outside_dev_without_the_booth_key_codes_are_closed_and_readyz_names_it(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.api.main import missing_keys

    monkeypatch.setenv("HOICON_ENV", "prod")
    monkeypatch.delenv("HOICON_BOOTH_CODE_KEY", raising=False)
    get_settings.cache_clear()
    assert "booth_code_key" in missing_keys()  # cổng mô phỏng bật mà chưa có khóa riêng
    body = (await call("GET", "/readyz")).json()
    assert "booth_code_key" in body["missing"]
    assert (await call("POST", "/v1/booth/codes", token=world.demo.token, headers=ORIGIN)).status_code == 503
    before = len(booth._global_failures)
    assert (await join("ABCDEF")).status_code == 503  # lỗi của ta, không tính là đoán mò
    assert len(booth._global_failures) == before
    monkeypatch.setenv("HOICON_BOOTH_CODE_KEY", "prod-booth-key-" + "p" * 32)  # gitleaks:allow
    get_settings.cache_clear()
    assert "booth_code_key" not in missing_keys()
    monkeypatch.delenv("HOICON_BOOTH_CODE_KEY")
    monkeypatch.setenv("HOICON_SIM_ENABLED", "false")
    get_settings.cache_clear()
    assert "booth_code_key" not in missing_keys()  # cổng tắt ⇒ không đòi khóa


def test_the_booth_key_name_is_in_the_prod_example_and_the_caddy_log_hides_the_join_code() -> None:
    root = Path(__file__).resolve().parents[3]
    assert "HOICON_BOOTH_CODE_KEY" in (root / "infra" / "env.prod.example").read_text("utf-8")
    caddy = (root / "infra" / "caddy" / "Caddyfile").read_text("utf-8").splitlines()
    redact = next(line for line in caddy if "request>uri" in line)
    pattern = re.search(r'regexp "([^"]+)"', redact).group(1)  # type: ignore[union-attr]
    assert re.sub(pattern, r"\1REDACTED", "/join/ABCDEF?x=1") == "/join/REDACTED?x=1"
    assert re.sub(pattern, r"\1REDACTED", "/login/tok") == "/login/REDACTED"
