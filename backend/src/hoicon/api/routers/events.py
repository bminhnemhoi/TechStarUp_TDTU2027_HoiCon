"""`POST /v1/events` (spec 021, FR-004): app Lính gác gửi lô sự kiện rủi ro (1–50).

Một lô = MỘT giao dịch: lưu sự kiện (`ON CONFLICT (id) DO NOTHING` ⇒ gửi lại cả lô vô hại), rồi với mỗi sự kiện MỚI
gọi `IncidentService.correlate_event` (mở/liên kết sự cố). Lỗi giữa chừng ⇒ rollback, app gửi lại được, không mất
sự kiện.
Thiết bị/gia đình/thành viên lấy từ token, không từ thân yêu cầu. Số điện thoại: chỉ `HMAC(pepper, h1)` + 3 số cuối
(ADR-006); h1 không vào DB, không vào log. Khớp `docs/schemas/events_batch.v1.json` / `events_result.v1.json`.
"""

import logging
import time
from collections import deque
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg.errors import LockNotAvailable
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.agents.runtime import prepare_event, safe_alias
from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.models import Incident, Member, RiskEventRecord
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import RiskEventIn
from hoicon.domain.pii import hmac_h1
from hoicon.jobs.queue import enqueue
from hoicon.services import AlertService, IncidentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["events"])

MAX_BATCH = 50
# Hạn mức theo thiết bị (đếm trong bộ nhớ ⇒ chỉ đúng với một tiến trình, ADR-002). App thật gửi lô thưa (theo sự kiện,
# có gom); 30 lô/phút là rất rộng nhưng chặn được một thiết bị (hoặc client lỗi) xả liên tục làm nghẽn pool kết nối.
MAX_BATCHES_PER_WINDOW = 30
WINDOW_S = 60
MAX_TRACKED_DEVICES = 4096
# Chờ khóa tư vấn của thiết bị quá lâu ⇒ trả 503 thay vì giữ kết nối trong pool (mặc định chờ vô hạn).
LOCK_TIMEOUT_MS = 3000
BUSY = "Hệ thống đang bận, vui lòng thử lại sau ít giây."

_batches: dict[UUID, deque[float]] = {}


def reset_limits() -> None:
    _batches.clear()


def _retry_after(device_id: UUID, now: float) -> int | None:
    """Ghi nhận một lô; ⇒ số giây phải đợi nếu thiết bị đã quá hạn mức trong cửa sổ, None nếu được nhận."""
    if device_id not in _batches and len(_batches) >= MAX_TRACKED_DEVICES:  # bộ nhớ có trần
        for key in [k for k, w in _batches.items() if not w or now - w[-1] >= WINDOW_S]:
            del _batches[key]
    if device_id not in _batches and len(_batches) >= MAX_TRACKED_DEVICES:  # vẫn đầy: bỏ nguồn cũ nhất (trần cứng)
        del _batches[next(iter(_batches))]
    window = _batches.setdefault(device_id, deque())
    while window and now - window[0] >= WINDOW_S:
        window.popleft()
    if len(window) >= MAX_BATCHES_PER_WINDOW:
        return max(1, int(WINDOW_S - (now - window[0])))
    window.append(now)
    return None


class EventsBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[RiskEventIn] = Field(min_length=1, max_length=MAX_BATCH)


class EventsResult(BaseModel):
    accepted: int
    duplicates: int
    incident_id: UUID | None
    incident_opened: bool


def _row(event: RiskEventIn, claims: DeviceClaims) -> dict[str, Any]:
    """Dòng `risk_events`. `payload` = sự kiện đã BỎ `caller.h1`; cột `caller_*` chỉ có HMAC + 3 số cuối."""
    payload = event.model_dump(mode="json", exclude_none=True)
    row: dict[str, Any] = {
        "id": event.id,
        "family_id": claims.family_id,
        "device_id": claims.device_id,
        "type": event.type,
        "rule_id": event.rule_id,
        "rule_floor": event.rule_floor.value,
        "occurred_at": event.occurred_at,
        "is_drill": event.is_drill,
        "drill_id": event.drill_id,
        "app_category": event.app.category if event.app else None,
        "app_package": event.app.package if event.app else None,
        "call_duration_s": event.call.duration_s if event.call else None,
        "timing_detect_ms": event.timing.detect_ms if event.timing else None,
        "timing_pause_ms": event.timing.pause_ms if event.timing else None,
        "caller_hmac": None,
        "caller_kid": None,
        "caller_last3": None,
        "caller_in_contacts": None,
    }
    if event.caller is not None:
        row["caller_kid"], row["caller_hmac"] = hmac_h1(event.caller.h1)
        row["caller_last3"] = event.caller.last3
        row["caller_in_contacts"] = event.caller.in_contacts
        payload["caller"].pop("h1")
    row["payload"] = payload
    return row


