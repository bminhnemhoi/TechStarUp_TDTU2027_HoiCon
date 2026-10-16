"""Spec 028 FR-003 / SC-002 / D2: cờ diễn tập chỉ do máy chủ cấp. Sự kiện tự khai `is_drill`/`drill_id` chỉ được tin khi
khớp một bài `in_progress` của CHÍNH người cao tuổi đó và `occurred_at` nằm trong khung giờ; ngược lại là sự cố THẬT.

Ưu tiên an toàn: nghi ngờ thì xử lý như thật (một cảnh báo thừa ít hại hơn một vụ thật bị coi là diễn tập)."""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from consent_support import pair_device, purge_family
from drill_support import add_drill, me, running_drill_for
from sqlalchemy import select
from test_api_events import make_event, post

from hoicon.agents.texts import AI_DISCLOSURE, DRILL_LABEL
from hoicon.db.ids import new_id
from hoicon.db.models import Family, Incident, Job, Member, RiskEventRecord
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration


@pytest.fixture
async def token(device_world: Any) -> str:
    return (await pair_device(device_world.code))["access_token"]


@pytest.fixture
async def guardian(device_world: Any, token: str) -> None:
    """Cảnh báo nhanh cần một người giám hộ để xếp job."""
    async with get_sessionmaker().begin() as session:
        session.add(Member(family_id=device_world.family_id, role="guardian", guardian_rank=1))


async def send(token: str, drill_id: UUID | str, **changes: Any) -> tuple[dict[str, Any], str]:
    event = make_event(is_drill=True, drill_id=str(drill_id), **changes)
    resp = await post(token, event)
    assert resp.status_code == 200, resp.text
    return resp.json(), event["id"]


async def stored(event_id: str) -> RiskEventRecord:
    async with get_sessionmaker()() as session:
        record = await session.get(RiskEventRecord, UUID(event_id))
    assert record is not None
    return record


async def incident(body: dict[str, Any]) -> Incident:
    async with get_sessionmaker()() as session:
        found = await session.get(Incident, UUID(body["incident_id"]))
    assert found is not None
    return found


async def alert(incident_id: UUID) -> Job:
    async with get_sessionmaker()() as session:
        job = await session.scalar(select(Job).where(Job.idempotency_key == f"{incident_id}:msg:fast_alert"))
    assert job is not None, "cảnh báo nhanh phải được xếp"
    return job


async def assert_treated_as_real(body: dict[str, Any], event_id: str) -> None:
    record = await stored(event_id)
    assert record.is_drill is False and record.drill_id is None
    assert record.payload.get("is_drill") is False and "drill_id" not in record.payload
    found = await incident(body)
    assert found.is_drill is False and found.drill_id is None
    job = await alert(found.id)
    assert job.payload["is_drill"] is False
    assert DRILL_LABEL not in job.payload["text"]  # cảnh báo đi như THẬT
    assert job.payload["text"].startswith(AI_DISCLOSURE)


async def test_a_matching_in_progress_drill_is_trusted(device_world: Any, token: str, guardian: None) -> None:
    drill_id = await running_drill_for(token)
    body, event_id = await send(token, drill_id)
    record = await stored(event_id)
    assert record.is_drill is True and record.drill_id == drill_id
    found = await incident(body)
    assert found.is_drill is True and found.drill_id == drill_id
    job = await alert(found.id)
    assert job.payload["is_drill"] is True and DRILL_LABEL in job.payload["text"]


@pytest.mark.parametrize("edge", ["start", "end"])
async def test_the_window_edges_are_inclusive(device_world: Any, token: str, guardian: None, edge: str) -> None:
    window = {"before": timedelta(0), "after": timedelta(hours=1)}  # sự kiện đúng lúc bắt đầu
    if edge == "end":
        window = {"before": timedelta(hours=1), "after": timedelta(0)}  # sự kiện đúng lúc kết thúc
    drill_id = await running_drill_for(token, **window)
    body, event_id = await send(token, drill_id)
    assert (await stored(event_id)).is_drill is True
    assert (await incident(body)).is_drill is True


async def test_no_drill_at_all_is_a_real_incident(device_world: Any, token: str, guardian: None) -> None:
    body, event_id = await send(token, new_id())
    await assert_treated_as_real(body, event_id)


