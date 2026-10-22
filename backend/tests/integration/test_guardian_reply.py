"""US3 (FR-009, SC-006): người giám hộ trả lời 1/2/3 ⇒ đồ thị sự cố chạy tiếp; văn bản trả lời không được lưu."""

import json
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select

from hoicon.agents import texts
from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.agents.spike import demo_event
from hoicon.channels.guardian import send_to_guardian
from hoicon.channels.updates import handle_update
from hoicon.db.models import Job
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import ATTEMPT_KEY
from hoicon.jobs.worker import incident_handlers

pytestmark = pytest.mark.integration

USER_1, USER_2 = "fixture-user-1", "fixture-user-2"


@pytest.fixture
async def runtime(zalo_world: Any) -> Any:
    # Không có client LLM ⇒ mọi node rơi về mẫu soạn sẵn, không gọi mạng. Hẹn giờ dài: không đến hạn trong test.
    settings = zalo_world.settings.model_copy(update={"timer_t1_s": 3600, "timer_t2_s": 7200, "timer_t3_s": 9000})
    deps = Deps(LlmRouter(None, "claude-haiku-4-5", Decimal(10)), get_sessionmaker(), settings)
    async with IncidentRuntime.open(deps) as rt:
        yield rt


async def pair(world: Any, user: str, rank: int) -> None:
    await handle_update(world.deps, None, world.update_payload(user, kind="start", value=await world.make_code()))
    members = {m.guardian_rank: m for m in await world.members()}
    assert rank in members  # đúng hạng mong đợi (ghép theo thứ tự)


async def deliver_pending(world: Any, incident: str) -> None:
    """Giả lập worker: gửi mọi tin `notify_guardian` đã xếp của sự cố (idempotent theo khóa)."""
    async with get_sessionmaker()() as session:
        query = select(Job).where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{incident}:msg:"))
        jobs = list((await session.scalars(query.order_by(Job.created_at))).all())
    for job in jobs:
        await send_to_guardian(world.deps, job.payload)


async def open_incident(world: Any, rt: Any, threads: list[str], *, is_drill: bool = False) -> str:
    incident = world.new_incident()
    threads.append(incident)
    await rt.start(
        demo_event(is_drill=is_drill),
        incident_id=incident,
        elder_alias="Mẹ",
        is_demo=True,
        family_id=str(world.family.id),
    )
    await rt.resume(incident, {"answer": "no"}, expect="ask_elder")
    await deliver_pending(world, incident)
    assert (await rt.status(incident)).waiting_for == "await_guardian"
    return incident


async def reply(world: Any, user: str, choice: str, rt: Any, message_id: str | None = None) -> str | None:
    payload = world.update_payload(user, kind="choice", value=choice, message_id=message_id)
    return await handle_update(world.deps, rt, payload)


async def finish(rt: Any, incident: str) -> None:
    await rt.graph.checkpointer.adelete_thread(incident)


