"""Migration 0010 (spec 029): bảng `device_heartbeats`."""

import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import Device, DeviceHeartbeat, Family, Member
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

SLOT = datetime(2026, 12, 1, 3, 15, tzinfo=UTC)


@pytest.fixture
async def device(require_db: None) -> AsyncGenerator[UUID]:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name=f"test-0010-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(fam)
        await session.flush()
        member = Member(family_id=fam.id, role="protected", alias="Bà thử", address_form="bà")
        session.add(member)
        await session.flush()
        dev = Device(
            family_id=fam.id,
            member_id=member.id,
            app_version="0.3.0",
            rules_version="r1",
            device_secret_hash=secrets.token_hex(32),
        )
        session.add(dev)
        await session.flush()
        family_id, device_id = fam.id, dev.id
    yield device_id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": family_id})


async def columns() -> dict[str, Any]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, is_nullable from information_schema.columns "
                    "where table_name = 'device_heartbeats'"
                )
            )
        ).all()
    return {r.column_name: r for r in rows}


async def test_columns_and_no_free_text(require_db: None) -> None:
    cols = await columns()
    assert set(cols) == {"device_id", "slot", "protected"}
    assert all(c.is_nullable == "NO" for c in cols.values())
    assert not [n for n, c in cols.items() if c.data_type in ("character varying", "text", "jsonb")]


async def test_primary_key_is_device_and_slot(device: UUID) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(DeviceHeartbeat(device_id=device, slot=SLOT, protected=True))
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(DeviceHeartbeat(device_id=device, slot=SLOT, protected=False))
    async with get_sessionmaker().begin() as session:  # khung kế tiếp thì được
        session.add(DeviceHeartbeat(device_id=device, slot=SLOT.replace(minute=30), protected=False))


@pytest.mark.parametrize("minute, second", [(7, 0), (15, 1), (14, 59)])
async def test_a_slot_must_be_a_quarter_hour_mark(device: UUID, minute: int, second: int) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(
                DeviceHeartbeat(device_id=device, slot=SLOT.replace(minute=minute, second=second), protected=True)
            )


async def test_the_device_must_exist(require_db: None) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(DeviceHeartbeat(device_id=new_id(), slot=SLOT, protected=True))


async def test_deleting_the_device_cascades(device: UUID) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(DeviceHeartbeat(device_id=device, slot=SLOT, protected=True))
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from devices where id = :d"), {"d": device})
    async with get_sessionmaker()() as session:
        left = (await session.scalars(select(DeviceHeartbeat).where(DeviceHeartbeat.device_id == device))).all()
    assert left == []


async def test_the_slot_index_exists_for_the_retention_job(require_db: None) -> None:
    async with get_engine().connect() as conn:
        names = (
            (await conn.execute(text("select indexname from pg_indexes where tablename = 'device_heartbeats'")))
            .scalars()
            .all()
        )
    assert "ix_device_heartbeats_slot" in names
