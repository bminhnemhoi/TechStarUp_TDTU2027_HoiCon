"""US4 (FR-007/008, SC-007): hạn mức tin/tháng theo bot — cảnh báo 80%, giữ tin không khẩn ở 95%, tin sự cố luôn đi."""

import logging
from typing import Any

import pytest
from sqlalchemy import delete

from hoicon.agents import texts
from hoicon.channels.guardian import _threshold, quota_month, send_to_guardian
from hoicon.channels.updates import handle_update
from hoicon.config import Settings
from hoicon.db.ids import new_id
from hoicon.db.models import MessageOut
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration
# Hạn mức test = 20 (conftest): cảnh báo ở 16 tin, giữ tin không khẩn từ tin thứ 20 (đã dùng ≥ 19).


async def seed_sent(world: Any, n: int, *, month: str | None = None, bot_id: str | None = None) -> None:
    async with get_sessionmaker().begin() as session:
        for _ in range(n):
            session.add(
                MessageOut(
                    family_id=None,
                    channel="zalo",
                    bot_id=bot_id or world.bot_id,
                    template_id="seed",
                    status="sent",
                    quota_month=month or quota_month(),
                    job_key=f"seed:{new_id()}",
                )
            )


async def stranger_reply(world: Any, user: str) -> str | None:
    """Tin KHÔNG khẩn: trả lời người lạ nhắn `/start` (không gắn sự cố)."""
    return await handle_update(world.deps, None, world.update_payload(user, kind="start_no_code"))


async def alert(world: Any, template: str = "fast_alert") -> str | None:
    if 1 not in world.guardians:
        await world.add_guardian(1)
    payload = {
        "incident_id": world.new_incident(),
        "family_id": str(world.family.id),
        "template": template,
        "text": texts.guardian_fast_alert("Mẹ", "002", "bank", False),
        "guardian_rank": 1,
        "is_drill": False,
        "is_demo": True,
    }
    return await send_to_guardian(world.deps, payload)


def test_default_thresholds_match_the_basic_plan() -> None:
    settings = Settings(_env_file=None)
    assert settings.zalo_monthly_quota == 3000  # gói Basic (bot.zapps.me, tra 15/10/2026)
    assert (_threshold(3000, settings.zalo_quota_warn_pct), _threshold(3000, settings.zalo_quota_hold_pct)) == (
        2400,
        2850,
    )


async def test_at_95_percent_non_urgent_is_held_but_incident_alert_still_goes(zalo_world: Any) -> None:
    world = zalo_world
    await seed_sent(world, 19)  # 95% của 20
    assert await stranger_reply(world, "u-1") == "held_quota"
    assert world.client.sent == []  # không gọi Zalo
    held = [r for r in await world.rows() if r.status == "held_quota"]
    assert len(held) == 1 and held[0].error == "over_hold_threshold"
    assert await alert(world) == "sent"  # SC-007: tin sự cố vẫn đi
    assert len(world.client.sent) == 1


async def test_below_95_percent_non_urgent_is_sent(zalo_world: Any) -> None:
    world = zalo_world
    await seed_sent(world, 18)
    assert await stranger_reply(world, "u-1") == "sent"


async def test_warning_is_logged_once_when_crossing_80_percent(
    zalo_world: Any, caplog: pytest.LogCaptureFixture
) -> None:
    world = zalo_world
    await seed_sent(world, 14)
    with caplog.at_level(logging.WARNING, logger="hoicon.channels.guardian"):
        await stranger_reply(world, "u-1")  # tin thứ 15: chưa tới 16
        assert "≥ 80%" not in caplog.text
        await stranger_reply(world, "u-2")  # tin thứ 16: chạm ngưỡng
        assert caplog.text.count("≥ 80%") == 1 and "16/20" in caplog.text
        await stranger_reply(world, "u-3")  # tin thứ 17: không cảnh báo lại
        assert caplog.text.count("≥ 80%") == 1


async def test_exhausted_quota_needs_fallback_for_incident_and_holds_the_rest(zalo_world: Any) -> None:
    world = zalo_world
    await seed_sent(world, 20)
    assert await alert(world) == "fallback_required"  # FR-008: hết hẳn hạn mức
    rows = {r.template_id: r for r in await world.rows() if r.template_id == "fast_alert"}
    assert rows["fast_alert"].error == "quota_exhausted"
    assert await stranger_reply(world, "u-1") == "held_quota"
    assert world.client.sent == []


async def test_new_month_resets_the_counter(zalo_world: Any) -> None:
    world = zalo_world
    await seed_sent(world, 20, month="2000-01")  # tháng cũ không tính
    assert await alert(world) == "sent"
    assert await stranger_reply(world, "u-1") == "sent"


async def test_other_bots_and_unsent_rows_do_not_count(zalo_world: Any) -> None:
    world = zalo_world
    await seed_sent(world, 30, bot_id=f"{world.bot_id}-other")
    async with get_sessionmaker().begin() as session:
        for status in ("held_quota", "fallback_required", "failed", "queued"):
            session.add(
                MessageOut(
                    channel="zalo",
                    bot_id=world.bot_id,
                    template_id="seed",
                    status=status,
                    quota_month=quota_month(),
                    job_key=f"seed:{new_id()}",
                )
            )
    try:
        assert await stranger_reply(world, "u-1") == "sent"  # 0 tin đã gửi của bot này trong tháng
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(delete(MessageOut).where(MessageOut.bot_id == f"{world.bot_id}-other"))


async def test_month_is_vietnam_time() -> None:
    from datetime import UTC, datetime

    assert quota_month(datetime(2026, 10, 31, 17, 30, tzinfo=UTC)) == "2026-11"  # 00:30 ngày 1/11 giờ Việt Nam
    assert quota_month(datetime(2026, 10, 31, 16, 59, tzinfo=UTC)) == "2026-10"