async def test_1_resumes_the_graph_as_safe_and_acknowledges(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    assert await reply(world, USER_1, "1", runtime) == "sent"
    status = await runtime.status(incident)
    assert (status.status, status.outcome) == ("done", "resolved_safe")
    assert world.sent_to(USER_1)[-1] == texts.guardian_ack("safe", False)
    ack = [r for r in await world.rows() if r.template_id == "ack_safe"]
    assert len(ack) == 1 and str(ack[0].incident_id) == incident
    await finish(runtime, incident)


async def test_2_resumes_the_graph_as_scam(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    await reply(world, USER_1, "2", runtime)
    assert (await runtime.status(incident)).outcome == "case_open"  # spec 023/024: "2 - nghi lừa đảo" mở hồ sơ
    assert world.sent_to(USER_1)[-1] == texts.guardian_ack("scam", False)
    await finish(runtime, incident)


async def test_3_sends_the_detail_again_without_changing_the_incident(
    zalo_world: Any, runtime: Any, threads: list[str]
) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    detail_text = next(m.text for m in world.client.sent if "Mức nguy cơ" in m.text)
    await reply(world, USER_1, "3", runtime)
    assert world.sent_to(USER_1)[-1] == detail_text
    assert (await runtime.status(incident)).waiting_for == "await_guardian"  # vẫn chờ quyết định
    await reply(world, USER_1, "3", runtime)  # hỏi lại bao nhiêu lần cũng không đổi gì
    assert (await runtime.status(incident)).status == "waiting"
    await finish(runtime, incident)


async def test_3_before_the_detail_exists_says_it_is_coming(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = world.new_incident()
    threads.append(incident)
    await runtime.start(
        demo_event(), incident_id=incident, elder_alias="Mẹ", is_demo=True, family_id=str(world.family.id)
    )
    await deliver_pending(world, incident)  # mới có tin cảnh báo nhanh, chưa có chi tiết (còn đang hỏi người cao tuổi)
    await reply(world, USER_1, "3", runtime)
    assert world.sent_to(USER_1)[-1] == texts.detail_pending(False)
    assert (await runtime.status(incident)).waiting_for == "ask_elder"
    await finish(runtime, incident)


async def test_unclear_reply_gets_instructions_and_changes_nothing(
    zalo_world: Any, runtime: Any, threads: list[str]
) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    payload = world.update_payload(USER_1, kind="other")
    await handle_update(world.deps, runtime, payload)
    assert world.sent_to(USER_1)[-1] == texts.reply_help()
    assert (await runtime.status(incident)).status == "waiting"
    await finish(runtime, incident)


async def test_reply_when_nothing_is_waiting(zalo_world: Any, runtime: Any) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    await reply(world, USER_1, "1", runtime)
    assert world.sent_to(USER_1)[-1] == texts.reply_no_incident()


async def test_late_or_repeated_answer_does_not_resume_twice(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    await reply(world, USER_1, "1", runtime, message_id="fixture-msg-a")
    await reply(world, USER_1, "2", runtime, message_id="fixture-msg-b")  # đến sau khi đã đóng
    assert (await runtime.status(incident)).outcome == "resolved_safe"  # quyết định đầu tiên thắng
    assert world.sent_to(USER_1)[-1] == texts.reply_incident_closed(False)
    await reply(world, USER_1, "1", runtime, message_id="fixture-msg-a")  # Zalo giao lại đúng cập nhật cũ
    assert sum(t == texts.guardian_ack("safe", False) for t in world.sent_to(USER_1)) == 1
    await finish(runtime, incident)


async def test_rank_2_can_answer_after_escalation(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    await pair(world, USER_2, 2)
    incident = await open_incident(world, runtime, threads)
    await runtime.resume(incident, {"timer": "t2"}, expect="await_guardian")  # hẹn giờ T2 đến hạn
    await deliver_pending(world, incident)
    assert any(m.text.startswith(texts.guardian_escalation("Mẹ", False)[:60]) for m in world.client.sent)
    assert world.sent_to(USER_2)[0].startswith("Đây là trợ lý AI HỏiCon.")
    await reply(world, USER_2, "2", runtime)
    assert (await runtime.status(incident)).outcome == "case_open"
    await finish(runtime, incident)


async def test_drill_acknowledgement_carries_the_drill_label(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads, is_drill=True)
    await reply(world, USER_1, "1", runtime)
    assert world.sent_to(USER_1)[-1] == texts.guardian_ack("safe", True)  # luật 8
    assert "[DIỄN TẬP]" in world.sent_to(USER_1)[-1]
    await finish(runtime, incident)


async def test_reply_text_is_never_stored(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    secret_text = "mã của tôi là 987654 gọi 0900000001"
    payload = world.update_payload(USER_1, kind="other")
    assert secret_text not in json.dumps(payload)  # webhook đã bỏ chữ thô trước khi xếp job
    await handle_update(world.deps, runtime, payload)
    for row in await world.rows():
        assert secret_text not in repr(vars(row))
    await finish(runtime, incident)


async def test_job_handler_registered_and_wired(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads)
    handler = incident_handlers(runtime, world.deps)["zalo_update"]
    payload = world.update_payload(USER_1, kind="choice", value="1")
    await handler({**payload, ATTEMPT_KEY: 1})
    assert (await runtime.status(incident)).outcome == "resolved_safe"
    await finish(runtime, incident)


async def test_drill_label_survives_a_chain_of_replies(zalo_world: Any, runtime: Any, threads: list[str]) -> None:
    """M3: sau khi trả lời "3" (tin trả lời không có job gốc), tin xác nhận "1" vẫn phải mang nhãn diễn tập (luật 8)."""
    world = zalo_world
    await pair(world, USER_1, 1)
    incident = await open_incident(world, runtime, threads, is_drill=True)
    await reply(world, USER_1, "3", runtime)
    assert "[DIỄN TẬP]" in world.sent_to(USER_1)[-1]
    await reply(world, USER_1, "1", runtime)
    assert world.sent_to(USER_1)[-1] == texts.guardian_ack("safe", True)
    assert (await runtime.status(incident)).outcome == "resolved_safe"
    await finish(runtime, incident)


# --- Spec 032 FR-007: lệnh tắt/bật bản tin tuần -------------------------------------------------------------------


async def digest_flag(member_id: Any) -> bool:
    from hoicon.db.models import Member as _Member

    async with get_sessionmaker()() as session:
        return bool(await session.scalar(select(_Member.weekly_digest_enabled).where(_Member.id == member_id)))


async def test_digest_off_and_on_update_only_that_guardian_and_reply_with_an_ack(zalo_world: Any) -> None:
    first = await zalo_world.add_guardian(1)
    second = await zalo_world.add_guardian(2)
    user1, _ = zalo_world.zalo_ids[1]
    status = await handle_update(zalo_world.deps, None, zalo_world.update_payload(user1, kind="digest_off"))
    assert status == "sent"
    assert await digest_flag(first.id) is False and await digest_flag(second.id) is True
    ack = zalo_world.client.sent[-1].text
    assert ack.startswith(texts.AI_DISCLOSURE) and "vẫn nhận cảnh báo khi có chuyện" in ack
    assert await handle_update(zalo_world.deps, None, zalo_world.update_payload(user1, kind="digest_on")) == "sent"
    assert await digest_flag(first.id) is True
    assert "Đã bật lại bản tin tuần" in zalo_world.client.sent[-1].text


async def test_a_stranger_cannot_change_any_digest_flag(zalo_world: Any) -> None:
    guardian = await zalo_world.add_guardian(1)
    status = await handle_update(zalo_world.deps, None, zalo_world.update_payload("nguoi-la-1", kind="digest_off"))
    assert status == "sent"  # chỉ nhận câu hướng dẫn ghép đôi
    assert await digest_flag(guardian.id) is True
    assert "Đã tắt bản tin tuần" not in zalo_world.client.sent[-1].text


async def test_digest_commands_are_idempotent(zalo_world: Any) -> None:
    guardian = await zalo_world.add_guardian(1)
    user, _ = zalo_world.zalo_ids[1]
    for _ in range(2):
        await handle_update(zalo_world.deps, None, zalo_world.update_payload(user, kind="digest_off"))
    assert await digest_flag(guardian.id) is False
