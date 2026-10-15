"""US1 (FR-005/006/008/014, SC-006): `notify_guardian` gửi qua một client, đúng người, đúng một lần."""

import dataclasses
import uuid
from typing import Any

import pytest

from hoicon.agents import texts
from hoicon.channels.guardian import quota_month, send_to_guardian
from hoicon.channels.zalo import MockZaloClient, ZaloError
from hoicon.jobs.queue import MAX_ATTEMPTS
from hoicon.jobs.worker import incident_handlers

pytestmark = pytest.mark.integration


def payload(world: Any, incident: str, **override: Any) -> dict[str, Any]:
    is_drill = override.get("is_drill", False)
    base = {
        "incident_id": incident,
        "family_id": str(world.family.id),
        "template": "fast_alert",
        "text": texts.guardian_fast_alert("Mẹ", "002", "bank", is_drill),
        "guardian_rank": 1,
        "is_drill": is_drill,
        "is_demo": True,
    }
    return {**base, **override}


@dataclasses.dataclass
class FlakyClient(MockZaloClient):
    """Mock thất bại theo kịch bản trước khi chạy bình thường."""

    failures: list[ZaloError] = dataclasses.field(default_factory=list)

    async def send_message(self, chat_id: str, text: str) -> Any:
        if self.failures:
            raise self.failures.pop(0)
        return await super().send_message(chat_id, text)


async def test_alert_goes_to_rank_1_once_with_a_messages_out_row(zalo_world: Any) -> None:
    world = zalo_world
    member = await world.add_guardian(1)
    other = await world.add_guardian(2)
    incident = world.new_incident()

    assert await send_to_guardian(world.deps, payload(world, incident)) == "sent"

    (sent,) = world.client.sent
    assert sent.chat_id == world.zalo_ids[1][1] and sent.chat_id != world.zalo_ids[2][1]
    assert sent.text.startswith("Đây là trợ lý AI HỏiCon.")  # luật 6, SC-006
    (row,) = await world.rows()
    assert (row.status, row.channel, row.template_id, row.bot_id) == ("sent", "zalo", "fast_alert", world.bot_id)
    assert (row.member_id, row.family_id, row.incident_id) == (member.id, world.family.id, uuid.UUID(incident))
    assert row.job_key == f"{incident}:msg:fast_alert" and row.sent_at is not None
    assert row.error == "mock"  # gửi bằng MockZaloClient: nhìn vào bảng là biết tin KHÔNG tới người nhận
    assert row.quota_month == quota_month()
    assert other.id != row.member_id


