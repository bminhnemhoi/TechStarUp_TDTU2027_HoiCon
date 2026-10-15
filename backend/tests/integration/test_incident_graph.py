"""Đồ thị sự cố trên Postgres thật: 2 interrupt, bộ hẹn giờ bằng job, LLM chỉ nâng mức, công khai AI, che PII."""

import asyncio
import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import func, select

from hoicon.agents.incident_graph import Deps, GuardianBrief, RiskAssessment
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.agents.spike import DEMO_H1, demo_event
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep, Job
from hoicon.db.session import get_sessionmaker
from hoicon.eval.checks import checkpoint_bytes
from hoicon.jobs.queue import run_once
from hoicon.jobs.worker import incident_handlers

pytestmark = pytest.mark.integration


class ScriptedClient:
    """LLM giả cư xử TỆ: cố hạ mức rủi ro và nhét số điện thoại + link vào tóm tắt gửi người giám hộ."""

    def with_options(self, **_: Any) -> "ScriptedClient":
        return self

    @property
    def messages(self) -> "ScriptedClient":
        return self

    async def parse(self, *, output_format: type, **_: Any) -> Any:
        if output_format is RiskAssessment:
            output = RiskAssessment(level="low", tactic="legit_likely", reasons=["ok"], ask_question="q_know_caller")
        else:
            output = GuardianBrief(
                summary="Gọi ngay 0900000003 hoặc vào https://x.example để xử lý.", action="call_now"
            )
        usage = SimpleNamespace(input_tokens=800, output_tokens=100)
        return SimpleNamespace(parsed_output=output, stop_reason="end_turn", usage=usage)


def deps(**timers: int) -> Deps:
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60, **timers})
    return Deps(LlmRouter(ScriptedClient(), "claude-haiku-4-5", Decimal(10)), get_sessionmaker(), settings)


async def drain(d: Deps, runtime: IncidentRuntime) -> None:
    """Chạy hết job đến hạn (DB dev có thể còn job cũ: một lượt `run_once` chỉ lấy 10 job sớm nhất)."""
    while await run_once(d.sessions, incident_handlers(runtime), "test-worker"):
        pass


async def jobs_for(thread: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(Job).where(Job.idempotency_key.startswith(f"{thread}:"))))


async def test_full_incident_flow(threads: list[str], seeded_threat: dict[str, Any]) -> None:
    d = deps(timer_t1_s=1, timer_t2_s=2)
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(d) as runtime:
        status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        # Số trong danh sách đe dọa ⇒ critical; LLM đề xuất "low" nhưng không được hạ.
        assert status.waiting_for == "ask_elder" and status.level == "critical"
        assert status.interrupt["question_id"] == "q_know_caller"
        assert status.interrupt["text"].startswith("Đây là trợ lý AI HỏiCon")

        note = "Họ bảo đọc mã OTP 123456 và gọi lại 0900000001"
        status = await runtime.resume(thread, {"answer": "no", "note": note}, expect="ask_elder")
        assert status.waiting_for == "await_guardian" and status.level == "critical"
        # Hẹn giờ hỏi người cao tuổi đến muộn: bị bỏ qua, không đẩy nhầm vào chỗ chờ người giám hộ.
        assert await runtime.resume(thread, {"timeout": True}, expect="ask_elder") is None

        await asyncio.sleep(2.3)  # T1 (1 s) và T2 (2 s) đến hạn
        await drain(d, runtime)
        assert (await runtime.status(thread)).waiting_for == "await_guardian"

        status = await runtime.resume(thread, {"decision": "safe"}, expect="await_guardian")
        assert status.status == "done" and status.outcome == "resolved_safe"

        values = (await runtime.graph.aget_state({"configurable": {"thread_id": thread}})).values
        assert values["elder_answer"]["note_flags"]["mentions_code"] is True and "note" not in values["elder_answer"]
        # Lời kể thô (OTP, số điện thoại), h1 của số gọi đến và tên gói app không nằm ở đâu trong checkpoint (ADR-006).
        raw = await checkpoint_bytes(get_sessionmaker(), thread)
        assert raw, "không đọc được bảng checkpoint"
        for secret in ("123456", "0900000001", DEMO_H1, "vn.hoicon.demobank"):
            assert secret.encode() not in raw, secret
        await runtime.graph.checkpointer.adelete_thread(thread)

    jobs = await jobs_for(thread)
    messages = {j.idempotency_key.rsplit(":", 1)[1]: j.payload for j in jobs if j.kind == "notify_guardian"}
    assert set(messages) == {"fast_alert", "detail", "reminder", "escalation"}  # mỗi tin đúng một lần
    assert messages["escalation"]["guardian_rank"] == 2
    for payload in messages.values():
        assert payload["text"].startswith("Đây là trợ lý AI HỏiCon"), payload["text"]
        assert payload["is_demo"] is True and payload["is_drill"] is False  # luật 8
    detail = messages["detail"]["text"]
    # LLM chèn số + link vào tóm tắt ⇒ tóm tắt bị thay bằng câu mẫu; mức rất cao luôn kèm "giữ máy".
    assert "0900000003" not in detail and "x.example" not in detail and "rất cao" in detail
    assert "giữ máy" in detail
    pending_timers = [j for j in jobs if j.kind == "graph_resume" and j.done_at is None]
    assert pending_timers == []  # T3 và hẹn giờ hỏi người cao tuổi đã bị hủy

    async with get_sessionmaker()() as session:
        run = (await session.scalars(select(AgentRun).where(AgentRun.thread_id == thread))).one()
        llm_cost = await session.scalar(select(func.sum(AgentStep.cost_usd)).where(AgentStep.run_id == run.id))
        nodes = list(await session.scalars(select(AgentStep.node).where(AgentStep.run_id == run.id)))
    assert run.status == "done" and run.finished_at is not None
    assert run.cost_usd == llm_cost > 0
    # SC-001 (spec 003): h1 của số gọi đến (kể cả khi số nằm trong danh sách đe dọa) cũng không nằm ở `agent_steps`.
    async with get_sessionmaker()() as session:
        steps = (await session.scalars(select(AgentStep).where(AgentStep.run_id == run.id))).all()
    steps_dump = json.dumps([[s.input_redacted, s.output] for s in steps], ensure_ascii=False)
    assert steps and DEMO_H1 not in steps_dump and "vn.hoicon.demobank" not in steps_dump
    assert nodes.count("risk_scorer") == 2 and nodes.count("fast_alert") == 1


