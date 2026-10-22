"""Migration 0011 (spec 031): bảng `case_files`."""

import secrets
from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from hoicon.db.models import CaseFile, Family, Incident, Member
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

CONTENT = {"schema_version": 1}


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[SimpleNamespace]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0011-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add_all([guardian, protected])
        await session.flush()
        incident = Incident(
            family_id=family.id, member_id=protected.id, state="case_open", level="high", rule_floor="high"
        )
        session.add(incident)
        await session.flush()
        ids = SimpleNamespace(family=family.id, guardian=guardian.id, incident=incident.id)
    yield ids
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": ids.family})


async def add(world: SimpleNamespace, **values: object) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(CaseFile(incident_id=world.incident, family_id=world.family, content=CONTENT, **values))


async def test_defaults_are_draft_and_template(world: SimpleNamespace) -> None:
    await add(world)
    async with get_sessionmaker()() as session:
        row = await session.scalar(select(CaseFile).where(CaseFile.incident_id == world.incident))
    assert (row.status, row.summary_source, row.is_demo, row.approved_at) == ("draft", "template", False, None)


@pytest.mark.parametrize("field", ["status", "summary_source"])
async def test_check_constraints_reject_unknown_values(world: SimpleNamespace, field: str) -> None:
    with pytest.raises(IntegrityError):
        await add(world, **{field: "khac"})


async def test_one_case_file_per_incident(world: SimpleNamespace) -> None:
    await add(world)
    with pytest.raises(IntegrityError):
        await add(world)


async def test_deleting_the_member_who_approved_sets_null_and_the_incident_cascades(world: SimpleNamespace) -> None:
    await add(world, status="approved", approved_by=world.guardian)
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from members where id = :m"), {"m": world.guardian})
    async with get_sessionmaker()() as session:
        row = await session.scalar(select(CaseFile).where(CaseFile.incident_id == world.incident))
        assert row is not None and row.approved_by is None and row.status == "approved"
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from incidents where id = :i"), {"i": world.incident})
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(CaseFile).where(CaseFile.incident_id == world.incident)) is None


async def test_deleting_the_family_removes_the_case_file(world: SimpleNamespace) -> None:
    await add(world)
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": world.family})
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(CaseFile).where(CaseFile.family_id == world.family)) is None
