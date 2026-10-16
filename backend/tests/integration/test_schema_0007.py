"""Migration 0007 (spec 026): verifications, threat_indicators.bucket_enc, consents.purpose += lookups."""

import os
import secrets
import subprocess
import sys
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import item, purge_family
from sqlalchemy import select, text
from sqlalchemy.exc import DataError, DBAPIError, IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Family, Incident, Member, Verification
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

HEX64 = "ab" * 32  # chuỗi giả, không phải băm của dữ liệu thật
BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    """Gia đình + thành viên + sự cố giả; dọn cuối test (xóa gia đình kéo theo sự cố và xác minh)."""
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0007-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        incident = Incident(family_id=family.id, member_id=member.id, level="high", rule_floor="high")
        session.add(incident)
        await session.flush()
        ids = {"family": family.id, "member": member.id, "incident": incident.id}
    yield ids
    await purge_family(ids["family"])


def verification(ids: dict[str, UUID], **changes: Any) -> Verification:
    base: dict[str, Any] = {
        "id": new_id(),
        "family_id": ids["family"],
        "incident_id": ids["incident"],
        "actor": "device",
        "actor_id": ids["member"],
        "kind": "phone",
        "via": "typed",
        "subject_kid": 1,
        "subject_hmac": HEX64,
        "last3": "123",
        "verdict": "unknown",
        "confidence": 0,
    }
    return Verification(**{**base, **changes})


async def columns(table: str) -> dict[str, Any]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, is_nullable from information_schema.columns where table_name = :t"
                ),
                {"t": table},
            )
        ).all()
    return {r.column_name: r for r in rows}


async def test_verifications_columns_and_defaults(world: dict[str, UUID]) -> None:
    cols = await columns("verifications")
    assert set(cols) == {
        "id",
        "family_id",
        "incident_id",
        "actor",
        "actor_id",
        "kind",
        "via",
        "subject_kid",
        "subject_hmac",
        "last3",
        "verdict",
        "confidence",
        "sources",
        "list_version",
        "is_demo",
        "at",
    }
    assert cols["incident_id"].is_nullable == "YES"
    assert cols["actor_id"].is_nullable == "YES"
    assert cols["last3"].is_nullable == "YES"
    async with get_sessionmaker().begin() as session:
        session.add(verification(world))
    async with get_sessionmaker()() as session:
        row = (
            await session.execute(select(Verification).where(Verification.family_id == world["family"]))
        ).scalar_one()
    assert row.sources == []
    assert row.is_demo is False
    assert row.at is not None


async def test_no_column_can_hold_a_raw_phone_h1_or_url() -> None:
    for table in ("verifications", "threat_indicators"):
        for name in await columns(table):
            assert not any(bad in name for bad in ("h1", "phone", "url")), f"{table}.{name}"


@pytest.mark.parametrize(
    "bad",
    [
        {"actor": "robot"},
        {"kind": "email"},
        {"via": "sms"},
        {"verdict": "maybe"},
        {"subject_hmac": "AB" * 32},
        {"subject_hmac": "ab" * 31},
        {"last3": "12a"},
        {"last3": "1234"},
        {"confidence": 1.5},
        {"confidence": -0.1},
    ],
    ids=lambda b: next(iter(b)) + "=" + str(next(iter(b.values()))),
)
async def test_verification_check_constraints(world: dict[str, UUID], bad: dict[str, Any]) -> None:
    with pytest.raises((IntegrityError, DataError)):
        async with get_sessionmaker().begin() as session:
            session.add(verification(world, **bad))


@pytest.mark.parametrize("kind", ["phone", "url", "account"])
@pytest.mark.parametrize("verdict", ["safe", "warning", "dangerous", "unknown"])
async def test_verification_accepts_every_documented_kind_and_verdict(
    world: dict[str, UUID], kind: str, verdict: str
) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(verification(world, kind=kind, verdict=verdict, last3=None if kind != "phone" else "123"))


