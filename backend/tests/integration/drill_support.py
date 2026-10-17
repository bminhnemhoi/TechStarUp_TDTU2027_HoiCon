"""Tạo bài diễn tập `in_progress` hợp lệ cho các test gửi sự kiện `is_drill=true` (spec 028 D2/FR-003): từ nay cờ
diễn tập chỉ được tin khi khớp một bài đang chạy của chính người cao tuổi đó, trong khung giờ."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from consent_support import call

from hoicon.db.ids import new_id
from hoicon.db.models import Drill
from hoicon.db.session import get_sessionmaker

EVENT_TIME = "2026-12-01T02:15:30.120Z"  # `occurred_at` mặc định của make_event trong test_api_events


def at(value: str = EVENT_TIME) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def me(token: str) -> dict[str, Any]:
    return (await call("GET", "/v1/devices/me", token=token)).json()["device"]


async def add_drill(
    family_id: UUID,
    member_id: UUID,
    *,
    around: datetime | None = None,
    before: timedelta = timedelta(minutes=10),
    after: timedelta = timedelta(minutes=50),
    **changes: Any,
) -> UUID:
    """Chèn thẳng một bài (mặc định `in_progress`, khung giờ ôm lấy `around` = EVENT_TIME); ⇒ id."""
    centre = around or at()
    values: dict[str, Any] = {
        "id": new_id(),
        "family_id": family_id,
        "member_id": member_id,
        "scheduled_by": "ops",
        "script_id": "drill_bank_card_locked",
        "window_start": centre - before,
        "window_end": centre + after,
        "status": "in_progress",
        "started_at": centre - before,
        "is_demo": True,
    }
    values.update(changes)
    async with get_sessionmaker().begin() as session:
        session.add(Drill(**values))
    return values["id"]


async def running_drill_for(token: str, **changes: Any) -> UUID:
    """Bài `in_progress` của chính thiết bị mang `token`, bao quanh EVENT_TIME."""
    device = await me(token)
    return await add_drill(UUID(device["family_id"]), UUID(device["member_id"]), **changes)
