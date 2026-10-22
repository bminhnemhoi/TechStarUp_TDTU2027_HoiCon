"""Migration 0012 (spec 032): `members.weekly_digest_enabled`."""

import secrets
from collections.abc import AsyncGenerator
from uuid import UUID

import pytest
from sqlalchemy import select, text

from hoicon.db.models import Family, Member
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration


@pytest.fixture
async def family(require_db: None) -> AsyncGenerator[UUID]:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name=f"test-0012-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(fam)
        await session.flush()
        family_id = fam.id
    yield family_id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": family_id})


async def test_column_is_a_non_null_boolean_defaulting_to_true(require_db: None) -> None:
    async with get_engine().connect() as conn:
        row = (
            await conn.execute(
                text(
                    "select data_type, is_nullable, column_default from information_schema.columns "
                    "where table_name = 'members' and column_name = 'weekly_digest_enabled'"
                )
            )
        ).one()
    assert (row.data_type, row.is_nullable) == ("boolean", "NO") and "true" in row.column_default


async def test_new_guardians_receive_the_digest_by_default_and_can_opt_out(family: UUID) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(Member(family_id=family, role="guardian", guardian_rank=1))
    async with get_sessionmaker()() as session:
        member = await session.scalar(select(Member).where(Member.family_id == family))
        assert member.weekly_digest_enabled is True
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update members set weekly_digest_enabled = false where family_id = :f"), {"f": family}
        )
    async with get_sessionmaker()() as session:
        member = await session.scalar(select(Member).where(Member.family_id == family))
        assert member.weekly_digest_enabled is False
