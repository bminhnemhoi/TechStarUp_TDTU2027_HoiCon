"""`POST /v1/consents` (spec 020, FR-005): ghi THÊM vào sổ đồng ý; không có route sửa/xóa (và trigger Postgres chặn
cả khi có lỗi phần mềm). Rút đồng ý = gửi lại cùng `purpose` với `granted = false`. `family_id`/`member_id` lấy từ
token, không bao giờ từ thân yêu cầu; `recorded_at` do máy chủ đặt (`now()` của giao dịch ⇒ cả lô cùng một mốc)."""

import logging
import time
from collections import deque
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.config import get_settings
from hoicon.db.models import Consent
from hoicon.db.session import get_sessionmaker
from hoicon.ops.consent_texts import load_manifest
from hoicon.services import consent_gate, verification_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["consents"])

Purpose = Literal[
    "core_protection",
    "call_screening",
    "usage_monitoring",
    "overlay_pause",
    "guardian_alerts",
    "llm_processing",
    "voice_input",
    "drills",
    "pilot_research",
    "lookups",
]
MAX_ITEMS = 32
# Spec 037 FR-005: giới hạn tần suất theo thiết bị (cửa sổ trượt, trong bộ nhớ: ADR-002 một tiến trình).
# Đồng ý hiếm khi đổi quá vài lần mỗi phút; hạn mức chặn thiết bị lỗi/độc hại làm đầy sổ chỉ-ghi-thêm.
WINDOW_S = 60
MAX_PER_WINDOW = 20
MAX_TRACKED_DEVICES = 4096
_calls: dict[UUID, deque[float]] = {}


def reset_limits() -> None:
    _calls.clear()


def _retry_after(device_id: UUID, now: float) -> int | None:
    """Ghi nhận một lần gọi; ⇒ số giây phải đợi nếu thiết bị đã quá hạn mức, None nếu được nhận."""
    if device_id not in _calls and len(_calls) >= MAX_TRACKED_DEVICES:  # bộ nhớ có trần
        for key in [k for k, w in _calls.items() if not w or now - w[-1] >= WINDOW_S]:
            del _calls[key]
        if len(_calls) >= MAX_TRACKED_DEVICES:
            del _calls[next(iter(_calls))]
    window = _calls.setdefault(device_id, deque())
    while window and now - window[0] >= WINDOW_S:
        window.popleft()
    if len(window) >= MAX_PER_WINDOW:
        return max(1, int(WINDOW_S - (now - window[0])))
    window.append(now)
    return None


class ConsentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: Purpose
    granted: StrictBool  # không nhận "yes"/1: hợp đồng là boolean thật
    consent_version: str = Field(min_length=1, max_length=16)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    # Schema cho phép app/zalo/web (dùng chung với các kênh khác); thiết bị chỉ được khai kênh của chính nó.
    channel: Literal["app"]


class ConsentBatch(BaseModel):
    """Khớp `docs/schemas/consent_record.v1.json`, chặt hơn ở hai điểm (xem mô tả schema): kênh `app` và purpose không
    trùng trong một lô (UUIDv7 cùng mili-giây không có thứ tự ⇒ "dòng mới nhất" của purpose trùng sẽ mơ hồ)."""

    model_config = ConfigDict(extra="forbid")

    items: list[ConsentItem] = Field(min_length=1, max_length=MAX_ITEMS)

    @model_validator(mode="after")
    def _distinct_purposes(self) -> "ConsentBatch":
        purposes = [i.purpose for i in self.items]
        if len(set(purposes)) != len(purposes):
            raise ValueError("mỗi purpose chỉ xuất hiện một lần trong một lô")
        return self


class ConsentReceipt(BaseModel):
    status: Literal["recorded"] = "recorded"
    count: int
    recorded_at: str


UNKNOWN_TEXT = "Văn bản đồng ý này không còn hiệu lực. Vui lòng cập nhật ứng dụng rồi thử lại."


def _accepted_texts() -> set[tuple[str, str, str]]:
    """(mục đích, phiên bản, sha256) được nhận ở chế độ nghiêm: bản `approved` trong manifest hoặc đã `released`."""
    manifest = load_manifest()
    accepted = {
        (e["purpose"], e["version"], e["sha256"]) for e in manifest["purposes"] if e.get("status") == "approved"
    }
    return accepted | {(e["purpose"], e["version"], e["sha256"]) for e in manifest.get("released", [])}


@router.post("/consents", response_model=ConsentReceipt)
async def record_consents(
    batch: ConsentBatch, device: Annotated[DeviceClaims, Depends(get_current_device)]
) -> ConsentReceipt:
    wait = _retry_after(device.device_id, time.monotonic())
    if wait is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Bạn gửi quá nhanh. Vui lòng thử lại sau ít phút.",
            headers={"Retry-After": str(wait)},
        )
    # Spec 037 FR-001: CẤP đồng ý chỉ nhận chữ đã duyệt (không đọc được manifest ⇒ đóng). RÚT đồng ý luôn được nhận
    # (quyền rút không phụ thuộc manifest hay phiên bản app) nên chỉ kiểm các mục `granted=true`.
    grants = [i for i in batch.items if i.granted]
    if grants and get_settings().consent_strict_on:
        try:
            accepted = _accepted_texts()
        except (OSError, ValueError, KeyError) as exc:
            logger.error("manifest đồng ý không đọc được (%s): từ chối ghi", type(exc).__name__)
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chưa ghi được, vui lòng thử lại") from None
        if any((i.purpose, i.consent_version, i.text_sha256) not in accepted for i in grants):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=UNKNOWN_TEXT)  # không nêu sha mong đợi
    try:
        async with get_sessionmaker().begin() as session:
            session.add_all(
                Consent(
                    family_id=device.family_id,
                    member_id=device.member_id,
                    purpose=i.purpose,
                    granted=i.granted,
                    consent_version=i.consent_version,
                    text_sha256=i.text_sha256,
                    channel=i.channel,
                )
                for i in batch.items
            )
            await session.flush()  # INSERT ngay để lỗi DB hiện ở đây, trước khi đọc mốc thời gian
            if any(i.purpose == "lookups" and not i.granted for i in batch.items):
                scrubbed = await verification_service.scrub_member_lookups(session, device.member_id)
                logger.info("rút đồng ý lookups: làm sạch %d lượt tra cứu", scrubbed)  # chỉ số đếm
            recorded_at = await session.scalar(select(func.now()))  # cùng giao dịch ⇒ đúng mốc `server_default now()`
    except SQLAlchemyError as exc:
        logger.error("ghi sổ đồng ý lỗi (%s)", type(exc).__name__)  # không kèm thông điệp: có thể chứa tham số
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chưa ghi được, vui lòng thử lại") from None
    consent_gate.invalidate(device.member_id)  # spec 034: đồng ý mới có hiệu lực ngay, không chờ hết đệm 60 giây
    return ConsentReceipt(count=len(batch.items), recorded_at=recorded_at.isoformat())
