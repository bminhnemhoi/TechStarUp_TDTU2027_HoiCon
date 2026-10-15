"""Migration 0006 (spec 021): incidents, incident_transitions, risk_events + FK từ action_tokens/messages_out."""

import secrets
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import (
    ActionToken,
    Device,
    Family,
    Incident,
    IncidentTransition,
    Member,
    MessageOut,
    RiskEventRecord,
)
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

HEX64 = "ab" * 32  # chuỗi giả, không phải băm của dữ liệu thật
LEVELS = ["none", "low", "medium", "high", "critical"]


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    """Gia đình + thành viên + thiết bị giả; dọn cuối test (xóa gia đình kéo theo sự cố, sự kiện, thiết bị)."""
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0006-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        device = Device(
            family_id=family.id,
            member_id=member.id,
            app_version="0.2.0",
            rules_version="r1",
            device_secret_hash=secrets.token_hex(32),
        )
        session.add(device)
        await session.flush()
        ids = {"family": family.id, "member": member.id, "device": device.id}
    yield ids
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from messages_out where family_id = :f"), {"f": ids["family"]})
        await session.execute(text("delete from families where id = :f"), {"f": ids["family"]})


def incident(ids: dict[str, UUID], **changes: Any) -> Incident:
    base: dict[str, Any] = {
        "family_id": ids["family"],
        "member_id": ids["member"],
        "device_id": ids["device"],
        "state": "detected",
        "level": "high",
        "rule_floor": "high",
    }
    return Incident(**{**base, **changes})


def risk_event(ids: dict[str, UUID], **changes: Any) -> RiskEventRecord:
    base: dict[str, Any] = {
        "id": new_id(),
        "family_id": ids["family"],
        "device_id": ids["device"],
        "type": "banking_app_foreground",
        "rule_floor": "high",
        "occurred_at": text("now()"),
        "is_drill": False,
        "payload": {},
    }
    return RiskEventRecord(**{**base, **changes})


async def columns(table: str) -> dict[str, Any]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, character_maximum_length, is_nullable "
                    "from information_schema.columns where table_name = :t"
                ),
                {"t": table},
            )
        ).all()
    return {r.column_name: r for r in rows}


async def test_columns_match_the_data_model_and_hold_no_raw_pii(require_db: None) -> None:
    expected = {
        "incidents": {
            "id",
            "family_id",
            "member_id",
            "device_id",
            "state",
            "level",
            "rule_floor",
            "version",
            "is_drill",
            "drill_id",
            "is_demo",
            "opened_by_event_id",
            "outcome",
            "opened_at",
            "closed_at",
        },
        "incident_transitions": {"id", "incident_id", "from_state", "to_state", "actor", "reason", "at"},
        "risk_events": {
            "id",
            "family_id",
            "device_id",
            "incident_id",
            "type",
            "rule_id",
            "rule_floor",
            "occurred_at",
            "received_at",
            "caller_hmac",
            "caller_kid",
            "caller_last3",
            "caller_in_contacts",
            "call_duration_s",
            "app_category",
            "app_package",
            "timing_detect_ms",
            "timing_pause_ms",
            "is_drill",
            "drill_id",
            "payload",
        },
    }
    for table, names in expected.items():
        cols = await columns(table)
        assert set(cols) == names, table
        # SC-005/FR-009: không cột nào chứa số điện thoại thô, h1 hay tên thật (ADR-006: chỉ HMAC + 3 số cuối).
        assert not [c for c in cols if any(w in c for w in ("phone", "h1", "real_name", "zalo_id", "otp"))], table
    risk = await columns("risk_events")
    assert (risk["caller_hmac"].character_maximum_length, risk["caller_last3"].character_maximum_length) == (64, 3)
    assert risk["payload"].data_type == "jsonb"


async def test_incident_defaults_and_constraints(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(incident(world))
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(Incident).where(Incident.family_id == world["family"]))).one()
        assert (row.version, row.is_drill, row.is_demo, row.closed_at) == (1, False, False, None)
        assert row.opened_at is not None and row.outcome is None and row.opened_by_event_id is None
    for bad in (
        {"state": "exploded"},
        {"level": "none"},
        {"level": "extreme"},
        {"rule_floor": "extreme"},
        {"version": 0},
        {"is_drill": True, "drill_id": None},  # diễn tập phải có drill_id
        {"closed_at": text("now()")},  # chưa kết thúc mà có closed_at
        {"state": "closed", "closed_at": None},  # đã kết thúc mà thiếu closed_at
    ):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(incident(world, **bad))


