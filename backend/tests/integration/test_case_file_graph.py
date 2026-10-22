"""Spec 031 FR-003/FR-006 (SC-001): nhánh `resolve → case_file → await_case_approval` của đồ thị trên Postgres thật."""

import json
from collections.abc import AsyncGenerator
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from case_support import purge_case, seed_case
from sqlalchemy import func, select

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime, prepare_event
from hoicon.agents.spike import demo_event
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, AgentStep, CaseFile, Job
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration


def deps() -> Deps:
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60})
    return Deps(LlmRouter(None, "claude-haiku-5-5", Decimal(10)), get_sessionmaker(), settings)  # không khóa ⇒ mẫu


@pytest.fixture
async def world(require_db: None, seeded_threat: dict[str, Any]) -> AsyncGenerator[SimpleNamespace]:
    w = await seed_case(state="detected", with_run=False, flagged=False, answers=())
    yield w
    await purge_case(w)


async def drive_to_decision(runtime: IncidentRuntime, w: SimpleNamespace, decision: str, drill: bool = False) -> Any:
    event = demo_event()
    if drill:
        event = event.model_copy(update={"is_drill": True, "drill_id": w.incident})
    thread = str(w.incident)
    status = await runtime.start(event, incident_id=thread, elder_alias="Mẹ", family_id=str(w.family), is_demo=True)
    while status.waiting_for == "ask_elder":
        status = await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
    assert status.waiting_for == "await_guardian"
    return await runtime.resume(thread, {"decision": decision}, expect="await_guardian")


async def case_rows(w: SimpleNamespace) -> list[CaseFile]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(CaseFile).where(CaseFile.incident_id == w.incident)))


async def case_messages(w: SimpleNamespace) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(Job).where(Job.idempotency_key == f"{w.incident}:msg:case_file")))


async def test_scam_creates_one_draft_one_message_and_waits_for_approval(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        status = await drive_to_decision(runtime, world, "scam")
        assert status.waiting_for == "await_case_approval" and status.outcome == "case_open"
        (row,) = await case_rows(world)
        assert row.status == "draft" and row.is_demo is True and row.summary_source == "template"
        assert row.content["ai_label"].startswith("Đây là trợ lý AI HỏiCon")
        (job,) = await case_messages(world)
        assert job.payload["text"].startswith("Đây là trợ lý AI HỏiCon")
        assert "http" not in job.payload["text"] and "{action_link}" not in job.payload["text"]
        assert job.payload["is_drill"] is False and job.payload["template"] == "case_file"
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))


async def test_discarding_ends_the_graph(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        await drive_to_decision(runtime, world, "scam")
        status = await runtime.resume(
            str(world.incident), {"case_action": "discard", "actor": "guardian"}, expect="await_case_approval"
        )
        assert status.status == "done"
        again = await runtime.resume(str(world.incident), {"case_action": "approve"}, expect="await_case_approval")
        assert again is None  # đến muộn: không còn chờ
        assert len(await case_rows(world)) == 1 and len(await case_messages(world)) == 1
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))


async def test_other_outcomes_have_no_case_file(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        status = await drive_to_decision(runtime, world, "safe")
        assert status.status == "done" and status.outcome == "resolved_safe"
        assert await case_rows(world) == [] and await case_messages(world) == []
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))


async def test_a_drill_never_gets_a_case_file(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        status = await drive_to_decision(runtime, world, "scam", drill=True)
        assert status.status == "done"
        assert await case_rows(world) == [] and await case_messages(world) == []
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))


async def test_eval_and_demo_threads_without_a_real_incident_have_no_case_file(
    world: SimpleNamespace, threads: list[str]
) -> None:
    thread = f"eval-test-{world.incident}"  # không phải UUID: như lượt eval
    threads.append(thread)  # job `eval-*` còn sót làm đỏ test "không để lại job" của suite eval
    async with IncidentRuntime.open(deps()) as runtime:
        status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        while status.waiting_for == "ask_elder":
            status = await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
        status = await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
        assert status.status == "done"
        assert await case_rows(world) == []
        await runtime.graph.checkpointer.adelete_thread(thread)


async def test_a_restarted_runtime_still_waits_at_the_same_interrupt(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        await drive_to_decision(runtime, world, "scam")
    async with IncidentRuntime.open(deps()) as fresh:  # như kill -9 rồi dựng lại tiến trình
        status = await fresh.status(str(world.incident))
        assert status.waiting_for == "await_case_approval"
        done = await fresh.resume(str(world.incident), {"case_action": "approve"}, expect="await_case_approval")
        assert done is not None and done.status == "done"
        await fresh.graph.checkpointer.adelete_thread(str(world.incident))


async def test_steps_record_codes_only_and_no_secrets(world: SimpleNamespace) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        await drive_to_decision(runtime, world, "scam")
        async with get_sessionmaker()() as session:
            run = await session.scalar(select(AgentRun).where(AgentRun.thread_id == str(world.incident)))
            steps = (await session.scalars(select(AgentStep).where(AgentStep.run_id == run.id))).all()
            count = await session.scalar(
                select(func.count()).select_from(AgentStep).where(AgentStep.node == "case_file")
            )
        assert count >= 1
        dump = json.dumps([s.output for s in steps if s.node == "case_file"], ensure_ascii=False)
        assert "summary_source" in dump and "vn.hoicon" not in dump
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))


async def test_without_guardian_alerts_consent_there_is_no_case_file(world: SimpleNamespace) -> None:
    thread = str(world.incident)
    async with IncidentRuntime.open(deps()) as runtime:
        threat, event_data = await prepare_event(get_sessionmaker(), demo_event())
        status = await runtime.start_prepared(
            event_data,
            threat,
            incident_id=thread,
            elder_alias="Mẹ",
            is_demo=True,
            family_id=str(world.family),
            guardian_alerts=False,
        )
        while status.waiting_for == "ask_elder":
            status = await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
        status = await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
        assert status.status == "done"
        assert await case_rows(world) == [] and await case_messages(world) == []
        await runtime.graph.checkpointer.adelete_thread(thread)


async def test_a_failure_while_building_the_case_file_does_not_break_the_incident(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.services import case_file_service

    async def boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("DB chớp")

    monkeypatch.setattr(case_file_service, "build_content", boom)
    async with IncidentRuntime.open(deps()) as runtime:
        status = await drive_to_decision(runtime, world, "scam")
        assert status.status == "done" and status.outcome == "case_open"  # không treo ở await_case_approval
        assert await case_rows(world) == [] and await case_messages(world) == []
        async with get_sessionmaker()() as session:
            run = await session.scalar(select(AgentRun).where(AgentRun.thread_id == str(world.incident)))
            steps = (
                await session.scalars(
                    select(AgentStep).where(AgentStep.run_id == run.id, AgentStep.node == "case_file")
                )
            ).all()
        assert steps and steps[0].output["created"] is False and steps[0].output["error"] == "RuntimeError"
        await runtime.graph.checkpointer.adelete_thread(str(world.incident))
