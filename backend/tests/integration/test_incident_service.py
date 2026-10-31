"""Spec 021 (FR-005, FR-006, FR-008, SC-002..SC-004): `IncidentService` — máy trạng thái, khóa lạc quan, advisory."""

import asyncio
import secrets
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, text

from hoicon.db.ids import new_id
from hoicon.db.models import Device, Family, Incident, IncidentTransition, Member, RiskEventRecord
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import RiskEvent
from hoicon.services.incident_service import (
    ALLOWED,
    STATES,
    TERMINAL,
    ConcurrencyConflictError,
    IncidentNotFoundError,
    IncidentService,
    InvalidTransitionError,
)

pytestmark = pytest.mark.integration


@dataclass
class World:
    family_id: UUID
    member_id: UUID
    device_id: UUID
    other_device_id: UUID


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[World]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-021-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        devices = [
            Device(
                family_id=family.id,
                member_id=member.id,
                app_version="0.2.0",
                rules_version="r1",
                device_secret_hash=secrets.token_hex(32),
            )
            for _ in range(2)
        ]
        session.add_all(devices)
        await session.flush()
        ids = World(family.id, member.id, devices[0].id, devices[1].id)
    yield ids
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": ids.family_id})


async def make_incident(world: World, state: str = "detected", **changes: Any) -> UUID:
    """Chèn thẳng một sự cố ở trạng thái bất kỳ (bỏ qua service) để thử từng cạnh của máy trạng thái."""
    base: dict[str, Any] = {
        "family_id": world.family_id,
        "member_id": world.member_id,
        "device_id": world.device_id,
        "state": state,
        "level": "high",
        "rule_floor": "high",
        "closed_at": datetime.now(UTC) if state in TERMINAL else None,
    }
    incident = Incident(**{**base, **changes})
    async with get_sessionmaker().begin() as session:
        session.add(incident)
    return incident.id


async def transition(
    incident_id: UUID, to: str, *, version: int, actor: str = "system", reason: str | None = None
) -> Incident:
    async with get_sessionmaker().begin() as session:
        return await IncidentService.transition(session, incident_id, to, actor, reason, expected_version=version)


async def load(incident_id: UUID) -> Incident:
    async with get_sessionmaker()() as session:
        return await session.get(Incident, incident_id, populate_existing=True)  # type: ignore[return-value]


async def history(incident_id: UUID) -> list[tuple[str | None, str, str]]:
    async with get_sessionmaker()() as session:
        rows = await session.scalars(
            select(IncidentTransition)
            .where(IncidentTransition.incident_id == incident_id)
            .order_by(IncidentTransition.at, IncidentTransition.id)
        )
        return [(r.from_state, r.to_state, r.actor) for r in rows]


# --- tạo sự cố ----------------------------------------------------------------------------------------------------


async def test_create_incident_starts_detected_with_a_first_transition(world: World) -> None:
    async with get_sessionmaker().begin() as session:
        incident = await IncidentService.create_incident(
            session, family_id=world.family_id, member_id=world.member_id, device_id=world.device_id, rule_floor="high"
        )
        incident_id = incident.id
    row = await load(incident_id)
    assert (row.state, row.level, row.rule_floor, row.version, row.closed_at) == ("detected", "high", "high", 1, None)
    assert row.is_drill is False and row.is_demo is True  # is_demo theo gia đình demo
    assert await history(incident_id) == [(None, "detected", "device")]


async def test_level_defaults_to_the_floor_but_never_below_low(world: World) -> None:
    async with get_sessionmaker().begin() as session:
        a = await IncidentService.create_incident(
            session,
            family_id=world.family_id,
            member_id=world.member_id,
            device_id=world.device_id,
            rule_floor="critical",
        )
        b = await IncidentService.create_incident(
            session, family_id=world.family_id, member_id=world.member_id, device_id=world.device_id, rule_floor="none"
        )
        c = await IncidentService.create_incident(
            session,
            family_id=world.family_id,
            member_id=world.member_id,
            device_id=world.device_id,
            rule_floor="medium",
            level="critical",  # đề xuất cao hơn sàn: được nâng
        )
    assert (a.level, b.level, c.level) == ("critical", "low", "critical")


async def test_create_refuses_a_level_below_the_floor(world: World) -> None:
    async with get_sessionmaker().begin() as session:
        with pytest.raises(ValueError, match="rule_floor"):
            await IncidentService.create_incident(
                session,
                family_id=world.family_id,
                member_id=world.member_id,
                device_id=world.device_id,
                rule_floor="high",
                level="low",
            )


