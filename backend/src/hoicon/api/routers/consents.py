"""`POST /v1/consents` (spec 020, FR-005): ghi THÊM vào sổ đồng ý; không có route sửa/xóa (và trigger Postgres chặn
cả khi có lỗi phần mềm). Rút đồng ý = gửi lại cùng `purpose` với `granted = false`. `family_id`/`member_id` lấy từ
token, không bao giờ từ thân yêu cầu; `recorded_at` do máy chủ đặt (`now()` của giao dịch ⇒ cả lô cùng một mốc)."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.models import Consent
from hoicon.db.session import get_sessionmaker

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
]
MAX_ITEMS = 32


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


@router.post("/consents", response_model=ConsentReceipt)
async def record_consents(
    batch: ConsentBatch, device: Annotated[DeviceClaims, Depends(get_current_device)]
) -> ConsentReceipt:
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
            recorded_at = await session.scalar(select(func.now()))  # cùng giao dịch ⇒ đúng mốc `server_default now()`
    except SQLAlchemyError as exc:
        logger.error("ghi sổ đồng ý lỗi (%s)", type(exc).__name__)  # không kèm thông điệp: có thể chứa tham số
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Chưa ghi được, vui lòng thử lại") from None
    return ConsentReceipt(count=len(batch.items), recorded_at=recorded_at.isoformat())
