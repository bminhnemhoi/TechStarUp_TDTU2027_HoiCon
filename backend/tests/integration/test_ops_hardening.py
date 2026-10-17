"""Spec 034 FR-007: `ops devices revoke`, `ops threat_list unflag --h1-file`, và tra cứu đe dọa ở prod bỏ số hư cấu."""

import hashlib
import secrets
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from consent_support import call, pair_device
from sqlalchemy import delete, func, select

from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import Device, ThreatIndicator
from hoicon.db.session import get_sessionmaker
from hoicon.mcp_servers.threat import lookup_h1
from hoicon.ops import devices as ops_devices
from hoicon.ops import threat_list

pytestmark = pytest.mark.integration

VERSION = "test-spec034-unflag"


def fake_h1(label: str) -> str:
    """h1 GIẢ (băm một nhãn tùy ý), không liên quan người thật."""
    return hashlib.sha256(f"fixture-034:{label}".encode()).hexdigest()


def indicator(label: str) -> dict[str, Any]:
    return {"h1": fake_h1(label), "source": "Nguồn thử nghiệm", "confidence": 0.9, "last3": "123"}


@pytest.fixture
async def threats(require_db: None, fake_pepper: None, fake_data_key: None) -> AsyncGenerator[None]:
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == VERSION))


async def seed(*labels: str, is_demo: bool = False) -> None:
    doc = {"version": VERSION, "is_demo": is_demo, "indicators": [indicator(label) for label in labels]}
    await threat_list.load_seed(get_sessionmaker(), doc, env="dev")


# --- devices revoke ------------------------------------------------------------------------------------------------


