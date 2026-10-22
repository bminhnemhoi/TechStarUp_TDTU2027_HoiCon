"""Spec 011 FR-006 / SC-006 (T013): `llm_processing` được thực thi ở máy chủ.

Người cao tuổi chưa đồng ý hoặc đã rút ⇒ đồ thị KHÔNG gọi nhà cung cấp LLM (kể cả khi có khóa), rơi về mẫu soạn sẵn,
`agent_steps` ghi `fallback_used` + lý do `consent`."""

from collections.abc import AsyncGenerator
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from case_support import seed_case
from consent_support import SHA, purge_family
from sqlalchemy import select

from hoicon.agents.incident_graph import Deps, GuardianBrief, RiskAssessment
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.agents.spike import demo_event
from hoicon.config import get_settings
from hoicon.db.models import AgentStep, Consent
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


class CountingClient:
    """LLM giả đếm số lời gọi; trả đúng dạng để lượt được cấp đồng ý chạy tới cùng."""

    def __init__(self) -> None:
        self.calls = 0

    def with_options(self, **_: Any) -> "CountingClient":
        return self

    @property
    def messages(self) -> "CountingClient":
        return self

    async def parse(self, *, output_format: type, **_: Any) -> Any:
        self.calls += 1
        if output_format is RiskAssessment:
            output = RiskAssessment(level="high", tactic="unknown", reasons=["x"], ask_question="none")
        else:
            output = GuardianBrief(points=["common_scam_pattern"], action="call_now")
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        return SimpleNamespace(parsed_output=output, stop_reason="end_turn", usage=usage)


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    consent_gate.reset_cache()


@pytest.fixture
async def world(require_db: None, seeded_threat: dict[str, Any]) -> AsyncGenerator[SimpleNamespace]:
    w = await seed_case(state="detected", with_run=False, flagged=False, answers=())
    yield w
    await purge_family(w.family)


async def grant(world: SimpleNamespace, granted: bool) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world.family,
                member_id=world.protected,
                purpose="llm_processing",
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()


async def run_incident(world: SimpleNamespace, *, is_demo: bool) -> CountingClient:
    client = CountingClient()
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60})
    deps = Deps(
        LlmRouter(client, "claude-haiku-5-5", Decimal(10), sessions=get_sessionmaker()), get_sessionmaker(), settings
    )
    async with IncidentRuntime.open(deps) as runtime:
        thread = str(world.incident)
        await runtime.start(
            demo_event(), incident_id=thread, elder_alias="Mẹ", family_id=str(world.family), is_demo=is_demo
        )
        await runtime.graph.checkpointer.adelete_thread(thread)
    return client


async def llm_steps(world: SimpleNamespace) -> list[AgentStep]:
    async with get_sessionmaker()() as session:
        rows = await session.scalars(
            select(AgentStep).where(AgentStep.model_profile.is_not(None)).order_by(AgentStep.at)
        )
        # các bước LLM của thread này: lọc theo run của sự cố
        from hoicon.db.models import AgentRun

        runs = set(await session.scalars(select(AgentRun.id).where(AgentRun.thread_id == str(world.incident))))
        return [s for s in rows if s.run_id in runs]


async def test_no_consent_row_means_no_provider_call_and_a_consent_fallback(world: SimpleNamespace) -> None:
    client = await run_incident(world, is_demo=False)
    steps = await llm_steps(world)
    assert client.calls == 0
    assert steps and all(s.fallback_used and s.error == "consent" and s.model is None for s in steps)


async def test_a_withdrawn_consent_means_no_provider_call(world: SimpleNamespace) -> None:
    await grant(world, True)
    await grant(world, False)
    assert (await run_incident(world, is_demo=False)).calls == 0


async def test_a_granted_consent_lets_the_provider_be_called(world: SimpleNamespace) -> None:
    await grant(world, True)
    client = await run_incident(world, is_demo=False)
    steps = await llm_steps(world)
    assert client.calls >= 2 and steps and not any(s.error == "consent" for s in steps)


async def test_other_purposes_do_not_stand_in_for_llm_processing(world: SimpleNamespace) -> None:
    async with get_sessionmaker().begin() as session:
        for purpose in ("core_protection", "guardian_alerts"):
            session.add(
                Consent(
                    family_id=world.family,
                    member_id=world.protected,
                    purpose=purpose,
                    granted=True,
                    consent_version="v1.0",
                    text_sha256=SHA,
                    channel="app",
                )
            )
    assert (await run_incident(world, is_demo=False)).calls == 0


async def test_demo_runs_hold_only_fictional_data_so_they_are_not_gated(world: SimpleNamespace) -> None:
    assert (await run_incident(world, is_demo=True)).calls >= 2


async def test_a_thread_with_no_incident_row_and_no_demo_flag_is_not_exempt(world: SimpleNamespace) -> None:
    """Không có dòng sự cố (hoặc người cao tuổi đã bị xóa) ⇒ không biết đồng ý ⇒ đóng, trừ eval/demo/mô phỏng."""
    from uuid import uuid4

    client = CountingClient()
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60})
    deps = Deps(
        LlmRouter(client, "claude-haiku-5-5", Decimal(10), sessions=get_sessionmaker()), get_sessionmaker(), settings
    )
    thread = str(uuid4())
    async with IncidentRuntime.open(deps) as runtime:
        await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=False)
        await runtime.graph.checkpointer.adelete_thread(thread)
    async with get_sessionmaker().begin() as session:
        from sqlalchemy import delete

        from hoicon.db.models import AgentRun, Job

        await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{thread}:")))
        await session.execute(delete(AgentRun).where(AgentRun.thread_id == thread))
    assert client.calls == 0


async def test_a_consent_changed_while_the_state_is_being_read_is_not_cached(world: SimpleNamespace) -> None:
    """Race: `invalidate` giữa lúc truy vấn đồng ý ⇒ kết quả trả về nhưng KHÔNG ghi đệm (không sống thêm 60 giây)."""
    await grant(world, True)
    consent_gate.reset_cache()
    async with get_sessionmaker()() as session:
        real_execute = session.execute

        async def execute_then_invalidate(*args: Any, **kwargs: Any) -> Any:
            result = await real_execute(*args, **kwargs)
            consent_gate.invalidate(world.protected)  # đồng ý đổi đúng lúc truy vấn đang chạy
            return result

        session.execute = execute_then_invalidate  # type: ignore[method-assign]
        state = await consent_gate.state_for(session, world.protected)
    assert state.llm_processing is True
    assert world.protected not in consent_gate._cache