async def _start_graph(session: AsyncSession, incident: Incident, event: RiskEventIn) -> None:
    """Spec 024 FR-006: sự cố đạt mức cảnh báo (cùng ngưỡng với cảnh báo nhanh) ⇒ xếp job chạy đồ thị tác tử, cùng
    giao dịch với lô. Khóa theo sự cố ⇒ một sự cố một lượt dù nhiều sự kiện liên kết vào. Payload đã bỏ h1 + tên gói
    (ADR-006): bảng `jobs` giữ dòng đã chạy xong."""
    threat, event_data = await prepare_event(session, event)
    member = await session.get(Member, incident.member_id)
    payload = {
        "event": event_data,
        "threat": threat,
        "incident_id": str(incident.id),
        "family_id": str(incident.family_id),
        "elder_alias": safe_alias(member.alias if member else None),
        "is_demo": bool(incident.is_demo),
    }
    await enqueue(session, "start_graph", payload, key=f"{incident.id}:graph:start")


@router.post("/events", response_model=EventsResult)
async def post_events(batch: EventsBatch, claims: Annotated[DeviceClaims, Depends(get_current_device)]) -> EventsResult:
    wait = _retry_after(claims.device_id, time.monotonic())
    if wait is not None:
        logger.info("events: thiết bị vượt hạn mức lô")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=BUSY, headers={"Retry-After": str(wait)})
    try:
        rows = sorted((_row(event, claims) for event in batch.events), key=lambda row: row["id"])  # thứ tự khóa ổn định
    except RuntimeError as exc:  # thiếu pepper: lỗi cấu hình của ta ⇒ 503, không nêu chi tiết, không lưu gì
        logger.error("events: không băm được số gọi đến (%s)", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    try:
        async with get_sessionmaker().begin() as session:
            await session.execute(text(f"SET LOCAL lock_timeout = {int(LOCK_TIMEOUT_MS)}"))
            stored = await session.scalars(
                insert(RiskEventRecord)
                .values(rows)
                .on_conflict_do_nothing(index_elements=["id"])
                .returning(RiskEventRecord.id)
            )
            fresh = set(stored.all())
            accepted = incident_id = None
            opened = False
            seen: set[UUID] = set()
            # Theo thứ tự xảy ra (ổn định trong lô): sự kiện cũ hơn mở sự cố trước, sự kiện sau liên kết vào.
            for event in sorted(batch.events, key=lambda e: e.occurred_at):
                if event.id not in fresh or event.id in seen:
                    continue
                seen.add(event.id)
                result = await IncidentService.correlate_event(
                    session, event, device_id=claims.device_id, family_id=claims.family_id, member_id=claims.member_id
                )
                if result is not None:
                    incident_id, opened = result.incident.id, opened or result.opened
                    if result.incident.level in ("high", "critical"):
                        await AlertService.trigger_guardian_fast_alert(session, incident=result.incident, event=event)
                        await _start_graph(session, result.incident, event)
            accepted = len(fresh)
    except OperationalError as exc:
        if not isinstance(exc.orig, LockNotAvailable):
            raise
        logger.warning("events: chờ khóa thiết bị quá hạn")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=BUSY, headers={"Retry-After": "2"}) from None
    logger.info("events: accepted=%d duplicates=%d incident_opened=%s", accepted, len(batch.events) - accepted, opened)
    return EventsResult(
        accepted=accepted, duplicates=len(batch.events) - accepted, incident_id=incident_id, incident_opened=opened
    )
