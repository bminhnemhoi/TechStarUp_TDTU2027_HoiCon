"""Spec 032 FR-006: hạn mức. Bản tin tuần dừng ở `warn_pct`; tin mất bảo vệ đi tới `hold_pct`; cả hai `urgent=False`;
tin sự cố không bị ảnh hưởng. Đếm bằng `messages_out` giả lập (hạn mức test = 20: 80% = 16 tin, 95% = 19 tin)."""

from typing import Any

import pytest
from sqlalchemy import select

from hoicon.agents import texts
from hoicon.channels.guardian import quota_month, send_to_guardian
from hoicon.db.ids import new_id
from hoicon.db.models import MessageOut
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration


async def seed_sent(world: Any, n: int) -> None:
    async with get_sessionmaker().begin() as session:
        for _ in range(n):
            session.add(
                MessageOut(
                    family_id=None,
                    channel="zalo",
                    bot_id=world.bot_id,
                    template_id="seed",
                    status="sent",
                    quota_month=quota_month(),
                    job_key=f"seed:{new_id()}",
                )
            )


def coach_payload(world: Any, kind: str) -> dict[str, Any]:
    """Payload y như `coach_service` xếp (gia đình của fixture là demo nên `is_demo` True; hạn mức không phụ thuộc)."""
    key = f"{kind}:{new_id()}"
    base: dict[str, Any] = {
        "family_id": str(world.family.id),
        "guardian_rank": 1,
        "member_id": str(world.guardians[1].id),
        "is_demo": True,
        "is_drill": False,
        "urgent": False,
        "job_key": key,
    }
    if kind == "weekly":
        return {
            **base,
            "template": "weekly_digest",
            "text": texts.weekly_digest("Mẹ", 0, 0, 1.0, 0, None),
            "quota_class": "digest",
        }
    return {
        **base,
        "template": "protection_silent",
        "text": texts.guardian_protection_silent("Mẹ", "07:30 ngày 20 tháng 10"),
    }


async def status_of(job_key: str) -> str:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(MessageOut.status).where(MessageOut.job_key == job_key))


async def send(world: Any, payload: dict[str, Any]) -> str:
    await send_to_guardian(world.deps, payload)
    return await status_of(payload["job_key"])


async def test_quota_79_percent_sends_both_kinds(zalo_world: Any) -> None:
    await zalo_world.add_guardian(1)
    await seed_sent(zalo_world, 15)  # 75% < 80%
    assert await send(zalo_world, coach_payload(zalo_world, "weekly")) == "sent"
    assert await send(zalo_world, coach_payload(zalo_world, "protection")) == "sent"


async def test_quota_81_percent_holds_the_digest_but_still_sends_the_protection_message(zalo_world: Any) -> None:
    await zalo_world.add_guardian(1)
    await seed_sent(zalo_world, 16)  # ≥ 80%
    digest = coach_payload(zalo_world, "weekly")
    assert await send(zalo_world, digest) == "held_quota"
    assert await send(zalo_world, digest) == "held_quota"  # không thử lại trong tuần (trạng thái cuối)
    assert await send(zalo_world, coach_payload(zalo_world, "protection")) == "sent"


async def test_quota_96_percent_holds_both_kinds_but_never_an_incident_message(zalo_world: Any) -> None:
    await zalo_world.add_guardian(1)
    await seed_sent(zalo_world, 19)  # ≥ 95%
    assert await send(zalo_world, coach_payload(zalo_world, "weekly")) == "held_quota"
    assert await send(zalo_world, coach_payload(zalo_world, "protection")) == "held_quota"
    incident = {
        "template": "detail",
        "family_id": str(zalo_world.family.id),
        "guardian_rank": 1,
        "incident_id": zalo_world.new_incident(),
        "text": texts.guardian_fast_alert("Mẹ", None, "bank", False),
        "is_demo": True,
        "is_drill": False,
    }
    await send_to_guardian(zalo_world.deps, incident)  # tin sự cố khẩn: bỏ qua ngưỡng giữ
    key = f"{incident['incident_id']}:msg:detail"
    assert await status_of(key) == "sent"