async def test_drill_incident_needs_a_drill_id(world: World) -> None:
    async with get_sessionmaker().begin() as session:
        with pytest.raises(ValueError, match="drill_id"):
            await IncidentService.create_incident(
                session,
                family_id=world.family_id,
                member_id=world.member_id,
                device_id=world.device_id,
                rule_floor="high",
                is_drill=True,
            )


# --- chuyển trạng thái --------------------------------------------------------------------------------------------


async def test_happy_path_logs_every_step_and_bumps_the_version(world: World) -> None:
    incident_id = await make_incident(world)
    path = [
        ("assessing", "agent"),
        ("awaiting_guardian", "agent"),
        ("verifying", "guardian"),
        ("rescore", "agent"),
        ("resolved_prevented", "guardian"),
    ]
    for step, (to, actor) in enumerate(path, start=1):
        updated = await transition(incident_id, to, version=step, actor=actor, reason="test")
        assert (updated.state, updated.version) == (to, step + 1)
    row = await load(incident_id)
    assert (row.state, row.version, row.outcome) == ("resolved_prevented", 6, "prevented")
    assert row.closed_at is not None
    assert await history(incident_id) == [
        ("detected", "assessing", "agent"),
        ("assessing", "awaiting_guardian", "agent"),
        ("awaiting_guardian", "verifying", "guardian"),
        ("verifying", "rescore", "agent"),
        ("rescore", "resolved_prevented", "guardian"),
    ]


async def test_case_open_then_closed(world: World) -> None:
    incident_id = await make_incident(world, "rescore")
    await transition(incident_id, "case_open", version=1, actor="guardian")
    assert (await load(incident_id)).closed_at is None  # hồ sơ còn mở
    await transition(incident_id, "closed", version=2, actor="guardian")
    row = await load(incident_id)
    assert (row.state, row.version) == ("closed", 3) and row.closed_at is not None


@pytest.mark.parametrize("source", sorted(STATES))
@pytest.mark.parametrize("target", sorted(STATES))
async def test_every_edge_of_the_state_machine(world: World, source: str, target: str) -> None:
    """Mọi cặp (từ, đến): chỉ cạnh trong `ALLOWED` được qua; còn lại bị từ chối và KHÔNG ghi gì (SC-003)."""
    incident_id = await make_incident(world, source)
    if target in ALLOWED[source]:
        updated = await transition(incident_id, target, version=1)
        assert (updated.state, updated.version) == (target, 2)
        assert (updated.closed_at is not None) == (target in TERMINAL)
        return
    with pytest.raises(InvalidTransitionError):
        await transition(incident_id, target, version=1)
    row = await load(incident_id)
    assert (row.state, row.version) == (source, 1) and await history(incident_id) == []


def test_terminal_states_have_no_exits() -> None:
    assert all(ALLOWED[state] == frozenset() for state in TERMINAL)
    assert {"resolved_safe", "resolved_prevented", "resolved_false_alarm", "resolved_no_response", "closed"} == TERMINAL
    assert set(ALLOWED) == STATES and all(targets <= STATES for targets in ALLOWED.values())


async def test_unknown_state_actor_or_long_reason_is_rejected(world: World) -> None:
    incident_id = await make_incident(world)
    for kwargs in (
        {"to": "exploded"},
        {"to": "assessing", "actor": "hacker"},
        {"to": "assessing", "reason": "x" * 257},
    ):
        with pytest.raises(ValueError):
            await transition(
                incident_id, kwargs["to"], version=1, actor=kwargs.get("actor", "system"), reason=kwargs.get("reason")
            )
    assert (await load(incident_id)).version == 1


async def test_unknown_incident(world: World) -> None:
    with pytest.raises(IncidentNotFoundError):
        await transition(new_id(), "assessing", version=1)


# --- khóa lạc quan + advisory lock ---------------------------------------------------------------------------------


async def test_stale_version_is_refused_and_writes_nothing(world: World) -> None:
    incident_id = await make_incident(world, "awaiting_guardian")
    await transition(incident_id, "verifying", version=1, actor="guardian")  # người giám hộ nhanh hơn bộ hẹn giờ
    with pytest.raises(ConcurrencyConflictError):
        await transition(incident_id, "resolved_no_response", version=1, actor="timer")
    row = await load(incident_id)
    assert (row.state, row.version) == ("verifying", 2)
    assert await history(incident_id) == [("awaiting_guardian", "verifying", "guardian")]


