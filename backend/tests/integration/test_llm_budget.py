"""Trần chi tiêu LLM bền qua khởi động lại (spec 003 US4): router cộng `agent_steps.cost_usd` của ngày giờ Việt Nam."""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import OperationalError

from hoicon.agents.incident_graph import RiskAssessment
from hoicon.agents.llm_router import LlmRouter, load_prompt
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

VN = ZoneInfo("Asia/Ho_Chi_Minh")
PROMPT = load_prompt("risk_scorer")
FALLBACK = RiskAssessment(level="high", tactic="unknown", reasons=["mẫu"], ask_question="q_asked_transfer")
ANSWER = RiskAssessment(level="critical", tactic="impersonation_authority", reasons=["x"], ask_question="none")
BUDGET = Decimal("1")


class FakeClient:
    def __init__(self, gate: asyncio.Event | None = None) -> None:
        self.calls = 0
        self.gate = gate

    def with_options(self, **_: Any) -> "FakeClient":
        return self

    @property
    def messages(self) -> "FakeClient":
        return self

    async def parse(self, **_: Any) -> Any:
        self.calls += 1
        if self.gate:
            await self.gate.wait()
        usage = SimpleNamespace(input_tokens=100, output_tokens=20)
        return SimpleNamespace(parsed_output=ANSWER, stop_reason="end_turn", usage=usage)


def start_of_today_vn() -> datetime:
    return datetime.now(VN).replace(hour=0, minute=0, second=0, microsecond=0)


@pytest.fixture
async def spend(require_db: None) -> AsyncGenerator[Any]:
    """`await spend(cost, at)`: ghi một bước agent_steps đã tính tiền; dọn run sau test."""
    runs: list[Any] = []

    async def add(cost: str, at: datetime) -> None:
        run = AgentRun(graph="incident", thread_id=str(new_id()), is_demo=True)
        async with get_sessionmaker().begin() as session:
            session.add(run)
            await session.flush()
            session.add(
                AgentStep(run_id=run.id, node="risk_scorer", model_profile="fast", cost_usd=Decimal(cost), at=at)
            )
        runs.append(run.id)

    yield add
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(AgentRun).where(AgentRun.id.in_(runs)))


async def call(router: LlmRouter) -> Any:
    return await router.structured(
        prompt=PROMPT, context={"rule_floor": "high"}, output=RiskAssessment, fallback=FALLBACK, consented=True
    )


def router_with(client: FakeClient, budget: Decimal = BUDGET, sessions: Any = None) -> LlmRouter:
    return LlmRouter(client, "claude-haiku-4-5", budget, sessions=sessions or get_sessionmaker())


async def test_todays_recorded_spend_survives_a_restart(spend: Any) -> None:
    await spend("1.0", datetime.now(UTC))
    client = FakeClient()
    result = await call(router_with(client))  # router MỚI (như sau khi tiến trình khởi động lại)
    assert result.fallback_used and result.error == "budget_exhausted" and result.output == FALLBACK
    assert client.calls == 0


async def test_yesterdays_spend_does_not_count_and_midnight_in_vietnam_is_the_boundary(spend: Any) -> None:
    await spend("1.0", start_of_today_vn() - timedelta(seconds=1))  # 23:59:59 hôm qua (giờ VN)
    client = FakeClient()
    assert not (await call(router_with(client))).fallback_used and client.calls == 1
    await spend("1.0", start_of_today_vn())  # đúng 00:00 hôm nay (giờ VN) thì tính
    assert (await call(router_with(FakeClient()))).error == "budget_exhausted"


async def test_spend_is_summed_across_steps(spend: Any) -> None:
    await spend("0.6", datetime.now(UTC))
    await spend("0.6", datetime.now(UTC))
    assert (await call(router_with(FakeClient()))).error == "budget_exhausted"


async def test_in_flight_reservation_is_added_to_the_recorded_spend(require_db: None) -> None:
    gate = asyncio.Event()
    client = FakeClient(gate)
    # DB dev đã có chi tiêu của test khác hôm nay ⇒ trần = chi tiêu hiện có + chỗ cho MỘT lời gọi (giữ chỗ ≈ 0,0032).
    recorded = await router_with(client)._recorded_spend()
    router = router_with(client, budget=recorded + Decimal("0.004"))
    first = asyncio.create_task(call(router))
    async with asyncio.timeout(5):
        while client.calls == 0:  # noqa: ASYNC110 — chờ lời gọi đầu vào tới client
            await asyncio.sleep(0.01)
    second = await call(router)  # lời gọi thứ hai khi lời gọi đầu còn đang bay
    assert second.error == "budget_exhausted" and client.calls == 1
    gate.set()
    assert not (await first).fallback_used
    # Chi phí thật chỉ vào `agent_steps` khi node ghi bước; router không giữ lại phần đã quyết toán ⇒ lời sau được phép.
    assert not (await call(router)).fallback_used


async def test_unreadable_database_falls_back_without_calling_the_llm() -> None:
    class Broken:
        def __call__(self) -> "Broken":
            return self

        async def __aenter__(self) -> None:
            raise OperationalError("SELECT secret-connection-string", {}, Exception("password=hunter2"))

        async def __aexit__(self, *_: Any) -> None:
            return None

    client = FakeClient()
    result = await call(router_with(client, sessions=Broken()))
    assert result.fallback_used and result.error == "budget_unknown" and client.calls == 0
    assert "hunter2" not in repr(result) and "secret-connection-string" not in repr(result)


async def test_router_without_sessions_keeps_the_in_memory_behaviour() -> None:
    client = FakeClient()
    tight = LlmRouter(client, "claude-haiku-4-5", Decimal("0.0001"))  # không `sessions`: không chạm DB
    assert (await call(tight)).error == "budget_exhausted" and client.calls == 0
    roomy = LlmRouter(client, "claude-haiku-4-5", Decimal("1"))
    assert not (await call(roomy)).fallback_used and client.calls == 1


async def test_a_failed_call_is_still_charged_its_reservation() -> None:
    """Lời gọi lỗi/quá hạn vẫn có thể bị tính tiền ⇒ ghi chi phí ước tính để `agent_steps` (nguồn của trần) có nó."""

    class Failing(FakeClient):
        async def parse(self, **_: Any) -> Any:
            self.calls += 1
            raise TimeoutError

    result = await call(router_with(Failing()))
    assert result.fallback_used and result.error == "TimeoutError"
    assert result.cost_usd > Decimal("0.003")  # ≈ phần giữ chỗ (≈ 0,0032), không phải 0


async def test_a_slow_budget_read_falls_back_instead_of_blocking_the_llm_path(monkeypatch: pytest.MonkeyPatch) -> None:
    router = router_with(FakeClient())

    async def slow() -> Decimal:
        await asyncio.sleep(10)
        return Decimal(0)

    monkeypatch.setattr(router, "_recorded_spend", slow)
    started = asyncio.get_running_loop().time()
    result = await call(router)
    assert result.error == "budget_unknown" and asyncio.get_running_loop().time() - started < 3  # luật 5: ≤ 4 s


async def test_an_error_that_cannot_have_been_billed_costs_nothing() -> None:
    """Hết kết nối/khóa sai không bị tính tiền ⇒ không ghi chi phí (tránh tắt LLM cả ngày vì nhà cung cấp hỏng)."""

    class Refused(FakeClient):
        async def parse(self, **_: Any) -> Any:
            self.calls += 1
            raise ConnectionError

    result = await call(router_with(Refused()))
    assert result.fallback_used and result.error == "ConnectionError" and result.cost_usd == 0
