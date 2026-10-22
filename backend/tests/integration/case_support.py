"""Dữ liệu dùng chung cho test hồ sơ vụ việc (spec 031): gia đình demo + sự cố `case_open` có dòng thời gian, bước đồ
thị, kết quả tra cứu. Mọi định danh hư cấu; dọn sạch sau test."""

import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from sqlalchemy import delete, text

from hoicon.db.ids import new_id
from hoicon.db.models import (
    AgentRun,
    AgentStep,
    Device,
    Family,
    Incident,
    IncidentTransition,
    Member,
    RiskEventRecord,
    Verification,
)
from hoicon.db.session import get_sessionmaker

T0 = datetime(2026, 12, 1, 2, 15, 30, tzinfo=UTC)
FAKE_LAST3 = "123"
FAKE_HMAC = "ab" * 32  # HMAC GIẢ: không bao giờ được xuất hiện trong hồ sơ


async def seed_case(
    *,
    reason: str = "graph_scam",
    app_category: str = "bank",
    rule_id: str = "R1",
    answers: tuple[tuple[str, str], ...] = (("q_caller_authority", "yes"), ("q_asked_transfer", "yes")),
    flagged: bool = True,
    is_drill: bool = False,
    state: str = "case_open",
    caller_last3: str | None = FAKE_LAST3,
    with_run: bool = True,
    closed_at: datetime | None = None,
) -> SimpleNamespace:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-031-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add_all([guardian, protected])
        await session.flush()
        device = Device(
            family_id=family.id,
            member_id=protected.id,
            app_version="0.3.0",
            rules_version="r1",
            device_secret_hash=secrets.token_hex(32),
        )
        session.add(device)
        await session.flush()
        event = RiskEventRecord(
            id=new_id(),
            family_id=family.id,
            device_id=device.id,
            type="banking_app_foreground",
            rule_id=rule_id,
            rule_floor="high",
            occurred_at=T0,
            caller_hmac=FAKE_HMAC if caller_last3 else None,  # ràng buộc: các cột caller_* có cùng hoặc không có
            caller_kid=1 if caller_last3 else None,
            caller_last3=caller_last3,
            caller_in_contacts=False if caller_last3 else None,
            call_duration_s=900,
            app_category=app_category,
            app_package="vn.hoicon.demobank",
            payload={"type": "banking_app_foreground"},
        )
        session.add(event)
        await session.flush()
        incident = Incident(
            family_id=family.id,
            member_id=protected.id,
            device_id=device.id,
            state=state,
            level="critical",
            rule_floor="high",
            opened_by_event_id=event.id,
            is_drill=is_drill,
        )
        incident.is_demo = True
        if state == "closed":
            incident.closed_at = closed_at or T0 + timedelta(
                hours=1
            )  # ràng buộc: `closed_at` có đúng khi trạng thái cuối
        session.add(incident)
        await session.flush()
        event.incident_id = incident.id
        for i, (src, dst, actor, why) in enumerate(
            [
                (None, "detected", "device", "risk_event"),
                ("detected", "assessing", "agent", "graph"),
                ("assessing", "awaiting_guardian", "agent", "graph"),
                ("awaiting_guardian", "case_open", "guardian" if reason != "graph_scam" else "system", reason),
            ]
        ):
            session.add(
                IncidentTransition(
                    incident_id=incident.id,
                    from_state=src,
                    to_state=dst,
                    actor=actor,
                    reason=why,
                    at=T0 + timedelta(minutes=i),
                )
            )
        run = None
        if with_run:
            run = AgentRun(
                incident_id=incident.id, graph="incident", status="done", thread_id=str(incident.id), is_demo=True
            )
            session.add(run)
            await session.flush()
            session.add(
                AgentStep(
                    run_id=run.id,
                    node="ingest",
                    output={"level": "high", "threat": "flagged" if flagged else "unknown"},
                )
            )
            for question, answer in answers:
                session.add(
                    AgentStep(run_id=run.id, node="ask_elder", output={"question_id": question, "answer": answer})
                )
        if flagged:
            session.add(
                Verification(
                    family_id=family.id,
                    incident_id=incident.id,
                    actor="system",
                    kind="phone",
                    via="call",
                    subject_kid=1,
                    subject_hmac=FAKE_HMAC,
                    last3=FAKE_LAST3,
                    verdict="dangerous",
                    confidence=1,
                    sources=[{"name": "Danh sách cảnh báo HỏiCon", "type": "list"}],
                    list_version="2026-12-19",
                )
            )
        return SimpleNamespace(
            family=family.id,
            guardian=guardian.id,
            protected=protected.id,
            incident=incident.id,
            run=run.id if run else None,
        )


async def purge_case(world: SimpleNamespace) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(AgentRun).where(AgentRun.thread_id == str(world.incident)))
        await session.execute(text("delete from jobs where idempotency_key like :p"), {"p": f"{world.incident}:%"})
        await session.execute(text("delete from families where id = :f"), {"f": world.family})


def uuid_str(value: Any) -> str:
    return str(value if isinstance(value, UUID) else UUID(str(value)))