async def test_concurrent_transitions_exactly_one_wins(world: World) -> None:
    """SC-002: 10 bên cùng đọc version 1 rồi cùng chuyển ⇒ đúng một thắng, chín nhận ConcurrencyConflictError."""
    incident_id = await make_incident(world, "awaiting_guardian")
    targets = ["verifying", "resolved_safe", "resolved_prevented", "resolved_false_alarm", "resolved_no_response"] * 2

    async def attempt(to: str) -> str | BaseException:
        try:
            return (await transition(incident_id, to, version=1)).state
        except (ConcurrencyConflictError, InvalidTransitionError) as exc:
            return exc

    results = await asyncio.gather(*(attempt(to) for to in targets))
    wins = [r for r in results if isinstance(r, str)]
    losses = [r for r in results if isinstance(r, ConcurrencyConflictError)]
    assert len(wins) == 1 and len(losses) == 9, results
    row = await load(incident_id)
    assert (row.state, row.version) == (wins[0], 2)
    assert len(await history(incident_id)) == 1  # đúng một dòng nhật ký


async def test_transition_waits_for_the_advisory_lock(world: World) -> None:
    """FR-006: giữ `pg_advisory_xact_lock(hashtext(id))` ở phiên khác ⇒ `transition` phải chờ, không chen ngang."""
    incident_id = await make_incident(world)
    holder = get_sessionmaker()()
    await holder.execute(text("select pg_advisory_xact_lock(hashtext(:i))"), {"i": str(incident_id)})
    task = asyncio.create_task(transition(incident_id, "assessing", version=1))
    await asyncio.sleep(0.4)
    assert not task.done(), "transition đã chạy dù khóa advisory đang bị giữ"
    await holder.rollback()
    await holder.close()
    assert (await asyncio.wait_for(task, 5)).state == "assessing"


# --- liên kết sự kiện ⇒ sự cố (FR-008, SC-004) -------------------------------------------------------------------


def event(**changes: Any) -> RiskEvent:
    base: dict[str, Any] = {
        "id": str(new_id()),
        "schema_version": 1,
        "type": "banking_app_foreground",
        "occurred_at": datetime.now(UTC).isoformat(),
        "rule_id": "R1",
        "rule_floor": "high",
        "is_drill": False,
    }
    return RiskEvent.model_validate({**base, **changes})


async def store_and_correlate(world: World, ev: RiskEvent, *, device: UUID | None = None) -> Any:
    device_id = device or world.device_id
    async with get_sessionmaker().begin() as session:
        session.add(
            RiskEventRecord(
                id=ev.id,
                family_id=world.family_id,
                device_id=device_id,
                type=ev.type,
                rule_floor=ev.rule_floor.value,
                occurred_at=ev.occurred_at,
                is_drill=ev.is_drill,
                drill_id=ev.drill_id,
                payload={},
            )
        )
        await session.flush()
        return await IncidentService.correlate_event(
            session, ev, device_id=device_id, family_id=world.family_id, member_id=world.member_id
        )


async def event_incident(event_id: UUID) -> UUID | None:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(RiskEventRecord.incident_id).where(RiskEventRecord.id == event_id))


@pytest.mark.parametrize("floor", ["high", "critical"])
async def test_high_floor_opens_an_incident_and_links_the_event(world: World, floor: str) -> None:
    ev = event(rule_floor=floor, type="risk_window_opened")
    result = await store_and_correlate(world, ev)
    assert result is not None and result.opened is True
    row = await load(result.incident.id)
    assert (row.state, row.level, row.rule_floor, row.device_id, row.member_id) == (
        "detected",
        floor,
        floor,
        world.device_id,
        world.member_id,
    )
    assert row.opened_by_event_id == ev.id and await event_incident(ev.id) == row.id
    assert await history(row.id) == [(None, "detected", "device")]


@pytest.mark.parametrize(
    "kind", ["banking_app_foreground", "flagged_number_call", "sideload_detected", "ask_child_pressed"]
)
async def test_trigger_types_open_an_incident_even_with_a_low_floor(world: World, kind: str) -> None:
    result = await store_and_correlate(world, event(type=kind, rule_floor="low", rule_id=None))
    assert result is not None and result.opened is True
    assert (result.incident.level, result.incident.rule_floor) == ("low", "low")


