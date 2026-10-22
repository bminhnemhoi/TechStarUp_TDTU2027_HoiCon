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

from hoicon.db.models import Consent, Member

# Spec 011 D9: mục đích chi phối việc XEM LẠI sự cố trên web của người giám hộ. Nếu Minh tách mục đích
# riêng (★ MASTER-PLAN §8): chỉ đổi hằng số này và thêm trường vào `ConsentState`.
WEB_READ_PURPOSE = "guardian_alerts"
TTL_S = 60.0
MAX_ENTRIES = 4096


@dataclass(frozen=True)
class ConsentState:
    core_protection: bool
    guardian_alerts: bool
    llm_processing: bool = False
    pilot_research: bool = False


_cache: dict[UUID, tuple[float, ConsentState]] = {}
_generation: dict[
    UUID, int
] = {}  # tăng mỗi lần `invalidate`: truy vấn bắt đầu trước đó không được ghi đệm (chống race)


def reset_cache() -> None:
    _cache.clear()
    _generation.clear()


def invalidate(member_id: UUID) -> None:
    _generation[member_id] = _generation.get(member_id, 0) + 1
    _cache.pop(member_id, None)


async def state_for(session: AsyncSession, member_id: UUID, *, now: float | None = None) -> ConsentState:
    """Trạng thái đồng ý hiện hành của một người (đệm 60 giây)."""
    moment = time.monotonic() if now is None else now
    hit = _cache.get(member_id)
    if hit is not None and moment - hit[0] < TTL_S:
        return hit[1]
    generation = _generation.get(member_id, 0)
    rows = await session.execute(
        select(Consent.purpose, Consent.granted)
        .where(
            Consent.member_id == member_id,
            Consent.purpose.in_(("core_protection", "guardian_alerts", "llm_processing", "pilot_research")),
        )
        .distinct(Consent.purpose)
        .order_by(Consent.purpose, Consent.recorded_at.desc(), Consent.id.desc())
    )
    latest = {purpose: granted for purpose, granted in rows}
    state = ConsentState(
        core_protection=latest.get("core_protection") is True,
        guardian_alerts=latest.get("guardian_alerts") is True,
        llm_processing=latest.get("llm_processing") is True,
        pilot_research=latest.get("pilot_research") is True,
    )
    if _generation.get(member_id, 0) != generation:  # đồng ý vừa đổi trong lúc truy vấn: trả kết quả, không ghi đệm
        return state
    if member_id not in _cache and len(_cache) >= MAX_ENTRIES:  # bộ nhớ có trần: bỏ mục cũ nhất
        del _cache[next(iter(_cache))]
    _cache[member_id] = (moment, state)
    return state


async def web_readable(session: AsyncSession, member_id: UUID, *, is_demo: bool) -> bool:
    """Người giám hộ có được xem dữ liệu của người cao tuổi này trên web? Đã rút (hoặc chưa có) `WEB_READ_PURPOSE`
    ⇒ không.
    Dữ liệu demo/mô phỏng (hư cấu) được miễn."""
    return is_demo or getattr(await state_for(session, member_id), WEB_READ_PURPOSE, False)


async def web_readable_members(session: AsyncSession, family_id: UUID) -> list[UUID]:
    """Thành viên của gia đình còn đồng ý `WEB_READ_PURPOSE` (để lọc danh sách sự cố; mặc định: rút ⇒ rỗng)."""
    members = (await session.scalars(select(Member.id).where(Member.family_id == family_id))).all()
    return [m for m in members if getattr(await state_for(session, m), WEB_READ_PURPOSE, False)]
