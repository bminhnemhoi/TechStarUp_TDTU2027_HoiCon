"""Spec 034 FR-002 / SC-001: job `retention` thực thi đúng bảng §6 của DATA-MODEL.md.

Mọi mốc thời gian dựng quanh một `NOW` cố định tiêm vào dịch vụ (không chờ thật): quá hạn 1 giây ⇒ xử lý, còn hạn 1
giây ⇒ giữ. Kiểm theo id của chính test (DB dev có thể còn dữ liệu cũ của việc khác nên không so tổng số)."""

import re
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, purge_family
from sqlalchemy import func, select, text

from hoicon.agents.runtime import open_checkpointer
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import (
    ActionToken,
    AgentRun,
    AgentStep,
    Consent,
    Device,
    Drill,
    Family,
    Incident,
    IncidentTransition,
    Job,
    Member,
    RiskEventRecord,
    Verification,
)
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.services import retention_service as rs

pytestmark = pytest.mark.integration

NOW = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
SECOND = timedelta(seconds=1)
KIND = "test_retention"
DATA_MODEL = Path(__file__).resolve().parents[3] / "docs" / "DATA-MODEL.md"


def expired(kind: str) -> datetime:
    return NOW - rs.RETENTION[kind] - SECOND


def fresh(kind: str) -> datetime:
    return NOW - rs.RETENTION[kind] + SECOND


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0034-ret-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        device = Device(
            family_id=family.id,
            member_id=member.id,
            app_version="1",
            rules_version="1",
            device_secret_hash=secrets.token_hex(32),
        )
        session.add(device)
        await session.flush()
        ids = {"family": family.id, "member": member.id, "device": device.id}
    yield ids
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from jobs where kind = :k"), {"k": KIND})
    await purge_family(ids["family"])


async def has(model: Any, key: UUID) -> bool:
    async with get_sessionmaker()() as session:
        return await session.get(model, key) is not None


def incident(world: dict[str, UUID], closed_at: datetime | None, **changes: Any) -> Incident:
    values: dict[str, Any] = {
        "id": new_id(),
        "family_id": world["family"],
        "member_id": world["member"],
        "device_id": world["device"],
        "level": "high",
        "rule_floor": "high",
        "state": "closed" if closed_at else "detected",
        "closed_at": closed_at,
    }
    return Incident(**{**values, **changes})


async def run_all(*, dry_run: bool = False, delete_thread: Any = None) -> dict[str, int]:
    async def noop(_: str) -> None:
        return None

    return await rs.run_retention(get_sessionmaker(), delete_thread or noop, now=NOW, dry_run=dry_run)


# --- hằng số khớp tài liệu -------------------------------------------------------------------------------------------


def test_retention_constants_match_the_data_model_table() -> None:
    rows = {
        cells[0]: cells[1]
        for line in DATA_MODEL.read_text(encoding="utf-8").split("## 6. Hạn lưu", 1)[1].splitlines()
        if line.startswith("|") and (cells := [c.strip() for c in line.strip("|").split("|")]) and len(cells) >= 2
    }

    def row(marker: str) -> str:
        found = [limit for name, limit in rows.items() if marker in name]
        assert found, f"DATA-MODEL §6 thiếu dòng cho {marker}"
        return found[0]

    def days(value: str) -> int:
        match = re.search(r"(\d+) ngày", value)
        assert match, value
        return int(match.group(1))

    assert days(row("`risk_events`")) == rs.RETENTION["risk_events"].days
    assert days(row("`agent_steps.input_redacted/output`")) == rs.RETENTION["agent_steps_content"].days
    assert "12 tháng" in row("`incidents` + transitions") and rs.RETENTION["incidents"].days == 365
    assert days(row("Checkpoint LangGraph")) == rs.RETENTION["checkpoints"].days
    assert days(row("`jobs`")) == rs.RETENTION["jobs"].days
    assert days(row("`action_tokens`")) == rs.RETENTION["action_tokens"].days
    assert days(row("`verifications`")) == rs.RETENTION["verifications"].days
    assert "12 tháng" in row("`drills`") and rs.RETENTION["drills"].days == 365
    assert days(row("`device_heartbeats`")) == rs.RETENTION["device_heartbeats"].days
    assert set(rs.RETENTION) == {
        "risk_events",
        "agent_steps_content",
        "incidents",
        "checkpoints",
        "jobs",
        "action_tokens",
        "verifications",
        "drills",
        "device_heartbeats",
    }


# --- từng loại: quá hạn 1 giây bị xử lý, còn hạn 1 giây được giữ -----------------------------------------------------


