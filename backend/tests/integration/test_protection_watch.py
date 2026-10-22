"""Spec 032 FR-002/FR-003/FR-006 (SC-001…SC-003): job `protection_watch` với đồng hồ giả."""

import json
from collections.abc import AsyncIterator
from datetime import timedelta
from types import SimpleNamespace

import pytest
from coach_support import NOW, payload_text, purge, seed_family, vn_utc, watch_jobs
from sqlalchemy import select, update

from hoicon.agents.texts import AI_DISCLOSURE
from hoicon.db.models import Device, Job
from hoicon.db.session import get_sessionmaker
from hoicon.services import coach_service

pytestmark = pytest.mark.integration


@pytest.fixture
async def worlds() -> AsyncIterator[list[SimpleNamespace]]:
    made: list[SimpleNamespace] = []
    yield made
    for w in made:
        await purge(w)


async def make(worlds: list[SimpleNamespace], **kwargs: object) -> SimpleNamespace:
    w = await seed_family(**kwargs)
    worlds.append(w)
    return w


async def run(w: SimpleNamespace, when=NOW, **kwargs: object) -> int:
    return await coach_service.run_protection_watch(get_sessionmaker(), now=when, family_id=w.family, **kwargs)


async def test_23_hours_is_quiet_and_25_hours_sends_one_message(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=23))
    assert await run(w) == 0 and await watch_jobs(w) == []
    async with get_sessionmaker().begin() as session:
        await session.execute(
            update(Device).where(Device.id == w.device).values(last_heartbeat_at=NOW - timedelta(hours=25))
        )
    assert await run(w) == 1
    (job,) = await watch_jobs(w)
    assert job.payload["template"] == "protection_silent" and job.payload["member_id"] == str(w.guardian1)
    assert job.payload["urgent"] is False and job.payload["is_demo"] is False and job.payload["is_drill"] is False
    assert payload_text(job).startswith(AI_DISCLOSURE) and "chưa báo về HỏiCon từ" in payload_text(job)


async def test_48_runs_of_the_same_episode_send_one_message(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=25))
    for hour in range(48):
        await run(w, vn_utc(8) + timedelta(hours=hour % 13))  # nhiều lượt trong giờ cho phép
    assert len(await watch_jobs(w)) == 1


async def test_a_second_episode_after_the_phone_comes_back_gets_a_second_message(
    require_db: None, worlds: list
) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=25))
    await run(w)
    async with get_sessionmaker().begin() as session:  # máy báo về rồi lại im > 24 giờ sau, quá 24 giờ kể từ tin trước
        await session.execute(
            update(Device).where(Device.id == w.device).values(last_heartbeat_at=NOW + timedelta(hours=1))
        )
    later = NOW + timedelta(hours=1) + timedelta(hours=25)
    assert await run(w, later) == 1
    assert len(await watch_jobs(w)) == 2


async def test_at_most_one_message_per_device_per_24_hours(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=25))
    await run(w)
    async with get_sessionmaker().begin() as session:  # đợt mới (mốc khác) nhưng chưa đủ 24 giờ kể từ tin trước
        await session.execute(
            update(Device).where(Device.id == w.device).values(last_heartbeat_at=NOW - timedelta(hours=24, minutes=1))
        )
    assert await run(w, NOW + timedelta(minutes=30)) == 0
    assert len(await watch_jobs(w)) == 1


async def test_permission_off_needs_two_consecutive_unprotected_slots(require_db: None, worlds: list) -> None:
    one = await make(worlds, protected_slots=[True, True, False])
    two = await make(worlds, protected_slots=[True, False, False])
    assert await run(one) == 0
    assert await run(two) == 1
    (job,) = await watch_jobs(two)
    assert job.payload["template"] == "protection_permission_off" and "quyền" in payload_text(job)


async def test_permission_off_episode_starts_at_the_first_false_slot(require_db: None, worlds: list) -> None:
    w = await make(worlds, protected_slots=[True, False, False, False])
    await run(w)
    (job,) = await watch_jobs(w)
    first_false = (NOW - timedelta(minutes=5)).replace(second=0, microsecond=0)
    first_false -= timedelta(minutes=first_false.minute % 15)
    first_false -= timedelta(minutes=15 * 2)  # khung false cũ nhất trong 3 khung cuối
    assert job.idempotency_key == f"protection:{w.device}:{int(first_false.timestamp())}"


async def test_excluded_devices_and_families_get_nothing(require_db: None, worlds: list) -> None:
    stale = NOW - timedelta(hours=30)
    cases = [
        await make(worlds, revoked=True, last_heartbeat=stale),  # thiết bị đã thu hồi
        await make(worlds, demo=True, last_heartbeat=stale),  # gia đình demo
        await make(worlds, consent=False, last_heartbeat=stale),  # chưa đồng ý guardian_alerts
    ]
    for w in cases:
        assert await run(w) == 0 and await watch_jobs(w) == []
    never = await make(worlds, last_heartbeat=None)  # chưa từng gửi heartbeat
    assert await run(never) == 0


async def test_the_flag_turns_the_watch_off(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=30))
    assert await run(w, enabled=False) == 0 and await watch_jobs(w) == []


async def test_quiet_hours_defer_until_seven(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=vn_utc(8, 0, day=18))
    assert await run(w, vn_utc(22, 30, day=19)) == 0 and await watch_jobs(w) == []
    assert await run(w, vn_utc(2, 0)) == 0
    assert await run(w, vn_utc(6, 59)) == 0
    assert await run(w, vn_utc(7, 5)) == 1
    assert len(await watch_jobs(w)) == 1
    assert coach_service.in_quiet_hours(vn_utc(21, 0)) and not coach_service.in_quiet_hours(vn_utc(7, 0))


async def test_the_second_guardian_is_used_when_the_first_has_no_chat(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=26))
    async with get_sessionmaker().begin() as session:
        from hoicon.db.models import Member

        await session.execute(
            update(Member)
            .where(Member.id == w.guardian1)
            .values(zalo_bot_id=None, zalo_user_hmac=None, zalo_hmac_kid=None, zalo_chat_enc=None)
        )
    assert await run(w) == 1
    (job,) = await watch_jobs(w)
    assert job.payload["member_id"] == str(w.guardian2) and job.payload["guardian_rank"] == 2


async def test_no_phone_number_hash_or_package_reaches_messages_jobs_or_steps(require_db: None, worlds: list) -> None:
    w = await make(worlds, last_heartbeat=NOW - timedelta(hours=26), protected_slots=[True, False, False])
    await run(w)
    from hoicon.db.models import AgentRun, AgentStep

    async with get_sessionmaker()() as session:
        jobs = (await session.scalars(select(Job).where(Job.payload["family_id"].astext == str(w.family)))).all()
        steps = (
            await session.scalars(
                select(AgentStep).join(AgentRun, AgentRun.id == AgentStep.run_id).where(AgentRun.graph == "coach")
            )
        ).all()
    blob = json.dumps([[j.payload, j.idempotency_key] for j in jobs] + [s.output for s in steps], ensure_ascii=False)
    for raw in ("0900000", "vn.hoicon", "h1", "+84"):
        assert raw not in blob, raw
    assert any(s.node == "protection_watch" for s in steps)
