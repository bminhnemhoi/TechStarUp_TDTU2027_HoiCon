"""Đồ thị sự cố trên Postgres thật: 2 interrupt, bộ hẹn giờ bằng job, LLM chỉ nâng mức, công khai AI, che PII."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import func, select, text

from hoicon.agents.incident_graph import Deps, GuardianBrief, RiskAssessment
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.agents.spike import DEMO_H1, demo_event
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep, Job
from hoicon.db.session import get_sessionmaker
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


async def checkpoint_bytes(thread: str) -> bytes:
    """Mọi thứ LangGraph đã ghi cho thread (state, blob, giá trị resume) — để kiểm không có dữ liệu thô nào lọt vào."""
    query = text(
        "SELECT blob FROM checkpoint_writes WHERE thread_id = :t AND blob IS NOT NULL "
        "UNION ALL SELECT blob FROM checkpoint_blobs WHERE thread_id = :t AND blob IS NOT NULL "
        "UNION ALL SELECT convert_to(checkpoint::text, 'UTF8') FROM checkpoints WHERE thread_id = :t"
    )
    async with get_sessionmaker()() as session:
        return b"".join(row[0] for row in await session.execute(query, {"t": thread}))


async def jobs_for(thread: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(Job).where(Job.idempotency_key.startswith(f"{thread}:"))))


async def test_full_incident_flow(threads: list[str]) -> None:
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
        raw = await checkpoint_bytes(thread)
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


async def test_full_name_alias_is_rejected(threads: list[str]) -> None:
    async with IncidentRuntime.open(deps()) as runtime:
        with pytest.raises(ValueError):
            await runtime.start(demo_event(), incident_id=str(new_id()), elder_alias="Bà Nguyễn Thị Lan 1955")