async def test_unique_call_verification_is_idempotent_per_incident(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(verification(world, actor="system", actor_id=None, via="call"))
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(verification(world, actor="system", actor_id=None, via="call"))


async def test_typed_lookups_of_the_same_subject_may_repeat(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(verification(world, via="typed"))
        session.add(verification(world, via="typed"))
        session.add(verification(world, via="qr"))
        session.add(verification(world, incident_id=None, via="call"))  # NULL không đụng UNIQUE một phần
        session.add(verification(world, incident_id=None, via="call"))


async def test_deleting_the_family_cascades_to_verifications() -> None:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0007-cascade-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        incident = Incident(family_id=family.id, member_id=member.id, level="high", rule_floor="high")
        session.add(incident)
        await session.flush()
        ids = {"family": family.id, "member": member.id, "incident": incident.id}
        session.add(verification(ids))
        session.add(verification(ids, incident_id=None))
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": ids["family"]})
    async with get_sessionmaker()() as session:
        left = (
            await session.execute(text("select count(*) from verifications where family_id = :f"), {"f": ids["family"]})
        ).scalar_one()
    assert left == 0


async def test_deleting_the_incident_cascades_to_its_verifications(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(verification(world))
        session.add(verification(world, incident_id=None))
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from incidents where id = :i"), {"i": world["incident"]})
    async with get_sessionmaker()() as session:
        rows = (
            await session.execute(
                text("select incident_id from verifications where family_id = :f"), {"f": world["family"]}
            )
        ).all()
    assert [r.incident_id for r in rows] == [None]


async def test_threat_indicator_has_a_nullable_bucket_enc_column() -> None:
    cols = await columns("threat_indicators")
    assert cols["bucket_enc"].is_nullable == "YES"
    assert cols["bucket_enc"].data_type == "character varying"


async def test_consent_for_lookups_is_recorded(world: dict[str, UUID]) -> None:
    entry = item("lookups")
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world["family"],
                member_id=world["member"],
                purpose=entry["purpose"],
                granted=True,
                consent_version="v1.0",
                text_sha256=HEX64,
                channel="app",
            )
        )
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(
                Consent(
                    family_id=world["family"],
                    member_id=world["member"],
                    purpose="sell_data",
                    granted=True,
                    consent_version="v1.0",
                    text_sha256=HEX64,
                    channel="app",
                )
            )


def _alembic(*args: str) -> None:
    env = {**os.environ, "PYTHONPATH": str(BACKEND / "src")}
    subprocess.run(  # noqa: S603 - lệnh cố định của chính repo, không có đầu vào ngoài
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND,
        env=env,
        check=True,
        capture_output=True,
    )


async def test_downgrade_then_upgrade_survives_existing_lookups_consent(world: dict[str, UUID]) -> None:
    """Trigger chặn DELETE `consents` ⇒ CHECK cũ phải dựng bằng NOT VALID để dòng `lookups` đã có không cản hạ cấp."""
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world["family"],
                member_id=world["member"],
                purpose="lookups",
                granted=True,
                consent_version="v1.0",
                text_sha256=HEX64,
                channel="app",
            )
        )
    await get_engine().dispose()
    try:
        _alembic("downgrade", "0006")
        # Sau hạ cấp: mục đích mới bị chặn ghi thêm, dòng cũ vẫn còn nguyên.
        async with get_engine().begin() as conn:
            kept = (await conn.execute(text("select count(*) from consents where purpose = 'lookups'"))).scalar_one()
            assert kept == 1
            with pytest.raises(DBAPIError):
                async with conn.begin_nested():
                    await conn.execute(
                        text(
                            "insert into consents (id, family_id, member_id, purpose, granted, consent_version,"
                            " text_sha256, channel)"
                            " values (gen_random_uuid(), :f, :m, 'lookups', true, 'v1', :h, 'app')"
                        ),
                        {"f": world["family"], "m": world["member"], "h": HEX64},
                    )
        assert "verifications" not in {r for r in await _tables()}
    finally:
        await get_engine().dispose()
        _alembic("upgrade", "head")
        await get_engine().dispose()
    assert "verifications" in set(await _tables())


async def _tables() -> list[str]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(text("select table_name from information_schema.tables where table_schema = 'public'"))
        ).all()
    return [r.table_name for r in rows]
