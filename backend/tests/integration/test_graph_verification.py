"""Spec 026 (FR-006, FR-007, SC-003, SC-006): node `verification` (tất định, không LLM) và tin bằng chứng `evidence`.

Số điện thoại/HMAC dưới đây là chuỗi giả (không băm của số thật).
"""

import json
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from consent_support import purge_family
from sqlalchemy import select, text

from hoicon.agents.incident_graph import Deps, GuardianBrief, RiskAssessment
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime, clean_resume
from hoicon.agents.spike import demo_event
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep, Family, Incident, Job, Member, Verification
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import mask_text
from hoicon.domain.risk import RiskLevel

pytestmark = pytest.mark.integration

AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon"
LEVELS = ["none", "low", "medium", "high", "critical"]


class Client:
    """LLM giả: trả mức/ câu hỏi cấu hình sẵn (mặc định: không hỏi gì, mức `low` — không hạ được mức sàn)."""

    def __init__(self, level: str = "low", ask: str = "none") -> None:
        self.level, self.ask = level, ask

    def with_options(self, **_: Any) -> "Client":
        return self

    @property
    def messages(self) -> "Client":
        return self

    async def parse(self, *, output_format: type, **_: Any) -> Any:
        if output_format is RiskAssessment:
            output = RiskAssessment(level=self.level, tactic="unknown", reasons=["ok"], ask_question=self.ask)  # type: ignore[arg-type]
        else:
            output = GuardianBrief(summary="Mẹ vừa nghe một số lạ rồi mở ứng dụng ngân hàng", action="call_now")
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        return SimpleNamespace(parsed_output=output, stop_reason="end_turn", usage=usage)


@dataclass
class World:
    family: UUID
    member: UUID
    incident: UUID
    drill_incident: UUID


@pytest.fixture
async def world(require_db: None, threads: list[str]) -> AsyncGenerator[World]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name="Gia đình mẫu 026", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add(member)
        await session.flush()
        real = Incident(family_id=family.id, member_id=member.id, level="high", rule_floor="high", is_demo=True)
        drill = Incident(
            family_id=family.id,
            member_id=member.id,
            level="high",
            rule_floor="high",
            is_demo=True,
            is_drill=True,
            drill_id=new_id(),
        )
        session.add_all([real, drill])
        await session.flush()
        ids = World(family.id, member.id, real.id, drill.id)
    threads.extend([str(ids.incident), str(ids.drill_incident)])
    yield ids
    await purge_family(ids.family)


def deps(client: Client) -> Deps:
    settings = get_settings().model_copy(
        update={"timer_ask_elder_s": 600, "timer_t1_s": 900, "timer_t2_s": 1200, "timer_t3_s": 1800}
    )
    return Deps(LlmRouter(client, "claude-haiku-4-5", Decimal(10)), get_sessionmaker(), settings)


def event(*, drill: bool = False) -> Any:
    """Sự kiện không có số gọi đến ⇒ không phụ thuộc danh sách đe dọa của DB dev; mức sàn `high`."""
    return demo_event(is_drill=drill).model_copy(update={"caller": None})


@asynccontextmanager
async def running(world: World, client: Client | None = None, *, drill: bool = False) -> AsyncIterator[tuple[Any, str]]:
    incident = world.drill_incident if drill else world.incident
    async with IncidentRuntime.open(deps(client or Client())) as runtime:
        thread = str(incident)
        try:
            yield runtime, thread
        finally:
            await runtime.graph.checkpointer.adelete_thread(thread)


async def start(runtime: Any, world: World, thread: str, *, drill: bool = False) -> Any:
    return await runtime.start(
        event(drill=drill), incident_id=thread, elder_alias="Mẹ", is_demo=True, family_id=str(world.family)
    )