async def test_escalation_goes_to_rank_2(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    await world.add_guardian(2)
    incident = world.new_incident()
    text = texts.guardian_escalation("Mẹ", False)
    await send_to_guardian(world.deps, payload(world, incident, template="escalation", guardian_rank=2, text=text))
    (sent,) = world.client.sent
    assert sent.chat_id == world.zalo_ids[2][1]


async def test_drill_label_survives_to_the_wire(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    text = texts.guardian_fast_alert("Bố", None, "other", True)
    await send_to_guardian(world.deps, payload(world, world.new_incident(), is_drill=True, text=text))
    assert world.client.sent[0].text.startswith("Đây là trợ lý AI HỏiCon. [DIỄN TẬP]")  # luật 8


async def test_retry_never_sends_twice(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    p = payload(world, world.new_incident())
    assert await send_to_guardian(world.deps, p, attempt=1) == "sent"
    assert await send_to_guardian(world.deps, p, attempt=2) == "sent"  # job chạy lại sau khi đã xong
    assert len(world.client.sent) == 1 and len(await world.rows()) == 1


async def test_transient_error_raises_for_retry_then_sends_exactly_once(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    flaky = FlakyClient(failures=[ZaloError(500), ZaloError(None)])
    deps = dataclasses.replace(world.deps, client=flaky)
    p = payload(world, world.new_incident())
    with pytest.raises(ZaloError):
        await send_to_guardian(deps, p, attempt=1)
    assert (await world.rows())[0].status == "queued" and (await world.rows())[0].error == "zalo_500"
    with pytest.raises(ZaloError):
        await send_to_guardian(deps, p, attempt=2)
    assert await send_to_guardian(deps, p, attempt=3) == "sent"
    assert len(flaky.sent) == 1 and len(await world.rows()) == 1


async def test_permanent_error_needs_fallback_and_is_not_retried(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    flaky = FlakyClient(failures=[ZaloError(401)])
    deps = dataclasses.replace(world.deps, client=flaky)
    p = payload(world, world.new_incident())
    assert await send_to_guardian(deps, p) == "fallback_required"  # không raise ⇒ hàng đợi không thử lại
    row = (await world.rows())[0]
    assert (row.status, row.error) == ("fallback_required", "zalo_401")
    assert await send_to_guardian(deps, p, attempt=2) == "fallback_required"  # đã kết thúc: không gọi Zalo lần nữa
    assert flaky.sent == [] and flaky.failures == []


async def test_transient_error_on_last_attempt_needs_fallback(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    deps = dataclasses.replace(world.deps, client=FlakyClient(failures=[ZaloError(503)]))
    status = await send_to_guardian(deps, payload(world, world.new_incident()), attempt=MAX_ATTEMPTS)
    assert status == "fallback_required"  # FR-008: hết số lần thử


async def test_missing_guardian_or_zalo_needs_fallback(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)  # chỉ có hạng 1; tin chuyển hạng 2 không có người nhận
    incident = world.new_incident()
    p = payload(world, incident, template="escalation", guardian_rank=2, text=texts.guardian_escalation("Mẹ", False))
    assert await send_to_guardian(world.deps, p) == "fallback_required"
    (row,) = await world.rows()
    assert row.error == "no_recipient" and row.member_id is None
    assert world.client.sent == []


async def test_demo_incident_never_reaches_a_real_family(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    from sqlalchemy import update

    from hoicon.db.models import Family
    from hoicon.db.session import get_sessionmaker

    async with get_sessionmaker().begin() as session:
        await session.execute(update(Family).where(Family.id == world.family.id).values(is_demo=False))
    assert await send_to_guardian(world.deps, payload(world, world.new_incident(), is_demo=True)) == "failed"
    assert world.client.sent == []
    assert (await world.rows())[0].error == "demo_to_real_family"  # FR-014


async def test_message_without_ai_disclosure_is_refused_at_the_gate(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    assert (
        await send_to_guardian(world.deps, payload(world, world.new_incident(), text="Bác ơi, cẩn thận!")) == "failed"
    )
    assert world.client.sent == [] and (await world.rows())[0].error == "no_ai_disclosure"


async def test_unknown_family_or_no_family_sends_nothing(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    no_family = payload(world, world.new_incident(), family_id=None)
    assert await send_to_guardian(world.deps, no_family) is None  # sự cố chưa gắn gia đình: giữ hành vi cũ (chỉ log)
    unknown = payload(world, world.new_incident(), family_id=str(uuid.uuid4()))
    assert await send_to_guardian(world.deps, unknown) is None
    assert world.client.sent == [] and await world.rows() == []


async def test_job_handler_wires_attempt_and_uses_the_same_gate(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    handler = incident_handlers(None, world.deps)["notify_guardian"]  # type: ignore[arg-type]
    p = payload(world, world.new_incident())
    await handler({**p, "_attempt": 1})
    await handler({**p, "_attempt": 2})
    assert len(world.client.sent) == 1


async def test_logs_never_contain_message_text_or_ids(zalo_world: Any, caplog: pytest.LogCaptureFixture) -> None:
    import logging

    world = zalo_world
    await world.add_guardian(1)
    with caplog.at_level(logging.DEBUG):
        await send_to_guardian(world.deps, payload(world, world.new_incident()))
    user_id, chat_id = world.zalo_ids[1]
    assert chat_id not in caplog.text and user_id not in caplog.text
    assert "số lạ đuôi" not in caplog.text  # nội dung tin không vào log