async def test_risk_events_older_than_90_days_are_deleted(world: dict[str, UUID]) -> None:
    old, young = new_id(), new_id()
    async with get_sessionmaker().begin() as session:
        for event_id, received in ((old, expired("risk_events")), (young, fresh("risk_events"))):
            session.add(
                RiskEventRecord(
                    id=event_id,
                    family_id=world["family"],
                    device_id=world["device"],
                    type="call_started",
                    rule_floor="none",
                    occurred_at=received,
                    received_at=received,
                    is_drill=False,
                    payload={},
                )
            )
    report = await run_all()
    assert report["risk_events"] >= 1
    assert not await has(RiskEventRecord, old) and await has(RiskEventRecord, young)


async def test_agent_step_content_is_blanked_but_the_measurements_stay(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        run = AgentRun(graph="incident", thread_id=str(new_id()), incident_id=None)
        session.add(run)
        await session.flush()
        old, young = new_id(), new_id()
        for step_id, at in ((old, expired("agent_steps_content")), (young, fresh("agent_steps_content"))):
            session.add(
                AgentStep(
                    id=step_id,
                    run_id=run.id,
                    node="risk_scorer",
                    input_redacted={"x": 1},
                    output={"y": 2},
                    latency_ms=120,
                    tokens_in=10,
                    tokens_out=5,
                    cost_usd=0.001,
                    at=at,
                )
            )
    await run_all()
    async with get_sessionmaker()() as session:
        blanked = await session.get(AgentStep, old)
        kept = await session.get(AgentStep, young)
    assert blanked is not None and kept is not None
    assert blanked.input_redacted is None and blanked.output is None
    assert (blanked.latency_ms, blanked.tokens_in, blanked.tokens_out, float(blanked.cost_usd)) == (120, 10, 5, 0.001)
    assert kept.input_redacted == {"x": 1} and kept.output == {"y": 2}
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from agent_runs where id = :r"), {"r": run.id})


async def test_closed_incidents_older_than_12_months_go_with_their_children(world: dict[str, UUID]) -> None:
    old = incident(world, expired("incidents"))
    young = incident(world, fresh("incidents"))
    still_open = incident(world, None, opened_at=NOW - timedelta(days=900))
    async with get_sessionmaker().begin() as session:
        session.add_all([old, young, still_open])
        await session.flush()
        for inc in (old, young):
            session.add(
                IncidentTransition(incident_id=inc.id, from_state="detected", to_state="assessing", actor="system")
            )
            session.add(
                Verification(
                    family_id=world["family"],
                    incident_id=inc.id,
                    actor="system",
                    kind="phone",
                    via="call",
                    subject_kid=1,
                    subject_hmac="ab" * 32,
                    last3="123",
                    verdict="unknown",
                    confidence=0,
                    at=NOW,
                )
            )
            session.add(
                ActionToken(
                    incident_id=inc.id,
                    member_id=world["member"],
                    token_hash=secrets.token_hex(32),
                    scope="incident_decision",
                    expires_at=NOW + timedelta(days=1),
                )
            )
        # đồ thị thật khóa theo thread_id (= id sự cố) và để incident_id NULL: phải bị xóa theo thread_id
        session.add(AgentRun(graph="incident", thread_id=str(old.id)))
    await run_all()
    assert not await has(Incident, old.id) and await has(Incident, young.id) and await has(Incident, still_open.id)
    async with get_sessionmaker()() as session:
        counts = {
            table: await session.scalar(text(f"select count(*) from {table} where incident_id = :i"), {"i": old.id})  # noqa: S608
            for table in ("incident_transitions", "verifications", "action_tokens")
        }
        young_children = await session.scalar(
            text("select count(*) from incident_transitions where incident_id = :i"), {"i": young.id}
        )
    counts["agent_runs"] = await _runs_of(old.id)
    assert counts == {"incident_transitions": 0, "verifications": 0, "action_tokens": 0, "agent_runs": 0}
    assert young_children == 1


async def _runs_of(incident_id: UUID) -> int:
    async with get_sessionmaker()() as session:
        return (
            await session.scalar(
                select(func.count()).select_from(AgentRun).where(AgentRun.thread_id == str(incident_id))
            )
            or 0
        )


async def test_finished_jobs_are_deleted_after_30_days_and_unfinished_ones_never(world: dict[str, UUID]) -> None:
    old, young, never_done = new_id(), new_id(), new_id()
    async with get_sessionmaker().begin() as session:
        session.add(Job(id=old, kind=KIND, payload={"text": "toàn văn tin"}, done_at=expired("jobs")))
        session.add(Job(id=young, kind=KIND, payload={}, done_at=fresh("jobs")))
        session.add(Job(id=never_done, kind=KIND, payload={}, done_at=None, created_at=NOW - timedelta(days=400)))
    await run_all()
    assert not await has(Job, old) and await has(Job, young) and await has(Job, never_done)


async def test_expired_action_tokens_are_deleted_30_days_after_expiry(world: dict[str, UUID]) -> None:
    old, young = secrets.token_hex(32), secrets.token_hex(32)
    async with get_sessionmaker().begin() as session:
        for digest, expires in ((old, expired("action_tokens")), (young, fresh("action_tokens"))):
            session.add(
                ActionToken(member_id=world["member"], token_hash=digest, scope="guardian_view", expires_at=expires)
            )
    await run_all()
    async with get_sessionmaker()() as session:
        left = set(
            await session.scalars(select(ActionToken.token_hash).where(ActionToken.member_id == world["member"]))
        )
    assert left == {young}


async def test_verifications_older_than_90_days_are_deleted(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        for at in (expired("verifications"), fresh("verifications")):
            session.add(
                Verification(
                    family_id=world["family"],
                    actor="system",
                    kind="phone",
                    via="typed",
                    subject_kid=1,
                    subject_hmac=secrets.token_hex(32),
                    last3="123",
                    verdict="unknown",
                    confidence=0,
                    at=at,
                )
            )
    await run_all()
    async with get_sessionmaker()() as session:
        left = await session.scalars(select(Verification.at).where(Verification.family_id == world["family"]))
        assert [a for a in left] == [fresh("verifications")]


async def test_drills_older_than_12_months_are_deleted(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        for created in (expired("drills"), fresh("drills")):
            start = created + timedelta(hours=1)
            session.add(
                Drill(
                    family_id=world["family"],
                    member_id=world["member"],
                    scheduled_by="ops",
                    script_id="drill_bank_card_locked",
                    window_start=start,
                    window_end=start + timedelta(hours=1),
                    status="expired",
                    created_at=created,
                )
            )
    await run_all()
    async with get_sessionmaker()() as session:
        left = list(await session.scalars(select(Drill.created_at).where(Drill.family_id == world["family"])))
    assert left == [fresh("drills")]


async def test_messages_out_rows_stay_for_the_quota_and_hold_no_text() -> None:
    async with get_engine().connect() as conn:
        cols = {
            r[0]
            for r in (
                await conn.execute(
                    text("select column_name from information_schema.columns where table_name = 'messages_out'")
                )
            ).all()
        }
    assert not cols & {"text", "body", "message", "content"}
    assert "messages_out" not in {"risk_events", *rs.RETENTION}


async def test_consents_are_never_touched(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world["family"],
                member_id=world["member"],
                purpose="core_protection",
                granted=True,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
                recorded_at=NOW - timedelta(days=2000),
            )
        )
    await run_all()
    async with get_sessionmaker()() as session:
        left = await session.scalar(
            select(func.count()).select_from(Consent).where(Consent.family_id == world["family"])
        )
    assert left == 1
    assert "consents" not in rs.RETENTION


# --- checkpoint LangGraph ------------------------------------------------------------------------------------------


async def put_checkpoint(thread: UUID) -> None:
    async with get_engine().begin() as conn:
        await conn.execute(
            text(
                "insert into checkpoints (thread_id, checkpoint_ns, checkpoint_id, type, checkpoint, metadata) "
                "values (:t, '', :c, 'json', '{}'::jsonb, '{}'::jsonb)"
            ),
            {"t": str(thread), "c": str(new_id())},
        )


async def checkpoint_count(thread: UUID) -> int:
    async with get_engine().connect() as conn:
        return (
            await conn.execute(text("select count(*) from checkpoints where thread_id = :t"), {"t": str(thread)})
        ).scalar_one()


async def test_checkpoints_of_incidents_closed_over_7_days_ago_are_deleted(world: dict[str, UUID]) -> None:
    eight_days = incident(world, NOW - timedelta(days=8))
    six_days = incident(world, NOW - timedelta(days=6))
    open_one = incident(world, None)
    async with get_sessionmaker().begin() as session:
        session.add_all([eight_days, six_days, open_one])
    for inc in (eight_days, six_days, open_one):
        await put_checkpoint(inc.id)
    url = get_settings().database_url.get_secret_value()
    async with open_checkpointer(url) as saver:
        report = await rs.run_retention(get_sessionmaker(), saver.adelete_thread, now=NOW)
    assert report["checkpoints"] >= 1
    assert await checkpoint_count(eight_days.id) == 0
    assert await checkpoint_count(six_days.id) == 1 and await checkpoint_count(open_one.id) == 1
    async with open_checkpointer(url) as saver:  # lần hai: lũy đẳng, không lỗi, kết quả không đổi
        await rs.purge_checkpoints(get_sessionmaker(), saver.adelete_thread, now=NOW)
    assert await checkpoint_count(eight_days.id) == 0 and await checkpoint_count(six_days.id) == 1


async def test_without_a_checkpoint_connection_the_kind_is_reported_as_skipped_not_done(world: dict[str, UUID]) -> None:
    report = await rs.run_retention(get_sessionmaker(), None, now=NOW)
    assert report["checkpoints"] == -1


# --- tính chất chung -------------------------------------------------------------------------------------------------


async def test_a_second_run_changes_nothing(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(Job(id=new_id(), kind=KIND, payload={}, done_at=expired("jobs")))
        session.add(incident(world, expired("incidents")))
    first = await run_all()
    second = await run_all()
    assert first["jobs"] >= 1 and first["incidents"] >= 1
    assert all(count == 0 for kind, count in second.items() if kind != "checkpoints")


async def test_dry_run_counts_but_writes_nothing(world: dict[str, UUID]) -> None:
    job_id = new_id()
    async with get_sessionmaker().begin() as session:
        session.add(Job(id=job_id, kind=KIND, payload={}, done_at=expired("jobs")))
    called: list[str] = []

    async def spy(thread: str) -> None:
        called.append(thread)

    report = await run_all(dry_run=True, delete_thread=spy)
    assert report["jobs"] >= 1 and called == []
    assert await has(Job, job_id)  # còn nguyên
    real = await run_all()
    assert real["jobs"] == report["jobs"] and not await has(Job, job_id)


async def test_deletion_runs_in_batches_of_at_most_the_batch_size(
    world: dict[str, UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rs, "BATCH", 3)
    ids = [new_id() for _ in range(8)]
    async with get_sessionmaker().begin() as session:
        session.add_all(Job(id=i, kind=KIND, payload={}, done_at=expired("jobs")) for i in ids)
    deleted = await rs.purge_jobs(get_sessionmaker(), now=NOW)
    assert deleted >= 8
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).select_from(Job).where(Job.id.in_(ids))) == 0


def test_the_batch_size_is_1000() -> None:
    assert rs.BATCH == 1000


async def test_the_log_carries_counts_and_never_content(
    world: dict[str, UUID], caplog: pytest.LogCaptureFixture
) -> None:
    secret_text = "toàn-văn-tin-không-được-log"
    async with get_sessionmaker().begin() as session:
        session.add(Job(id=new_id(), kind=KIND, payload={"text": secret_text}, done_at=expired("jobs")))
    with caplog.at_level("INFO", logger="hoicon.services.retention_service"):
        await run_all()
    text_ = " ".join(r.getMessage() for r in caplog.records)
    assert "jobs=" in text_ and secret_text not in text_


# --- lịch hằng ngày --------------------------------------------------------------------------------------------------


def test_the_daily_key_follows_the_vietnam_calendar_day() -> None:
    assert rs.retention_key(datetime(2027, 3, 1, 16, 59, tzinfo=UTC)) == "retention:2027-03-01"  # 23:59 giờ VN
    assert rs.retention_key(datetime(2027, 3, 1, 17, 0, tzinfo=UTC)) == "retention:2027-03-02"  # 00:00 giờ VN


async def test_scheduling_twice_the_same_day_queues_one_job(require_db: None) -> None:
    day = datetime(2031, 6, 15, 3, 0, tzinfo=UTC)
    key = rs.retention_key(day)
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from jobs where idempotency_key = :k"), {"k": key})
    try:
        assert await rs.schedule_daily(get_sessionmaker(), now=day) == key
        await rs.schedule_daily(get_sessionmaker(), now=day + timedelta(hours=5))
        async with get_sessionmaker()() as session:
            jobs = list(await session.scalars(select(Job).where(Job.idempotency_key == key)))
        assert len(jobs) == 1 and jobs[0].kind == "retention"
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(text("delete from jobs where idempotency_key = :k"), {"k": key})


def test_the_worker_registers_the_retention_and_purge_handlers() -> None:
    from hoicon.channels.guardian import ChannelDeps
    from hoicon.channels.zalo import MockZaloClient
    from hoicon.jobs.worker import incident_handlers

    class FakeRuntime:
        graph = None

    handlers = incident_handlers(
        FakeRuntime(),  # type: ignore[arg-type]
        ChannelDeps(get_sessionmaker(), MockZaloClient(), get_settings()),
    )
    assert {"retention", "purge_family", "drill_expire", "notify_guardian"} <= set(handlers)
