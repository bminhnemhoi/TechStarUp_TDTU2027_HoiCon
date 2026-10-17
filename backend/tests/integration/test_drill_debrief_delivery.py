"""Spec 028 FR-006, SC-001: tin tổng kết bài luyện tập đi qua `send_to_guardian`/`deliver` thật (không gắn sự cố).

Chạy từ job do `DrillService.record_result` xếp, rồi gửi bằng `MockZaloClient`: mở đầu công khai AI + [DIỄN TẬP], gửi
đúng một lần, tới đúng người giám hộ hạng 1, và không bao giờ lẫn demo với thật."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from drill_support import add_drill
from sqlalchemy import select, text

from hoicon.channels.guardian import send_to_guardian
from hoicon.db.models import Consent, Job, Member
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.domain import drill as dr
from hoicon.services.drill_service import DrillService

pytestmark = pytest.mark.integration

SCRIPT_ID = "drill_bank_card_locked"
SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.fixture
async def world(zalo_world: Any) -> AsyncGenerator[Any]:
    """Gia đình mẫu của spec 002 + dọn sổ đồng ý (chỉ-ghi-thêm: trigger chặn DELETE) trước khi nó xóa gia đình."""
    yield zalo_world
    async with get_engine().begin() as conn:
        await conn.execute(text("alter table consents disable trigger trg_consents_immutable"))
        await conn.execute(text("delete from consents where family_id = :f"), {"f": zalo_world.family.id})
        await conn.execute(text("alter table consents enable always trigger trg_consents_immutable"))


async def finished_drill(
    world: Any, *, is_demo: bool = True, answers: str = "right"
) -> tuple[uuid.UUID, dict[str, Any]]:
    """Một bài `offered` của người cao tuổi trong gia đình mẫu, đã nhận kết quả `completed`; ⇒ (id, payload job tin)."""
    async with get_sessionmaker().begin() as session:
        elder = Member(family_id=world.family.id, role="protected", alias="Bà")
        session.add(elder)
        await session.flush()
        elder_id = elder.id
        session.add(
            Consent(
                family_id=world.family.id,
                member_id=elder_id,
                purpose="drills",
                granted=True,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    drill_id = await add_drill(world.family.id, elder_id, status="offered", started_at=None, is_demo=is_demo)
    script = dr.get_script(SCRIPT_ID) or {}
    steps = script["steps"]
    given = [
        {"step": i, "choice_id": next(c["id"] for c in s["choices"] if c["correct"] == (answers == "right"))}
        for i, s in enumerate(steps)
    ]
    async with get_sessionmaker().begin() as session:
        await DrillService.record_result(
            session, family_id=world.family.id, member_id=elder_id, drill_id=drill_id, status="completed", answers=given
        )
    async with get_sessionmaker()() as session:
        job = await session.scalar(select(Job).where(Job.idempotency_key == f"{drill_id}:msg:debrief"))
    assert job is not None
    return drill_id, job.payload


async def test_the_debrief_reaches_guardian_rank_1_once_with_disclosure_and_label(world: Any) -> None:
    guardian = await world.add_guardian(1)
    other = await world.add_guardian(2)
    drill_id, payload = await finished_drill(world)

    assert await send_to_guardian(world.deps, payload) == "sent"
    assert await send_to_guardian(world.deps, payload, attempt=2) == "sent"  # job chạy lại: không gửi lần hai

    (sent,) = world.client.sent
    assert sent.chat_id == world.zalo_ids[1][1] and sent.chat_id != world.zalo_ids[2][1]
    assert sent.text.startswith("Đây là trợ lý AI HỏiCon. [DIỄN TẬP]")  # luật 6 + luật 8
    assert "Bà" in sent.text
    for flag in dr.red_flags(dr.get_script(SCRIPT_ID) or {}):
        assert flag in sent.text
    (row,) = await world.rows()
    assert (row.status, row.template_id, row.member_id, row.family_id) == (
        "sent",
        "debrief",
        guardian.id,
        world.family.id,
    )
    assert row.incident_id is None  # tin diễn tập không gắn sự cố nào
    assert row.job_key == f"{drill_id}:msg:debrief"
    assert other.id != row.member_id


async def test_a_failed_drill_debrief_is_sent_the_same_way(world: Any) -> None:
    await world.add_guardian(1)
    _, payload = await finished_drill(world, answers="wrong")
    assert await send_to_guardian(world.deps, payload) == "sent"
    (sent,) = world.client.sent
    assert sent.text.startswith("Đây là trợ lý AI HỏiCon. [DIỄN TẬP]")


async def test_no_guardian_means_the_message_is_marked_for_the_fallback_not_lost(world: Any) -> None:
    _, payload = await finished_drill(world)
    assert await send_to_guardian(world.deps, payload) == "fallback_required"
    assert world.client.sent == []


async def test_a_real_drill_is_never_delivered_to_a_demo_family(world: Any) -> None:
    """Luật 8: không lẫn demo với thật. Gia đình mẫu là demo; bài `is_demo=false` bị chặn trước khi gọi Zalo."""
    await world.add_guardian(1)
    _, payload = await finished_drill(world, is_demo=False)
    assert payload["is_demo"] is False
    assert await send_to_guardian(world.deps, payload) == "failed"
    assert world.client.sent == []
    (row,) = await world.rows()
    assert row.error == "real_to_demo_family"


async def test_a_debrief_without_the_drill_label_is_refused_at_the_gate(world: Any) -> None:
    """Cổng `deliver` cuối cùng: tin của bài diễn tập mà thiếu nhãn [DIỄN TẬP] không bao giờ ra khỏi máy chủ."""
    await world.add_guardian(1)
    _, payload = await finished_drill(world)
    unlabeled = {**payload, "text": payload["text"].replace("[DIỄN TẬP]", "")}
    assert await send_to_guardian(world.deps, unlabeled) == "failed"
    assert world.client.sent == []