async def add_verification(world: World, incident: UUID | None, verdict: str, **changes: Any) -> UUID:
    row = Verification(
        id=new_id(),
        family_id=world.family,
        incident_id=incident,
        actor=changes.pop("actor", "device"),
        actor_id=changes.pop("actor_id", world.member),
        kind=changes.pop("kind", "phone"),
        via=changes.pop("via", "typed"),
        subject_kid=1,
        subject_hmac=uuid4().hex + uuid4().hex,  # chuỗi giả 64 hex
        last3=changes.pop("last3", "123"),
        verdict=verdict,
        confidence=0.9 if verdict == "dangerous" else 0.6,
        **changes,
    )
    async with get_sessionmaker().begin() as session:
        session.add(row)
    return row.id


async def incident_row(incident: UUID) -> Incident:
    async with get_sessionmaker()() as session:
        row = await session.get(Incident, incident, populate_existing=True)
        assert row is not None
        return row


async def jobs(thread: str, suffix: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        found = await session.scalars(select(Job).where(Job.idempotency_key.startswith(f"{thread}:{suffix}")))
        return list(found.all())


async def steps(thread: str, node: str) -> list[AgentStep]:
    async with get_sessionmaker()() as session:
        run = (await session.scalars(select(AgentRun).where(AgentRun.thread_id == thread))).one()
        found = await session.scalars(
            select(AgentStep).where(AgentStep.run_id == run.id, AgentStep.node == node).order_by(AgentStep.at)
        )
        return list(found.all())


# --- node verification: nâng mức từ các dòng xác minh -------------------------------------------------------------


async def test_dangerous_verification_raises_the_level_in_state_and_in_the_incident(world: World) -> None:
    await add_verification(world, world.incident, "dangerous")
    async with running(world) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.waiting_for == "await_guardian"
        assert status.level == "critical"
    row = await incident_row(world.incident)
    assert (row.level, row.rule_floor) == ("critical", "high")
    (verify,) = await steps(thread, "verify")
    assert verify.output == {
        "checked": 1,
        "dangerous": 1,
        "warning": 0,
        "level_before": "high",
        "level_after": "critical",
    }
    assert verify.model_profile is None
    assert verify.tokens_in == 0 and verify.cost_usd == 0  # không LLM


async def test_warning_verification_raises_to_high_only(world: World) -> None:
    async with get_sessionmaker().begin() as session:  # sự cố khởi đầu ở mức medium với sàn medium
        await session.execute(
            text("update incidents set level = 'medium', rule_floor = 'medium' where id = :i"), {"i": world.incident}
        )
    await add_verification(world, world.incident, "warning")
    await add_verification(world, world.incident, "unknown")
    medium_event = demo_event().model_copy(update={"caller": None, "rule_floor": RiskLevel.MEDIUM})
    async with running(world) as (runtime, thread):
        status = await runtime.start(
            medium_event, incident_id=thread, elder_alias="Mẹ", is_demo=True, family_id=str(world.family)
        )
        assert status.level == "high"
    assert (await incident_row(world.incident)).level == "high"
    (verify,) = await steps(thread, "verify")
    assert verify.output["warning"] == 1 and verify.output["dangerous"] == 0 and verify.output["checked"] == 2


async def test_no_verification_leaves_the_level_alone(world: World) -> None:
    async with running(world) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.level == "high"
    row = await incident_row(world.incident)
    assert (row.level, row.version) == ("high", 1)
    (verify,) = await steps(thread, "verify")
    assert verify.output == {"checked": 0, "dangerous": 0, "warning": 0, "level_before": "high", "level_after": "high"}


async def test_unknown_results_never_raise_the_level(world: World) -> None:
    await add_verification(world, world.incident, "unknown")
    async with running(world) as (runtime, thread):
        assert (await start(runtime, world, thread)).level == "high"
    assert (await incident_row(world.incident)).level == "high"


async def test_the_level_raised_by_the_risk_scorer_is_written_through(world: World) -> None:
    async with running(world, Client(level="critical")) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.level == "critical"
    row = await incident_row(world.incident)
    assert (row.level, row.version) == ("critical", 2)


async def test_the_level_never_drops_below_the_rule_floor_or_the_current_level(world: World) -> None:
    await add_verification(world, world.incident, "warning")
    async with running(world, Client(level="low")) as (runtime, thread):  # LLM cố hạ xuống `low`
        status = await start(runtime, world, thread)
        assert status.level == "high"
    row = await incident_row(world.incident)
    assert LEVELS.index(row.level) >= LEVELS.index(row.rule_floor)


async def test_verifications_of_other_incidents_are_ignored(world: World) -> None:
    await add_verification(world, world.drill_incident, "dangerous")
    await add_verification(world, None, "dangerous", via="call")
    async with running(world) as (runtime, thread):
        assert (await start(runtime, world, thread)).level == "high"
    (verify,) = await steps(thread, "verify")
    assert verify.output["checked"] == 0


async def test_a_run_without_an_incident_row_skips_the_database(require_db: None, threads: list[str]) -> None:
    """Lượt eval/demo: id không phải sự cố thật ⇒ không đọc/ghi `verifications` hay `incidents`."""
    thread = str(new_id())  # UUID nhưng không có dòng `incidents`
    threads.append(thread)
    async with IncidentRuntime.open(deps(Client())) as runtime:
        status = await runtime.start(event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        await runtime.graph.checkpointer.adelete_thread(thread)
    assert status.waiting_for == "await_guardian" and status.level == "high"
    eval_thread = f"eval-abcd1234-{new_id()}"
    threads.append(eval_thread)
    async with IncidentRuntime.open(deps(Client())) as runtime:
        status = await runtime.start(event(), incident_id=eval_thread, elder_alias="Mẹ", is_demo=True)
        await runtime.graph.checkpointer.adelete_thread(eval_thread)
    assert status.waiting_for == "await_guardian"


async def test_a_decided_incident_is_not_touched_by_the_verification_node(world: World) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update incidents set state = 'resolved_safe', outcome = 'safe', closed_at = now() where id = :i"),
            {"i": world.incident},
        )
    await add_verification(world, world.incident, "dangerous")
    async with running(world) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.status == "done"
    row = await incident_row(world.incident)
    assert (row.level, row.state) == ("high", "resolved_safe")
    assert await jobs(thread, "msg:detail") == []  # đã quyết ⇒ không gửi chi tiết


async def test_the_step_holds_no_identifier(world: World) -> None:
    await add_verification(world, world.incident, "dangerous")
    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
    (verify,) = await steps(thread, "verify")
    blob = json.dumps([verify.input_redacted, verify.output], ensure_ascii=False)
    async with get_sessionmaker()() as session:
        hmac = await session.scalar(select(Verification.subject_hmac).where(Verification.incident_id == world.incident))
    assert hmac and hmac not in blob and "123" not in blob


# --- await_guardian nhận `evidence` --------------------------------------------------------------------------------


async def evidence_texts(thread: str) -> list[str]:
    return [job.payload["text"] for job in await jobs(thread, "msg:evidence")]


async def timers(thread: str) -> dict[str, Any]:
    return {job.idempotency_key: job.run_at for job in await jobs(thread, "timer:")}


async def test_evidence_while_waiting_sends_exactly_one_message_and_keeps_the_timers(world: World) -> None:
    async with running(world) as (runtime, thread):
        assert (await start(runtime, world, thread)).waiting_for == "await_guardian"
        before = await timers(thread)
        assert {"t1", "t2", "t3"} <= {key.rsplit(":", 1)[1] for key in before}
        vid = await add_verification(world, world.incident, "dangerous")
        status = await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
        assert status.waiting_for == "await_guardian"  # quay lại chờ
        assert await timers(thread) == before  # hẹn giờ không bị dời
    (message,) = await evidence_texts(thread)
    assert message.startswith(AI_DISCLOSURE)
    assert "đuôi 123" in message
    assert mask_text(message) == message  # không chữ số dài, không link
    (job,) = await jobs(thread, "msg:evidence")
    assert job.payload["family_id"] == str(world.family)
    assert job.payload["template"] == "evidence"
    assert job.payload["is_drill"] is False


async def test_a_second_evidence_adds_no_message(world: World) -> None:
    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
        first = await add_verification(world, world.incident, "dangerous")
        second = await add_verification(world, world.incident, "dangerous", kind="url", last3=None)
        await runtime.resume(thread, {"evidence": str(first)}, expect="await_guardian")
        await runtime.resume(thread, {"evidence": str(second)}, expect="await_guardian")
        assert (await runtime.status(thread)).waiting_for == "await_guardian"
    assert len(await jobs(thread, "msg:evidence")) == 1


async def test_evidence_about_a_link_mentions_a_link_not_a_host(world: World) -> None:
    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
        vid = await add_verification(world, world.incident, "dangerous", kind="url", last3=None)
        await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
    (message,) = await evidence_texts(thread)
    assert "đường link" in message
    assert mask_text(message) == message


async def test_evidence_after_the_guardian_decided_sends_nothing(world: World) -> None:
    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
        async with get_sessionmaker().begin() as session:
            await session.execute(
                text("update incidents set state = 'resolved_safe', outcome = 'safe', closed_at = now() where id = :i"),
                {"i": world.incident},
            )
        vid = await add_verification(world, world.incident, "dangerous")
        status = await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
        assert status.status == "done"
    assert await evidence_texts(thread) == []


async def test_drill_incident_marks_the_evidence_message_as_a_drill(world: World) -> None:
    async with running(world, drill=True) as (runtime, thread):
        await start(runtime, world, thread, drill=True)
        vid = await add_verification(world, world.drill_incident, "dangerous")
        await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
    (message,) = await evidence_texts(thread)
    assert message.startswith(AI_DISCLOSURE)
    assert "[DIỄN TẬP]" in message
    (job,) = await jobs(thread, "msg:evidence")
    assert job.payload["is_drill"] is True


@pytest.mark.parametrize("which", ["unknown_id", "other_incident", "not_dangerous"])
async def test_evidence_that_does_not_check_out_sends_nothing(world: World, which: str) -> None:
    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
        vid = {
            "unknown_id": uuid4(),
            "other_incident": await add_verification(world, world.drill_incident, "dangerous"),
            "not_dangerous": await add_verification(world, world.incident, "unknown"),
        }[which]
        status = await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
        assert status.waiting_for == "await_guardian"
    assert await evidence_texts(thread) == []


async def test_evidence_before_the_graph_waits_for_the_guardian_is_ignored_then_gathered(world: World) -> None:
    async with running(world, Client(ask="q_know_caller")) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.waiting_for == "ask_elder"
        vid = await add_verification(world, world.incident, "dangerous")
        assert await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian") is None  # đến sớm
        status = await runtime.resume(thread, {"answer": "unsure"}, expect="ask_elder")
        assert status.waiting_for == "await_guardian" and status.level == "critical"  # `verification` gom dòng đó
    assert await evidence_texts(thread) == []  # không mất gì, cũng không gửi tin lúc chưa tới chỗ chờ


# --- clean_resume + riêng tư ---------------------------------------------------------------------------------------


def test_clean_resume_keeps_only_a_valid_evidence_uuid() -> None:
    vid = str(uuid4())
    assert clean_resume({"evidence": vid}) == {"evidence": vid}
    assert clean_resume({"evidence": vid.upper()}) == {"evidence": vid}
    for bad in ("not-a-uuid", "0900000123", "", 5, None, {"x": 1}):
        assert clean_resume({"evidence": bad}) == {"invalid": True}


async def test_checkpoint_and_jobs_hold_no_identifier(world: World) -> None:
    from hoicon.eval.checks import checkpoint_bytes

    async with running(world) as (runtime, thread):
        await start(runtime, world, thread)
        vid = await add_verification(world, world.incident, "dangerous")
        await runtime.resume(thread, {"evidence": str(vid)}, expect="await_guardian")
        raw = await checkpoint_bytes(get_sessionmaker(), thread)
    async with get_sessionmaker()() as session:
        hmac = await session.scalar(select(Verification.subject_hmac).where(Verification.id == vid))
        payloads = "\n".join(
            await session.scalars(
                text("select payload::text from jobs where idempotency_key like :k"), {"k": f"{thread}:%"}
            )
        )
    assert hmac
    assert hmac.encode() not in raw
    assert hmac not in payloads
