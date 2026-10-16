"""Thực thi đồng ý ở máy chủ (spec 034 FR-005, D5). Android đã có cổng `mayShareWithFamily`, nhưng máy cũ, bị sửa hoặc
chưa kịp ghi sổ vẫn gửi được sau khi rút đồng ý: máy chủ là nơi quyết định cuối cùng.

Đọc dòng MỚI NHẤT của mỗi mục đích (`consents` chỉ ghi thêm, rút đồng ý = thêm dòng `granted = false`). Chưa có dòng
nào = chưa đồng ý (đóng mặc định). Đệm 60 giây theo `member_id` trong bộ nhớ tiến trình (ADR-002: một tiến trình) để
không thêm truy vấn mỗi lô; `POST /v1/consents` xóa mục đệm của chính người đó ngay khi ghi. Đồng ý đổi từ nơi khác
(kênh khác) có thể trễ tối đa 60 giây."""

import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.db.models import Consent

TTL_S = 60.0
MAX_ENTRIES = 4096


@dataclass(frozen=True)
class ConsentState:
    core_protection: bool
    guardian_alerts: bool


_cache: dict[UUID, tuple[float, ConsentState]] = {}


def reset_cache() -> None:
    _cache.clear()


def invalidate(member_id: UUID) -> None:
    _cache.pop(member_id, None)


async def state_for(session: AsyncSession, member_id: UUID, *, now: float | None = None) -> ConsentState:
    """Trạng thái đồng ý hiện hành của một người (đệm 60 giây)."""
    moment = time.monotonic() if now is None else now
    hit = _cache.get(member_id)
    if hit is not None and moment - hit[0] < TTL_S:
        return hit[1]
    rows = await session.execute(
        select(Consent.purpose, Consent.granted)
        .where(Consent.member_id == member_id, Consent.purpose.in_(("core_protection", "guardian_alerts")))
        .distinct(Consent.purpose)
        .order_by(Consent.purpose, Consent.recorded_at.desc(), Consent.id.desc())
    )
    latest = {purpose: granted for purpose, granted in rows}
    state = ConsentState(
        core_protection=latest.get("core_protection") is True, guardian_alerts=latest.get("guardian_alerts") is True
    )
    if member_id not in _cache and len(_cache) >= MAX_ENTRIES:  # bộ nhớ có trần: bỏ mục cũ nhất
        del _cache[next(iter(_cache))]
    _cache[member_id] = (moment, state)
    return state