@pytest.mark.parametrize(
    ("level", "floor", "ok"),
    [(lv, fl, LEVELS.index(lv) >= LEVELS.index(fl)) for lv in LEVELS[1:] for fl in LEVELS],
)
async def test_invariant_level_never_below_rule_floor(world: dict[str, UUID], level: str, floor: str, ok: bool) -> None:
    """Bất biến 1 (DATA-MODEL §4): `level >= rule_floor` ở mọi cặp giá trị — INSERT."""
    if ok:
        async with get_sessionmaker().begin() as session:
            session.add(incident(world, level=level, rule_floor=floor))
        return
    with pytest.raises(IntegrityError, match="level_ge_floor"):
        async with get_sessionmaker().begin() as session:
            session.add(incident(world, level=level, rule_floor=floor))


async def test_invariant_blocks_lowering_level_below_floor_by_update(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(incident(world, level="critical", rule_floor="high"))
    with pytest.raises(IntegrityError, match="level_ge_floor"):
        async with get_sessionmaker().begin() as session:
            await session.execute(
                text("update incidents set level = 'medium' where family_id = :f"), {"f": world["family"]}
            )


async def test_terminal_states_cannot_be_left(world: dict[str, UUID]) -> None:
    """Bất biến 2: `resolved_*`/`closed` không quay lại — chặn ở cấp CSDL, kể cả khi bỏ qua IncidentService."""
    async with get_sessionmaker().begin() as session:
        session.add(incident(world, state="resolved_safe", closed_at=text("now()")))
    with pytest.raises((DBAPIError, IntegrityError), match="terminal"):
        async with get_sessionmaker().begin() as session:
            await session.execute(
                text("update incidents set state = 'assessing', closed_at = null where family_id = :f"),
                {"f": world["family"]},
            )
    async with get_sessionmaker()() as session:
        assert (await session.scalars(select(Incident.state).where(Incident.family_id == world["family"]))).one() == (
            "resolved_safe"
        )


async def test_transition_constraints(world: dict[str, UUID]) -> None:
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        session.add(IncidentTransition(incident_id=inc.id, from_state=None, to_state="detected", actor="device"))
        incident_id = inc.id
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(IncidentTransition))).all()
        assert next(r for r in row if r.incident_id == incident_id).at is not None
    for bad in ({"actor": "hacker"}, {"to_state": "exploded"}, {"from_state": "exploded"}):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                payload: dict[str, Any] = {"incident_id": incident_id, "to_state": "assessing", "actor": "agent"}
                session.add(IncidentTransition(**{**payload, **bad}))