async def test_another_familys_drill_is_a_real_incident(device_world: Any, token: str, guardian: None) -> None:
    async with get_sessionmaker().begin() as session:
        other = Family(display_name="test-028-guard-other", region="nam", is_demo=True)
        session.add(other)
        await session.flush()
        stranger = Member(family_id=other.id, role="protected")
        session.add(stranger)
        await session.flush()
        ids = (other.id, stranger.id)
    try:
        theirs = await add_drill(ids[0], ids[1])
        body, event_id = await send(token, theirs)
        await assert_treated_as_real(body, event_id)
    finally:
        await purge_family(ids[0])


async def test_another_elder_in_the_same_family_is_a_real_incident(
    device_world: Any, token: str, guardian: None
) -> None:
    async with get_sessionmaker().begin() as session:
        sibling = Member(family_id=device_world.family_id, role="protected")
        session.add(sibling)
        await session.flush()
        sibling_id = sibling.id
    theirs = await add_drill(device_world.family_id, sibling_id)
    body, event_id = await send(token, theirs)
    await assert_treated_as_real(body, event_id)


@pytest.mark.parametrize("status", ["scheduled", "offered", "passed", "failed", "declined", "aborted", "expired"])
async def test_a_drill_that_is_not_in_progress_is_a_real_incident(
    device_world: Any, token: str, guardian: None, status: str
) -> None:
    extra: dict[str, Any] = {"status": status, "started_at": None}
    if status in ("passed", "failed"):
        extra["score"] = 1
    drill_id = await running_drill_for(token, **extra)
    body, event_id = await send(token, drill_id)
    await assert_treated_as_real(body, event_id)


@pytest.mark.parametrize(
    "occurred_at",
    ["2026-12-01T01:00:00Z", "2026-12-01T03:30:00Z"],
    ids=["before-window", "after-window"],
)
async def test_an_event_outside_the_window_is_a_real_incident(
    device_world: Any, token: str, guardian: None, occurred_at: str
) -> None:
    drill_id = await running_drill_for(token)  # khung 02:05–03:05
    body, event_id = await send(token, drill_id, occurred_at=occurred_at)
    await assert_treated_as_real(body, event_id)


async def test_a_drill_id_without_the_flag_is_dropped_too(device_world: Any, token: str, guardian: None) -> None:
    """Không khai `is_drill` mà vẫn kèm `drill_id`: cũng bị bỏ (mọi `drill_id` đều là một lời khai chưa kiểm)."""
    event = make_event(is_drill=False, drill_id=str(new_id()))
    resp = await post(token, event)
    assert resp.status_code == 200
    await assert_treated_as_real(resp.json(), event["id"])


async def test_each_event_in_a_batch_is_judged_on_its_own(device_world: Any, token: str, guardian: None) -> None:
    drill_id = await running_drill_for(token)
    good = make_event(is_drill=True, drill_id=str(drill_id), type="safe_pause_shown", rule_floor="none", rule_id=None)
    bad = make_event(is_drill=True, drill_id=str(new_id()), type="safe_pause_shown", rule_floor="none", rule_id=None)
    resp = await post(token, good, bad)
    assert resp.status_code == 200 and resp.json()["accepted"] == 2
    assert (await stored(good["id"])).is_drill is True
    rejected = await stored(bad["id"])
    assert rejected.is_drill is False and rejected.drill_id is None


async def test_the_rejection_is_logged_without_ids_or_personal_data(
    device_world: Any, token: str, guardian: None, caplog: pytest.LogCaptureFixture
) -> None:
    fake = new_id()
    with caplog.at_level(logging.WARNING, logger="hoicon.api.routers.events"):
        await send(token, fake)
    messages = [r.getMessage() for r in caplog.records if r.name == "hoicon.api.routers.events"]
    assert any("drill flag rejected" in m for m in messages)
    assert not any(str(fake) in m for m in messages)
    device = await me(token)
    assert not any(device["family_id"] in m or device["member_id"] in m for m in messages)


async def test_a_trusted_drill_is_not_logged_as_rejected(
    device_world: Any, token: str, guardian: None, caplog: pytest.LogCaptureFixture
) -> None:
    drill_id = await running_drill_for(token)
    with caplog.at_level(logging.WARNING, logger="hoicon.api.routers.events"):
        await send(token, drill_id)
    assert not any("drill flag rejected" in r.getMessage() for r in caplog.records)