async def test_harmless_event_without_an_open_incident_opens_nothing(world: World) -> None:
    ev = event(type="call_ended", rule_floor="none", rule_id=None)
    assert await store_and_correlate(world, ev) is None
    assert await event_incident(ev.id) is None
    async with get_sessionmaker()() as session:
        assert (await session.scalars(select(Incident).where(Incident.family_id == world.family_id))).first() is None


async def test_later_events_join_the_open_incident_and_can_only_raise_it(world: World) -> None:
    first = await store_and_correlate(world, event(rule_floor="high"))
    assert first is not None
    follow_up = event(type="safe_pause_shown", rule_floor="none", rule_id=None)
    second = await store_and_correlate(world, follow_up)
    assert second is not None and second.opened is False and second.incident.id == first.incident.id
    assert await event_incident(follow_up.id) == first.incident.id
    row = await load(first.incident.id)
    assert (row.level, row.rule_floor, row.version) == ("high", "high", 1)  # sàn thấp hơn không hạ gì
    escalate = event(type="flagged_number_call", rule_floor="critical")
    third = await store_and_correlate(world, escalate)
    assert third is not None and third.opened is False
    row = await load(first.incident.id)
    assert (row.level, row.rule_floor, row.version) == (
        "critical",
        "critical",
        2,
    )  # bất biến level ≥ rule_floor giữ nguyên


async def test_a_resolved_incident_is_not_reopened_a_new_one_is_created(world: World) -> None:
    first = await store_and_correlate(world, event())
    assert first is not None
    await transition(first.incident.id, "assessing", version=1)
    await transition(first.incident.id, "resolved_safe", version=2)
    second = await store_and_correlate(world, event())
    assert second is not None and second.opened is True and second.incident.id != first.incident.id
    assert (await load(first.incident.id)).state == "resolved_safe"


async def test_incidents_are_per_device(world: World) -> None:
    a = await store_and_correlate(world, event())
    b = await store_and_correlate(world, event(), device=world.other_device_id)
    assert a is not None and b is not None and a.incident.id != b.incident.id


async def test_drills_never_mix_with_real_incidents_or_other_drills(world: World) -> None:
    real = await store_and_correlate(world, event())
    drill_a, drill_b = str(new_id()), str(new_id())
    first = await store_and_correlate(world, event(is_drill=True, drill_id=drill_a))
    again = await store_and_correlate(
        world, event(is_drill=True, drill_id=drill_a, type="safe_pause_shown", rule_floor="none", rule_id=None)
    )
    other = await store_and_correlate(world, event(is_drill=True, drill_id=drill_b))
    assert real is not None and first is not None and again is not None and other is not None
    assert first.incident.id != real.incident.id and first.incident.is_drill is True
    assert again.incident.id == first.incident.id and again.opened is False
    assert other.incident.id not in {real.incident.id, first.incident.id}
    assert (await load(first.incident.id)).drill_id == UUID(drill_a)


async def test_concurrent_batches_open_exactly_one_incident(world: World) -> None:
    """SC-004: nhiều lô đến cùng lúc từ một thiết bị ⇒ chỉ một sự cố được mở, các sự kiện còn lại liên kết vào đó."""
    results = await asyncio.gather(*(store_and_correlate(world, event()) for _ in range(8)))
    ids = {r.incident.id for r in results if r is not None}
    assert len(ids) == 1 and sum(1 for r in results if r is not None and r.opened) == 1
    async with get_sessionmaker()() as session:
        rows = (await session.scalars(select(Incident).where(Incident.family_id == world.family_id))).all()
    assert len(rows) == 1


# --- cửa sổ liên kết (review: sự cố bị bỏ quên không được nuốt mãi sự kiện mới) -----------------------------------


async def test_a_stale_open_incident_does_not_swallow_new_events(world: World) -> None:
    first = await store_and_correlate(world, event())
    assert first is not None
    async with get_sessionmaker().begin() as session:  # sự cố và sự kiện cuối cùng của nó đã cách đây 30 ngày
        await session.execute(
            text("update incidents set opened_at = now() - interval '30 days' where id = :i"), {"i": first.incident.id}
        )
        await session.execute(
            text("update risk_events set received_at = now() - interval '30 days' where incident_id = :i"),
            {"i": first.incident.id},
        )
    second = await store_and_correlate(world, event())
    assert second is not None and second.opened is True and second.incident.id != first.incident.id
    assert (await load(first.incident.id)).state == "detected"  # sự cố cũ không bị đụng tới


