"""Spec 037 FR-002 / SC-002: đồng ý `guardian_alerts` là điều kiện LÚC GỬI. Tin đã xếp trước khi người cao tuổi
rút đồng ý không được gửi; tin demo/mô phỏng (hư cấu) và tin không gắn người cao tuổi nào được miễn."""

from typing import Any

import pytest
from consent_support import SHA, purge_family
from sqlalchemy import text
from test_notify_guardian import payload

from hoicon.channels.guardian import send_to_guardian
from hoicon.db.models import Consent
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    consent_gate.reset_cache()


async def real_world(world: Any) -> tuple[str, Any]:
    """Gia đình THẬT (không demo) có một sự cố; ⇒ (incident_id, member_id của người được bảo vệ)."""
    incident = world.new_incident()
    async with get_sessionmaker().begin() as session:
        await session.execute(text("update families set is_demo = false where id = :f"), {"f": world.family.id})
    return incident, world.protected_id


async def record(world: Any, member: Any, granted: bool) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world.family.id,
                member_id=member,
                purpose="guardian_alerts",
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()


async def test_no_consent_at_send_time_means_no_message(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    incident, _ = await real_world(world)
    try:
        assert await send_to_guardian(world.deps, payload(world, incident, is_demo=False)) == "skipped_consent"
        assert world.client.sent == [] and await world.rows() == []
    finally:
        await purge_family(world.family.id)


async def test_consent_granted_then_withdrawn_after_the_job_was_queued_stops_the_message(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    incident, member = await real_world(world)
    try:
        await record(world, member, True)
        job = payload(world, incident, is_demo=False)  # job đã xếp khi còn đồng ý
        await record(world, member, False)  # người cao tuổi rút trước khi worker gửi
        assert await send_to_guardian(world.deps, job) == "skipped_consent"
        assert world.client.sent == []
    finally:
        await purge_family(world.family.id)


async def test_with_consent_the_message_is_sent_as_before(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    incident, member = await real_world(world)
    try:
        await record(world, member, True)
        assert await send_to_guardian(world.deps, payload(world, incident, is_demo=False)) == "sent"
        assert len(world.client.sent) == 1
    finally:
        await purge_family(world.family.id)


async def test_a_drill_debrief_carries_the_protected_member_and_obeys_the_same_rule(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    _, member = await real_world(world)
    debrief = {
        "template": "debrief",
        "family_id": str(world.family.id),
        "guardian_rank": 1,
        "drill_id": str(world.protected_id),  # chỉ cần một id duy nhất cho khóa job
        "protected_member_id": str(member),
        "text": "Đây là trợ lý AI HỏiCon. [DIỄN TẬP] Tổng kết.",
        "is_demo": False,
        "is_drill": True,
    }
    try:
        assert await send_to_guardian(world.deps, debrief) == "skipped_consent"
        await record(world, member, True)
        assert await send_to_guardian(world.deps, debrief) == "sent"
    finally:
        await purge_family(world.family.id)


async def test_demo_messages_are_exempt(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    demo_incident = world.new_incident()
    assert await send_to_guardian(world.deps, payload(world, demo_incident)) == "sent"  # demo: hư cấu
    coach = {
        "template": "weekly",
        "job_key": f"weekly:{world.guardians[1].id}:2026-W43",
        "family_id": str(world.family.id),
        "guardian_rank": 1,
        "member_id": str(world.guardians[1].id),
        "text": "Đây là trợ lý AI HỏiCon. Bản tin tuần.",
        "is_demo": True,
        "is_drill": False,
    }
    assert await send_to_guardian(world.deps, coach) == "sent"  # tin demo: hư cấu


async def test_a_real_message_that_names_no_protected_member_fails_closed(zalo_world: Any) -> None:
    """Đóng mặc định (reviewer 037 #3): tin thật không xác định được người cao tuổi thì không gửi."""
    world = zalo_world
    await world.add_guardian(1)
    await real_world(world)
    try:
        orphan = {
            "template": "weekly_digest",
            "job_key": f"weekly:{world.guardians[1].id}:2026-W43",
            "family_id": str(world.family.id),
            "guardian_rank": 1,
            "member_id": str(world.guardians[1].id),
            "text": "Đây là trợ lý AI HỏiCon. Bản tin tuần.",
            "is_demo": False,
            "is_drill": False,
        }
        assert await send_to_guardian(world.deps, orphan) == "skipped_consent"
        assert world.client.sent == []
        await record(world, world.protected_id, True)
        assert await send_to_guardian(world.deps, {**orphan, "protected_member_id": str(world.protected_id)}) == "sent"
    finally:
        await purge_family(world.family.id)
