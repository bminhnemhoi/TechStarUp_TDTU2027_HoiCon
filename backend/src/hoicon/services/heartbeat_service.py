"""Heartbeat của thiết bị (spec 029 FR-002/003): cập nhật `devices` và ghi tối đa MỘT dòng `device_heartbeats` mỗi khung
15 phút để đo độ phủ Gate M2. Không văn bản tự do, không định danh: chỉ phiên bản, cờ quyền và mốc giờ."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.db.models import Device, DeviceHeartbeat

SLOT_SECONDS = 15 * 60
# Quyền lõi để bảo vệ chạy được (plan D2): vai trò sàng lọc cuộc gọi + quyền xem mức dùng app. Tên theo
# `SensorPermission` của Android (chữ thường). Thiếu khóa trong `permission_state` = coi như chưa bật.
CORE_PERMISSIONS = ("call_screening_role", "usage_access")


def slot_of(moment: datetime) -> datetime:
    """Mốc 15 phút (UTC) chứa `moment`."""
    epoch = int(moment.timestamp())
    return datetime.fromtimestamp(epoch - epoch % SLOT_SECONDS, tz=UTC)


def is_protected(permission_state: dict[str, Any]) -> bool:
    return all(permission_state.get(name) is True for name in CORE_PERMISSIONS)


async def record(
    session: AsyncSession,
    device_id: UUID,
    *,
    app_version: str,
    rules_version: str,
    threat_list_version: str | None,
    permission_state: dict[str, bool],
    now: datetime,
) -> bool:
    """⇒ False nếu thiết bị đã bị thu hồi (không ghi gì). Gửi lặp trong cùng khung: `devices` vẫn được làm mới, bảng
    khung giữ dòng đầu (ON CONFLICT DO NOTHING)."""
    values: dict[str, Any] = {
        "app_version": app_version,
        "rules_version": rules_version,
        "permission_state": permission_state,
        "last_heartbeat_at": now,
    }
    if threat_list_version is not None:
        values["threat_list_version"] = threat_list_version
    updated = await session.execute(
        update(Device).where(Device.id == device_id, Device.revoked_at.is_(None)).values(**values)
    )
    if updated.rowcount == 0:
        return False
    await session.execute(
        insert(DeviceHeartbeat)
        .values(device_id=device_id, slot=slot_of(now), protected=is_protected(permission_state))
        .on_conflict_do_nothing(index_elements=["device_id", "slot"])
    )
    return True


# --- Độ phủ (một định nghĩa cho Gate M2 `ops pilot` và bản tin tuần spec 032, plan D3) -------------------------------
def ceil_slot(moment: datetime) -> int:
    return -(-int(moment.timestamp()) // SLOT_SECONDS)


def floor_slot(moment: datetime) -> int:
    return int(moment.timestamp()) // SLOT_SECONDS


def slot_at(slot_index: int) -> datetime:
    return datetime.fromtimestamp(slot_index * SLOT_SECONDS, tz=UTC)


async def device_slot_counts(
    session: AsyncSession, device: Device, since: datetime, now: datetime
) -> tuple[int, int, int]:
    """⇒ (khung kỳ vọng, khung có heartbeat, khung có heartbeat VÀ được bảo vệ) từ `max(created_at, since)` tới
    `min(revoked_at, now)`: thiết bị ghép giữa kỳ hoặc đã thu hồi có mẫu số riêng."""
    first = ceil_slot(max(device.created_at, since))
    last = floor_slot(min(device.revoked_at or now, now))  # khung kỳ vọng: [first, last)
    expected = max(0, last - first)
    if not expected:
        return 0, 0, 0
    seen, protected = (
        await session.execute(
            select(func.count(), func.count().filter(DeviceHeartbeat.protected)).where(
                DeviceHeartbeat.device_id == device.id,
                DeviceHeartbeat.slot >= slot_at(first),
                DeviceHeartbeat.slot < slot_at(last),
            )
        )
    ).one()
    return expected, seen, protected


async def family_coverage(session: AsyncSession, family_id: UUID, days: int, now: datetime) -> float | None:
    """Độ phủ gộp mọi thiết bị của gia đình trong `days` ngày (cùng cách gộp với `ops pilot`); None khi chưa có khung kỳ
    vọng nào ("chưa đủ dữ liệu")."""
    since = now - timedelta(days=days)
    devices = (
        await session.scalars(
            select(Device).where(
                Device.family_id == family_id, (Device.revoked_at.is_(None)) | (Device.revoked_at >= since)
            )
        )
    ).all()
    expected = seen = 0
    for device in devices:
        e, s, _ = await device_slot_counts(session, device, since, now)
        expected, seen = expected + e, seen + s
    return seen / expected if expected else None