async def test_risk_event_constraints_and_no_raw_phone(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(risk_event(world, caller_hmac=HEX64, caller_kid=1, caller_last3="123", caller_in_contacts=False))
    for bad in (
        {"type": "teleport"},
        {"rule_floor": "extreme"},
        {"rule_id": "R9"},
        {"app_category": "game"},
        {"caller_hmac": "0900000001", "caller_kid": 1, "caller_last3": "123"},  # số thô không vào được cột băm
        {"caller_hmac": "AB" * 32, "caller_kid": 1, "caller_last3": "123"},
        {"caller_hmac": HEX64, "caller_kid": 1, "caller_last3": "12"},
        {"caller_hmac": HEX64, "caller_kid": 1, "caller_last3": "abc"},
        {"timing_detect_ms": -1},
        {"call_duration_s": -1},
        {"is_drill": True, "drill_id": None},
    ):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(risk_event(world, **bad))
    event_id = new_id()
    async with get_sessionmaker().begin() as session:
        session.add(risk_event(world, id=event_id))
    with pytest.raises(IntegrityError):  # id trùng ⇒ khóa chính (cơ sở của idempotency)
        async with get_sessionmaker().begin() as session:
            session.add(risk_event(world, id=event_id))


async def test_event_links_to_incident_and_survives_incident_delete(world: dict[str, UUID]) -> None:
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        event = risk_event(world, incident_id=inc.id)
        session.add(event)
        await session.flush()
        inc.opened_by_event_id = event.id
        incident_id, event_id = inc.id, event.id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from incidents where id = :i"), {"i": incident_id})
    async with get_sessionmaker()() as session:  # hạn lưu khác nhau (90 ngày vs 12 tháng): xóa sự cố không xóa sự kiện
        assert (await session.get(RiskEventRecord, event_id)) is not None
        assert (await session.get(RiskEventRecord, event_id)).incident_id is None  # type: ignore[union-attr]


async def test_action_tokens_and_messages_out_reference_incidents(world: dict[str, UUID]) -> None:
    """FR-001: `action_tokens.incident_id` và `messages_out.incident_id` giờ có FK tới `incidents.id`."""
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        session.add(
            ActionToken(
                incident_id=inc.id,
                member_id=world["member"],
                token_hash=HEX64,
                scope="incident_decision",
                expires_at=text("now() + interval '1 hour'"),
            )
        )
        session.add(
            MessageOut(
                family_id=world["family"],
                incident_id=inc.id,
                member_id=world["member"],
                channel="zalo",
                bot_id="b",
                template_id="fast_alert",
                status="sent",
                quota_month="2026-10",
            )
        )
        incident_id = inc.id
    with pytest.raises(IntegrityError):  # sự cố không tồn tại
        async with get_sessionmaker().begin() as session:
            session.add(
                MessageOut(
                    family_id=world["family"],
                    incident_id=new_id(),
                    channel="zalo",
                    bot_id="b",
                    template_id="x",
                    status="sent",
                    quota_month="2026-10",
                )
            )
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(
                ActionToken(
                    incident_id=new_id(),
                    member_id=world["member"],
                    token_hash="cd" * 32,
                    scope="incident_decision",
                    expires_at=text("now()"),
                )
            )
    async with get_sessionmaker().begin() as session:  # xóa sự cố: sổ tin gửi đi giữ nguyên (hạn mức), token mất theo
        await session.execute(text("delete from incidents where id = :i"), {"i": incident_id})
    async with get_sessionmaker()() as session:
        message = (await session.scalars(select(MessageOut).where(MessageOut.family_id == world["family"]))).one()
        assert message.incident_id is None
        assert (await session.scalars(select(ActionToken).where(ActionToken.token_hash == HEX64))).first() is None


async def test_deleting_the_family_removes_incidents_events_and_transitions(world: dict[str, UUID]) -> None:
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        session.add(IncidentTransition(incident_id=inc.id, from_state=None, to_state="detected", actor="device"))
        session.add(risk_event(world, incident_id=inc.id))
        incident_id = inc.id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": world["family"]})
    async with get_sessionmaker()() as session:
        assert (await session.get(Incident, incident_id)) is None
        left = await session.scalar(
            text("select count(*) from risk_events where family_id = :f"), {"f": world["family"]}
        )
        assert left == 0


async def test_terminal_incident_is_read_only(world: dict[str, UUID]) -> None:
    """Sau khi kết thúc, `level`/`rule_floor`/`outcome`/`closed_at` không sửa được (nhật ký kiểm toán đáng tin)."""
    async with get_sessionmaker().begin() as session:
        session.add(incident(world, state="resolved_safe", closed_at=text("now()"), outcome="safe"))
    edits = (
        "update incidents set level = 'critical' where family_id = :f",
        "update incidents set rule_floor = 'low' where family_id = :f",
        "update incidents set outcome = 'prevented' where family_id = :f",
        "update incidents set closed_at = now() + interval '1 day' where family_id = :f",
    )
    for statement in edits:
        with pytest.raises((DBAPIError, IntegrityError), match="terminal"):
            async with get_sessionmaker().begin() as session:
                await session.execute(text(statement), {"f": world["family"]})


async def test_transition_log_cannot_be_rewritten(world: dict[str, UUID]) -> None:
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        session.add(IncidentTransition(incident_id=inc.id, from_state=None, to_state="detected", actor="device"))
        incident_id = inc.id
    with pytest.raises((DBAPIError, IntegrityError), match="append-only"):
        async with get_sessionmaker().begin() as session:
            await session.execute(
                text("update incident_transitions set to_state = 'closed' where incident_id = :i"), {"i": incident_id}
            )


async def test_caller_columns_come_together(world: dict[str, UUID]) -> None:
    for bad in (
        {"caller_hmac": HEX64},  # có băm mà thiếu kid/last3
        {"caller_kid": 1},
        {"caller_last3": "123"},
        {"caller_hmac": HEX64, "caller_kid": 1},
    ):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(risk_event(world, **bad))


async def test_transition_rows_cannot_be_deleted_directly_but_go_with_their_incident(world: dict[str, UUID]) -> None:
    inc = incident(world)
    async with get_sessionmaker().begin() as session:
        session.add(inc)
        await session.flush()
        session.add(IncidentTransition(incident_id=inc.id, from_state=None, to_state="detected", actor="device"))
        incident_id = inc.id
    with pytest.raises((DBAPIError, IntegrityError), match="append-only"):
        async with get_sessionmaker().begin() as session:
            await session.execute(text("delete from incident_transitions where incident_id = :i"), {"i": incident_id})
    async with get_sessionmaker().begin() as session:  # xóa sự cố ⇒ CASCADE vẫn xóa được nhật ký (quyền xóa dữ liệu)
        await session.execute(text("delete from incidents where id = :i"), {"i": incident_id})
    async with get_sessionmaker()() as session:
        left = await session.scalar(
            text("select count(*) from incident_transitions where incident_id = :i"), {"i": incident_id}
        )
        assert left == 0