async def test_recent_activity_keeps_an_old_incident_open_for_linking(world: World) -> None:
    """Sự cố mở đã lâu nhưng vừa có sự kiện thì vẫn nhận sự kiện tiếp theo (kẻ gian vẫn đang gọi)."""
    first = await store_and_correlate(world, event())
    assert first is not None
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update incidents set opened_at = now() - interval '2 hours' where id = :i"), {"i": first.incident.id}
        )
    second = await store_and_correlate(world, event(type="safe_pause_shown", rule_floor="none", rule_id=None))
    assert second is not None and second.opened is False and second.incident.id == first.incident.id


# --- raise_level (spec 026 FR-006): chỉ nâng, không đụng trạng thái/nhật ký --------------------------------------


async def raise_level(incident_id: UUID, level: str, reason: str = "verification") -> Incident:
    async with get_sessionmaker().begin() as session:
        return await IncidentService.raise_level(session, incident_id, level, reason)


@pytest.mark.parametrize("state", ["detected", "assessing", "awaiting_guardian"])
async def test_raise_level_raises_the_level_and_bumps_the_version(world: World, state: str) -> None:
    incident_id = await make_incident(world, state, level="high", rule_floor="high")
    row = await raise_level(incident_id, "critical")
    assert (row.level, row.rule_floor, row.state, row.version) == ("critical", "high", state, 2)
    assert (await load(incident_id)).level == "critical"
    assert await history(incident_id) == []  # không ghi incident_transitions


async def test_raise_level_never_lowers_and_keeps_the_version(world: World) -> None:
    incident_id = await make_incident(world, level="critical", rule_floor="high")
    for lower in ("low", "medium", "high", "critical"):
        row = await raise_level(incident_id, lower)
        assert (row.level, row.version) == ("critical", 1)


async def test_raise_level_never_goes_below_the_rule_floor(world: World) -> None:
    incident_id = await make_incident(world, level="high", rule_floor="high")
    assert (await raise_level(incident_id, "low")).level == "high"


@pytest.mark.parametrize(
    "state",
    ["verifying", "rescore", "case_open", "resolved_safe", "resolved_prevented", "resolved_no_response", "closed"],
)
async def test_raise_level_does_nothing_once_the_guardian_has_decided(world: World, state: str) -> None:
    incident_id = await make_incident(world, state, level="high", rule_floor="high")
    row = await raise_level(incident_id, "critical")
    assert (row.level, row.state, row.version) == ("high", state, 1)
    assert (await load(incident_id)).level == "high"


async def test_raise_level_rejects_unknown_levels_and_missing_incidents(world: World) -> None:
    incident_id = await make_incident(world)
    for bad in ("none", "extreme", ""):
        with pytest.raises(ValueError, match="level"):
            await raise_level(incident_id, bad)
    with pytest.raises(IncidentNotFoundError):
        await raise_level(new_id(), "critical")
    with pytest.raises(ValueError, match="reason"):
        await raise_level(incident_id, "critical", "x" * 300)


async def test_concurrent_raise_levels_end_at_the_highest_with_one_bump_per_real_raise(world: World) -> None:
    incident_id = await make_incident(world, level="low", rule_floor="low")
    levels = ["medium", "high", "critical", "low", "high", "medium", "critical", "high"]
    await asyncio.gather(*(raise_level(incident_id, level) for level in levels))
    row = await load(incident_id)
    assert row.level == "critical"
    assert 2 <= row.version <= 4  # mỗi lần nâng THẬT tăng version đúng 1; lần không nâng thì không tăng


async def test_raise_level_waits_for_the_advisory_lock(world: World) -> None:
    incident_id = await make_incident(world)
    holder = get_sessionmaker()()
    await holder.execute(text("select pg_advisory_xact_lock(hashtext(:i))"), {"i": str(incident_id)})
    task = asyncio.create_task(raise_level(incident_id, "critical"))
    await asyncio.sleep(0.4)
    assert not task.done(), "raise_level đã chạy dù khóa advisory đang bị giữ"
    await holder.rollback()
    await holder.close()
    assert (await asyncio.wait_for(task, 5)).level == "critical"


async def test_a_raise_makes_a_stale_guardian_version_conflict(world: World) -> None:
    """Người giám hộ cầm version cũ không ghi đè mức vừa được nâng: nhận ConcurrencyConflictError."""
    incident_id = await make_incident(world, "awaiting_guardian", level="high", rule_floor="high")
    await raise_level(incident_id, "critical")
    with pytest.raises(ConcurrencyConflictError):
        await transition(incident_id, "resolved_safe", version=1)
