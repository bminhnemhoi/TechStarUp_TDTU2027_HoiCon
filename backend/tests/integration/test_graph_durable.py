"""Giết tiến trình (kill -9 / TerminateProcess) khi đồ thị đang ở giữa node risk_scorer ⇒ tiến trình mới chạy tiếp từ
checkpoint cuối, không gửi trùng tin đã xếp hàng (ADR-009, ROADMAP P1-S4)."""

import asyncio
import os
import subprocess
import sys
import time
from decimal import Decimal

import pytest
from sqlalchemy import select

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep, Job
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration


def run_child_until_llm(thread: str, timeout_s: float = 90) -> subprocess.Popen:
    child = subprocess.Popen(  # noqa: S603 — lệnh cố định, không có đầu vào ngoài
        [sys.executable, "-m", "hoicon.agents.spike", "crash", "--thread", thread],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    deadline = time.monotonic() + timeout_s
    assert child.stdout is not None
    for line in child.stdout:
        if "LLM_CALL_STARTED" in line:
            return child
        if time.monotonic() > deadline:
            break
    child.kill()
    raise AssertionError("tiến trình con không tới được node risk_scorer")


async def test_resumes_after_kill_9_without_duplicate_side_effects(threads: list[str]) -> None:
    thread = str(new_id())
    threads.append(thread)
    child = await asyncio.to_thread(run_child_until_llm, thread)
    child.kill()  # SIGKILL trên Linux, TerminateProcess trên Windows: không dọn dẹp gì
    child.wait(timeout=30)

    deps = Deps(LlmRouter(None, "claude-haiku-5-5", Decimal(1)), get_sessionmaker(), get_settings())
    async with IncidentRuntime.open(deps) as runtime:
        async with asyncio.timeout(60):  # khóa advisory của tiến trình chết phải được Postgres nhả
            recovered = {s.thread_id: s for s in await runtime.recover()}
        assert recovered[thread].waiting_for == "ask_elder"
        status = await runtime.resume(thread, {"answer": "yes"}, expect="ask_elder")
        assert status.waiting_for == "await_guardian"
        status = await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
        assert status.outcome == "resolved_prevented"
        await runtime.graph.checkpointer.adelete_thread(thread)

    async with get_sessionmaker()() as session:
        run = (await session.scalars(select(AgentRun).where(AgentRun.thread_id == thread))).one()
        nodes = list(await session.scalars(select(AgentStep.node).where(AgentStep.run_id == run.id)))
        alerts = list(await session.scalars(select(Job).where(Job.idempotency_key == f"{thread}:msg:fast_alert")))
    # ingest + fast_alert đã ghi checkpoint trước khi bị giết ⇒ không chạy lại; risk_scorer chạy lại sau phục hồi.
    assert nodes.count("ingest") == 1 and nodes.count("fast_alert") == 1
    assert len(alerts) == 1
    assert run.status == "done"
