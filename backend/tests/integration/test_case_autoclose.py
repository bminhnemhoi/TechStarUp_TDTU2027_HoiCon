"""Spec 031 FR-008 (SC-005): job `case_autoclose` với đồng hồ giả."""

from collections.abc import AsyncIterator
from datetime import timedelta
from types import SimpleNamespace

import pytest
from case_support import T0, purge_case, seed_case
from sqlalchemy import select

from hoicon.db.models import CaseFile, Incident, IncidentTransition, Job
from hoicon.db.session import get_sessionmaker
from hoicon.services import case_file_service

pytestmark = pytest.mark.integration

LAST_ACTIVITY = T0 + timedelta(minutes=3)  # chuyển trạng thái cuối cùng của sự cố seed


@pytest.fixture
async def world(require_db: None) -> AsyncIterator[SimpleNamespace]:
    w = await seed_case(with_run=False)
    async with get_sessionmaker().begin() as session:
        content = await case_file_service.build_content(session, w.incident)
        session.add(CaseFile(incident_id=w.incident, family_id=w.family, content=content, is_demo=True))
    yield w
    await purge_case(w)


async def state_of(w: SimpleNamespace) -> tuple[str, str]:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, w.incident, populate_existing=True)
        case = await session.scalar(select(CaseFile.status).where(CaseFile.incident_id == w.incident))
    return incident.state, case


async def run(w: SimpleNamespace, days: float) -> int:
    now = LAST_ACTIVITY + timedelta(days=days)
    return await case_file_service.run_autoclose(get_sessionmaker(), now=now, family_id=w.family)


async def test_29_days_keeps_everything_and_31_days_closes_with_system_actor(world: SimpleNamespace) -> None:
    await run(world, 29)
    assert await state_of(world) == ("case_open", "draft")
    await run(world, 31)
    assert await state_of(world) == ("closed", "discarded")
    async with get_sessionmaker()() as session:
        last = await session.scalar(
            select(IncidentTransition)
            .where(IncidentTransition.incident_id == world.incident, IncidentTransition.to_state == "closed")
            .limit(1)
        )
        resume = await session.scalar(
            select(Job).where(Job.idempotency_key.startswith(f"{world.incident}:case_action"))
        )
    assert last.actor == "system" and last.reason == "case_discarded"
    assert resume is not None and resume.payload["value"] == {"case_action": "discard", "actor": "system"}


async def test_an_approved_case_file_keeps_its_status_but_the_incident_still_closes(world: SimpleNamespace) -> None:
    async with get_sessionmaker().begin() as session:
        await case_file_service.apply_action(
            session, world.incident, "approve", actor="guardian", member_id=world.guardian
        )
    await run(world, 31)
    assert await state_of(world) == ("closed", "approved")


async def test_running_twice_is_idempotent(world: SimpleNamespace) -> None:
    await run(world, 31)
    await run(world, 40)
    assert await state_of(world) == ("closed", "discarded")


async def test_the_daily_job_is_scheduled_once_per_day(require_db: None) -> None:
    sessions = get_sessionmaker()
    first = await case_file_service.schedule_daily_autoclose(sessions)
    second = await case_file_service.schedule_daily_autoclose(sessions)
    assert first == second and first.startswith("case_autoclose:")
    async with sessions() as session:
        rows = list(await session.scalars(select(Job).where(Job.idempotency_key == first)))
    assert len(rows) == 1
    async with sessions.begin() as session:
        await session.delete(rows[0])
