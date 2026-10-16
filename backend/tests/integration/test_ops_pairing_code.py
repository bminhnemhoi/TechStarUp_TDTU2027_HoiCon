"""FR-004: lệnh vận hành sinh mã ghép Zalo cho gia đình dev — chỉ lưu băm, hết hạn 15 phút."""

import re
from datetime import timedelta

import pytest
from sqlalchemy import delete, func, select

from hoicon.db.models import Family, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_pairing_code
from hoicon.ops import pairing_code

pytestmark = pytest.mark.integration


@pytest.fixture
async def cleanup(require_db: None, zalo_env: None):
    names: list[str] = []
    yield names
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Family).where(Family.display_name.in_(names)))


async def test_creates_demo_family_and_a_code_stored_only_as_hash(
    cleanup: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    name = "dev-test-gia-dinh-001"
    cleanup.append(name)
    assert await pairing_code.run(name) == 0
    out = capsys.readouterr().out
    code = re.search(r"\b(\d{6})\b", out)
    assert code, out
    async with get_sessionmaker()() as session:
        family = (await session.scalars(select(Family).where(Family.display_name == name))).one()
        (row,) = (await session.scalars(select(PairingCode).where(PairingCode.family_id == family.id))).all()
        remaining = await session.scalar(select(row.expires_at - func.now()))
    assert family.is_demo is True  # lệnh này chỉ dành cho gia đình dev/demo
    assert row.code_hash == hmac_pairing_code(code.group(1)) and row.code_hash != code.group(1)
    assert row.used_at is None and timedelta(minutes=14) < remaining <= timedelta(minutes=15)
    assert "15 phút" in out and str(family.id) in out


async def test_reuses_the_family_and_issues_distinct_codes(
    cleanup: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    name = "dev-test-gia-dinh-002"
    cleanup.append(name)
    await pairing_code.run(name)
    await pairing_code.run(name)
    codes = list(dict.fromkeys(re.findall(r"\b(\d{6})\b", capsys.readouterr().out)))  # mỗi lần chạy in mã 2 lần
    assert len(codes) == 2
    async with get_sessionmaker()() as session:
        families = (await session.scalars(select(Family).where(Family.display_name == name))).all()
    assert len(families) == 1


async def test_refuses_to_issue_codes_for_a_real_family(cleanup: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    name = "dev-test-gia-dinh-003"
    cleanup.append(name)
    async with get_sessionmaker().begin() as session:
        session.add(Family(display_name=name, region="nam", is_demo=False))
    assert await pairing_code.run(name) == 2
    assert not re.search(r"\b\d{6}\b", capsys.readouterr().out)  # luồng thật đi qua app (spec 020)


def test_family_name_is_validated() -> None:
    with pytest.raises(SystemExit):
        pairing_code.main(["--family", ""])
    with pytest.raises(SystemExit):
        pairing_code.main(["--family", "x" * 65])