async def test_revoke_cuts_the_device_off_at_the_next_request(
    device_world: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    paired = await pair_device(device_world.code)
    token = paired["access_token"]
    me = (await call("GET", "/v1/devices/me", token=token)).json()["device"]
    assert me["device_id"] and (await call("GET", "/v1/devices/me", token=token)).status_code == 200
    args = ops_devices.build_parser().parse_args(["revoke", "--device", me["device_id"]])
    assert await ops_devices.execute(args) == 0
    assert "Đã thu hồi" in capsys.readouterr().out
    assert (await call("GET", "/v1/devices/me", token=token)).status_code == 401  # có hiệu lực ngay, không chờ hết hạn
    async with get_sessionmaker()() as session:
        row = await session.get(Device, __import__("uuid").UUID(me["device_id"]))
    assert row is not None and row.revoked_at is not None


async def test_revoke_is_idempotent_and_reports_a_missing_device(
    device_world: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    token = (await pair_device(device_world.code))["access_token"]
    device_id = (await call("GET", "/v1/devices/me", token=token)).json()["device"]["device_id"]
    parse = ops_devices.build_parser().parse_args
    assert await ops_devices.execute(parse(["revoke", "--device", device_id])) == 0
    first_time = await _revoked_at(device_id)
    assert await ops_devices.execute(parse(["revoke", "--device", device_id])) == 0
    assert "từ trước" in capsys.readouterr().out.splitlines()[-1]
    assert await _revoked_at(device_id) == first_time  # lần hai không đổi mốc thu hồi
    assert await ops_devices.execute(parse(["revoke", "--device", str(new_id())])) == 2
    assert "Không thấy" in capsys.readouterr().out


async def _revoked_at(device_id: str) -> Any:
    from uuid import UUID

    async with get_sessionmaker()() as session:
        return await session.scalar(select(Device.revoked_at).where(Device.id == UUID(device_id)))


async def test_revoking_one_device_leaves_the_others_working(device_world: Any) -> None:
    from hoicon.ops.pairing_code import create_pairing_code

    first = (await pair_device(device_world.code))["access_token"]
    second = (await pair_device(await create_pairing_code(get_sessionmaker(), device_world.family_id)))["access_token"]
    first_id = (await call("GET", "/v1/devices/me", token=first)).json()["device"]["device_id"]
    await ops_devices.execute(ops_devices.build_parser().parse_args(["revoke", "--device", first_id]))
    assert (await call("GET", "/v1/devices/me", token=first)).status_code == 401
    assert (await call("GET", "/v1/devices/me", token=second)).status_code == 200


async def test_outside_dev_revoke_needs_confirm(
    device_world: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    token = (await pair_device(device_world.code))["access_token"]
    device_id = (await call("GET", "/v1/devices/me", token=token)).json()["device"]["device_id"]
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        parse = ops_devices.build_parser().parse_args
        assert await ops_devices.execute(parse(["revoke", "--device", device_id])) == 2
        assert "--confirm" in capsys.readouterr().out
        assert await _revoked_at(device_id) is None
        assert await ops_devices.execute(parse(["revoke", "--device", device_id, "--confirm"])) == 0
        assert await _revoked_at(device_id) is not None
    finally:
        get_settings.cache_clear()


def test_a_device_id_must_be_a_uuid() -> None:
    with pytest.raises(SystemExit):
        ops_devices.build_parser().parse_args(["revoke", "--device", "0900000001"])


# --- threat_list unflag --------------------------------------------------------------------------------------------


async def test_unflag_removes_only_the_listed_numbers(
    threats: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    await seed("alpha", "bravo", "charlie")
    listed = tmp_path / "h1.txt"
    listed.write_text(
        f"# gỡ nhầm\n{fake_h1('alpha')}\n\n{fake_h1('charlie')}\n{fake_h1('khong-co')}\n", encoding="utf-8"
    )
    assert await threat_list.run_unflag(listed, confirm=False) == 0
    out = capsys.readouterr().out
    assert "Đã gỡ cờ: 2" in out and "không thấy: 1" in out
    assert fake_h1("alpha") not in out and fake_h1("charlie") not in out  # KHÔNG in h1
    sessions = get_sessionmaker()
    assert (await lookup_h1(sessions, fake_h1("alpha"))).verdict == "unknown"
    assert (await lookup_h1(sessions, fake_h1("charlie"))).verdict == "unknown"
    assert (await lookup_h1(sessions, fake_h1("bravo"))).verdict == "flagged"  # không bị đụng


async def test_unflag_twice_is_harmless(threats: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    await seed("alpha")
    listed = tmp_path / "h1.txt"
    listed.write_text(fake_h1("alpha") + "\n", encoding="utf-8")
    assert await threat_list.run_unflag(listed, confirm=False) == 0
    assert await threat_list.run_unflag(listed, confirm=False) == 0
    assert "Đã gỡ cờ: 0 · không thấy: 1" in capsys.readouterr().out.splitlines()[-1]


@pytest.mark.parametrize("line", ["0900000001", "+84900000001", "AB" * 32, "ab" * 31, "g" * 64, "ab" * 32 + " extra"])
async def test_a_file_with_anything_but_h1_is_refused_whole_and_echoes_nothing(
    threats: None, tmp_path: Path, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    await seed("alpha")
    listed = tmp_path / "h1.txt"
    listed.write_text(f"{fake_h1('alpha')}\n{line}\n", encoding="utf-8")
    assert await threat_list.run_unflag(listed, confirm=False) == 2
    out = capsys.readouterr().out
    assert line not in out and "0900000001" not in out
    assert (await lookup_h1(get_sessionmaker(), fake_h1("alpha"))).verdict == "flagged"  # không gỡ dở dang


async def test_a_missing_or_huge_file_is_refused(
    threats: None, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert await threat_list.run_unflag(tmp_path / "khong-co.txt", confirm=False) == 2
    huge = tmp_path / "huge.txt"
    huge.write_text("\n".join(secrets.token_hex(32) for _ in range(threat_list.MAX_UNFLAG + 1)), encoding="utf-8")
    assert await threat_list.run_unflag(huge, confirm=False) == 2
    assert "quá" in capsys.readouterr().out


async def test_outside_dev_unflag_needs_confirm(
    threats: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    await seed("alpha")
    listed = tmp_path / "h1.txt"
    listed.write_text(fake_h1("alpha") + "\n", encoding="utf-8")
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        assert await threat_list.run_unflag(listed, confirm=False) == 2
        assert "--confirm" in capsys.readouterr().out
        assert await threat_list.run_unflag(listed, confirm=True) == 0
    finally:
        get_settings.cache_clear()
    async with get_sessionmaker()() as session:
        left = await session.scalar(
            select(func.count()).select_from(ThreatIndicator).where(ThreatIndicator.list_version == VERSION)
        )
    assert left == 0


# --- tra cứu ở prod bỏ số hư cấu -----------------------------------------------------------------------------------


async def test_lookups_in_prod_ignore_demo_rows_but_dev_sees_them(
    threats: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    await seed("demo-number", is_demo=True)
    h1 = fake_h1("demo-number")
    assert (await lookup_h1(get_sessionmaker(), h1)).verdict == "flagged"  # dev/test: thấy số hư cấu
    for env in ("prod", "production", "staging", ""):
        monkeypatch.setenv("HOICON_ENV", env)
        get_settings.cache_clear()
        try:
            assert (await lookup_h1(get_sessionmaker(), h1)).verdict == "unknown", env
        finally:
            get_settings.cache_clear()


async def test_lookups_in_prod_still_find_real_rows(threats: None, monkeypatch: pytest.MonkeyPatch) -> None:
    await seed("real-number", is_demo=False)
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        assert (await lookup_h1(get_sessionmaker(), fake_h1("real-number"))).verdict == "flagged"
    finally:
        get_settings.cache_clear()