async def test_guardian_silence_ends_as_no_response(threads: list[str]) -> None:
    d = deps(timer_t1_s=1, timer_t2_s=1, timer_t3_s=1)
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(d) as runtime:
        await runtime.start(demo_event(is_drill=True), incident_id=thread, elder_alias="Bố", is_demo=True)
        await runtime.resume(thread, {"answer": "unsure"}, expect="ask_elder")
        await asyncio.sleep(1.3)
        await drain(d, runtime)
        status = await runtime.status(thread)
        await runtime.graph.checkpointer.adelete_thread(thread)
    assert status.status == "done" and status.outcome == "resolved_no_response"
    texts = [j.payload["text"] for j in await jobs_for(thread) if j.kind == "notify_guardian"]
    assert texts and all("[DIỄN TẬP]" in t for t in texts)  # luật 8


async def test_threat_lookup_failure_does_not_block_the_incident(
    threads: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-004 / T6: danh sách đe dọa lỗi ⇒ `threat = unknown` + tên lớp lỗi; sự cố vẫn chạy, mức ≥ mức sàn của máy."""
    from sqlalchemy.exc import OperationalError

    async def broken(*_: Any, **__: Any) -> None:
        raise OperationalError("SELECT secret-connection-string", {}, Exception("password=hunter2"))

    monkeypatch.setattr("hoicon.agents.runtime.lookup_h1", broken)
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(deps()) as runtime:
        status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        values = (await runtime.graph.aget_state({"configurable": {"thread_id": thread}})).values
        raw = await checkpoint_bytes(get_sessionmaker(), thread)
        await runtime.graph.checkpointer.adelete_thread(thread)
    assert values["threat"] == {"verdict": "unknown", "error": "OperationalError"}
    assert status.waiting_for == "ask_elder"  # đường cảnh báo không bị chặn
    assert status.level in ("high", "critical")  # không thấp hơn mức sàn `high` của luật máy (luật 5)
    for secret in (DEMO_H1, "vn.hoicon.demobank", "hunter2", "secret-connection-string"):
        assert secret.encode() not in raw, secret


async def test_full_name_alias_is_rejected(threads: list[str]) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        with pytest.raises(ValueError):
            await runtime.start(demo_event(), incident_id=str(new_id()), elder_alias="Bà Nguyễn Thị Lan 1955")


async def test_family_id_reaches_every_guardian_message(threads: list[str]) -> None:
    family_id = str(new_id())
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(deps()) as runtime:
        await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True, family_id=family_id)
        await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
        values = (await runtime.graph.aget_state({"configurable": {"thread_id": thread}})).values
        await runtime.graph.checkpointer.adelete_thread(thread)
    assert values["family_id"] == family_id
    payloads = [j.payload for j in await jobs_for(thread) if j.kind == "notify_guardian"]
    assert len(payloads) >= 2 and {p["family_id"] for p in payloads} == {family_id}


async def test_family_id_is_optional_and_payload_stays_backward_compatible(threads: list[str]) -> None:
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(deps()) as runtime:
        await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        values = (await runtime.graph.aget_state({"configurable": {"thread_id": thread}})).values
        await runtime.graph.checkpointer.adelete_thread(thread)
    assert "family_id" not in values  # checkpoint cũ/không gia đình: trạng thái không đổi
    (payload,) = [j.payload for j in await jobs_for(thread) if j.kind == "notify_guardian"]
    assert payload["family_id"] is None
    # các khóa cũ còn nguyên, người đọc cũ (worker hiện tại) không bị ảnh hưởng
    assert {"incident_id", "template", "text", "guardian_rank", "is_drill", "is_demo"} <= payload.keys()


@pytest.mark.parametrize("bad", ["", "not-a-uuid", "0900000001", "x" * 40])
async def test_invalid_family_id_is_rejected_before_any_write(bad: str, threads: list[str]) -> None:
    thread = str(new_id())
    async with IncidentRuntime.open(deps()) as runtime:
        with pytest.raises(ValueError):
            await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", family_id=bad)
        assert await jobs_for(thread) == []
