"""API thiết bị của diễn tập (spec 028 FR-005): `GET /v1/drills/offer` và `POST /v1/drills/{id}/result`.

Chỉ JWT thiết bị. Gia đình và người cao tuổi lấy từ token, không từ thân yêu cầu. Máy chỉ gửi MÃ lựa chọn (không văn bản
tự do, không trường `note`, không điểm): thân yêu cầu `extra="forbid"`. Máy chủ chấm lại, nên chỉ nó quyết `passed`/
`failed`. Khớp `docs/schemas/drill_offer.v1.json` / `drill_result.v1.json`. Không gọi LLM.
"""

import logging
import time
from collections import deque
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.session import get_sessionmaker
from hoicon.domain import drill as dr
from hoicon.services.drill_service import (
    DrillNotFound,
    DrillService,
    InvalidDrillTransition,
    ResultConflict,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/drills", tags=["drills"])

# Hạn mức hỏi bài theo thiết bị (đếm trong bộ nhớ ⇒ đúng với một tiến trình, ADR-002).
# Nhịp heartbeat 15 phút = 4 lần/giờ.
OFFERS_PER_HOUR = 30
WINDOW_S = 3600
MAX_TRACKED_DEVICES = 4096
BUSY = "Thiết bị hỏi quá nhiều lần, vui lòng thử lại sau."

_offers: dict[UUID, deque[float]] = {}


def reset_limits() -> None:
    _offers.clear()


def _retry_after(device_id: UUID, now: float) -> int | None:
    if device_id not in _offers and len(_offers) >= MAX_TRACKED_DEVICES:
        for key in [k for k, w in _offers.items() if not w or now - w[-1] >= WINDOW_S]:
            del _offers[key]
    if device_id not in _offers and len(_offers) >= MAX_TRACKED_DEVICES:
        del _offers[next(iter(_offers))]
    window = _offers.setdefault(device_id, deque())
    while window and now - window[0] >= WINDOW_S:
        window.popleft()
    if len(window) >= OFFERS_PER_HOUR:
        return max(1, int(WINDOW_S - (now - window[0])))
    window.append(now)
    return None


class DrillOut(BaseModel):
    drill_id: UUID
    window_end: datetime
    is_drill: Literal[True] = True
    script: dict[str, Any]


class DrillOffer(BaseModel):
    drill: DrillOut | None


class AnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: int = Field(ge=0)
    choice_id: str = Field(pattern=r"^[a-z]$")


class DrillResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drill_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    status: Literal["declined", "aborted", "completed"]
    answers: list[AnswerIn] = Field(max_length=5)
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None


class DrillResultAck(BaseModel):
    drill_id: UUID
    status: str  # passed | failed (do máy chủ chấm) | aborted | declined
    score: int | None


@router.get("/offer", response_model=DrillOffer)
async def get_offer(claims: Annotated[DeviceClaims, Depends(get_current_device)]) -> DrillOffer:
    wait = _retry_after(claims.device_id, time.monotonic())
    if wait is not None:
        logger.info("drills: thiết bị vượt hạn mức hỏi bài")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=BUSY, headers={"Retry-After": str(wait)})
    async with get_sessionmaker().begin() as session:
        drill = await DrillService.offer(session, family_id=claims.family_id, member_id=claims.member_id)
        script = dr.get_script(drill.script_id) if drill else None
        if drill is None or script is None:
            return DrillOffer(drill=None)
        return DrillOffer(drill=DrillOut(drill_id=drill.id, window_end=drill.window_end, script=script))


@router.post("/{drill_id}/result", response_model=DrillResultAck)
async def post_result(
    drill_id: UUID, body: DrillResultIn, claims: Annotated[DeviceClaims, Depends(get_current_device)]
) -> DrillResultAck:
    if body.drill_id != str(drill_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="drill_id không khớp đường dẫn")
    try:
        async with get_sessionmaker().begin() as session:
            outcome = await _record(session, claims, drill_id, body)
    except DrillNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài luyện tập") from None
    except dr.InvalidAnswers:  # không nêu giá trị máy gửi
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Câu trả lời không khớp bài luyện tập"
        ) from None
    except (ResultConflict, InvalidDrillTransition):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bài luyện tập không nhận kết quả này") from None
    drill = outcome.drill
    return DrillResultAck(drill_id=drill.id, status=drill.status, score=drill.score)


async def _record(session: AsyncSession, claims: DeviceClaims, drill_id: UUID, body: DrillResultIn) -> Any:
    return await DrillService.record_result(
        session,
        family_id=claims.family_id,
        member_id=claims.member_id,
        drill_id=drill_id,
        status=body.status,
        answers=[a.model_dump() for a in body.answers],
        started_at=body.started_at,
        completed_at=body.completed_at,
    )
