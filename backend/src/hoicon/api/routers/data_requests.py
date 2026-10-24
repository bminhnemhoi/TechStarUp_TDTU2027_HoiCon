"""Xóa dữ liệu từ app (spec 038 FR-004): `POST /v1/data-requests`.

Chỉ JWT thiết bị của người được bảo vệ (`role='protected'`); gia đình lấy từ token. Cố ý KHÔNG qua `consent_gate`: quyền
xóa không phụ thuộc đồng ý nào, kể cả người đã rút hết. Ghi `data_requests(requested_via='app')` và xếp `purge_family`
(034, lũy đẳng: đã có yêu cầu đang chờ thì trả lại chính nó, 200). Một tin Zalo cho người giám hộ hạng 1 CHỈ khi
`guardian_alerts` còn hiệu lực; tin xếp trước purge (purge hoãn `PURGE_DELAY_S`) và đồng ý được kiểm lại lúc gửi.
Hạn mức 3 lần/ngày/thiết bị (đếm trong bộ nhớ, ADR-002). Khớp `docs/schemas/data_request.v1.json`. Không gọi LLM.
"""

import logging
import time
from collections import deque
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict

from hoicon.agents import texts
from hoicon.agents.runtime import safe_alias
from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.models import DataRequest, Family, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate, purge_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/data-requests", tags=["data-requests"])

PER_DAY = 3
WINDOW_S = 86400
MAX_TRACKED_DEVICES = 4096
PURGE_DELAY_S = 24 * 3600  # khoảng chờ có thể hủy (spec 038 FR-006): tin báo đi ngay, purge sau 24 giờ
DEADLINE_HOURS = 72
BUSY = "Đã gửi yêu cầu nhiều lần hôm nay. Bác thử lại vào ngày mai nhé."
NO_STORE = {"Cache-Control": "no-store"}

_asked: dict[UUID, deque[float]] = {}


def reset_limits() -> None:
    _asked.clear()


def _retry_after(device_id: UUID, now: float) -> int | None:
    if device_id not in _asked and len(_asked) >= MAX_TRACKED_DEVICES:
        for key in [k for k, w in _asked.items() if not w or now - w[-1] >= WINDOW_S]:
            del _asked[key]
    if device_id not in _asked and len(_asked) >= MAX_TRACKED_DEVICES:
        del _asked[next(iter(_asked))]
    window = _asked.setdefault(device_id, deque())
    while window and now - window[0] >= WINDOW_S:
        window.popleft()
    if len(window) >= PER_DAY:
        return max(1, int(WINDOW_S - (now - window[0])))
    window.append(now)
    return None


class DataRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["delete"]
    confirmed: Literal[True]


class ReceiptOut(BaseModel):
    request_id: UUID
    status: Literal["pending", "done", "failed", "cancelled"]
    requested_at: datetime
    deadline_hours: Literal[72] = DEADLINE_HOURS
    execute_after: datetime  # purge bắt đầu từ lúc này; tới đó còn hủy được


@router.post(
    "",
    response_model=ReceiptOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Người được bảo vệ yêu cầu xóa dữ liệu gia đình (spec 038)",
    responses={
        200: {"model": ReceiptOut, "description": "Đã có yêu cầu đang chờ (lũy đẳng)"},
        429: {"description": BUSY},
    },
)
async def request_deletion(
    body: DataRequestIn, claims: Annotated[DeviceClaims, Depends(get_current_device)], response: Response
) -> ReceiptOut:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        member = await session.get(Member, claims.member_id)
        family = await session.get(Family, claims.family_id)
        if member is None or family is None or member.role != "protected":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Chỉ người được bảo vệ mới yêu cầu xóa dữ liệu")
        alias = safe_alias(member.alias)
        alerts_on = (await consent_gate.state_for(session, claims.member_id)).guardian_alerts
        is_demo = bool(family.is_demo)
    wait = _retry_after(claims.device_id, time.monotonic())
    if wait is not None:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=BUSY, headers={"Retry-After": str(wait)})

    def notice_for(
        due: datetime,
    ) -> dict:  # đã rút `guardian_alerts` ⇒ không dựng tin (còn kiểm lại lúc gửi, 037 FR-002)
        return {
            "template": "data_delete_notice",
            "family_id": str(claims.family_id),
            "guardian_rank": 1,
            "protected_member_id": str(claims.member_id),
            "job_key": None,  # đặt theo id yêu cầu ở `purge_service`
            "text": texts.guardian_data_delete_notice(alias, _when_label(due)),
            "urgent": True,
            "is_demo": is_demo,
            "is_drill": False,
        }

    request, created = await purge_service.request_delete_detailed(
        get_sessionmaker(),
        claims.family_id,
        "app",
        notice_for=notice_for if alerts_on else None,
        purge_delay_s=PURGE_DELAY_S,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return _receipt(request)


def _when_label(moment: datetime) -> str:
    local = moment.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    return f"{local:%H:%M} ngày {local.day} tháng {local.month}"


def _receipt(request: DataRequest) -> ReceiptOut:
    return ReceiptOut(
        request_id=request.id,
        status=request.status,  # type: ignore[arg-type]
        requested_at=request.requested_at,
        execute_after=request.execute_after,
    )


@router.delete(
    "/{request_id}",
    response_model=ReceiptOut,
    summary="Hủy yêu cầu xóa còn trong khoảng chờ 24 giờ (spec 038 FR-006)",
    responses={
        404: {"description": "Không thấy (hoặc không thuộc gia đình này)"},
        409: {"description": "Đã quá khoảng chờ hoặc đã xóa xong"},
    },
)
async def cancel_request(
    request_id: UUID, claims: Annotated[DeviceClaims, Depends(get_current_device)], response: Response
) -> ReceiptOut:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        member = await session.get(Member, claims.member_id)
    if member is None or member.role != "protected":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Chỉ người được bảo vệ mới hủy được yêu cầu xóa")
    try:
        request = await purge_service.cancel_delete(get_sessionmaker(), claims.family_id, request_id)
    except purge_service.CancelRefusedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Đã quá thời gian chờ hoặc dữ liệu đã được xóa, không hủy được nữa"
        ) from None
    if request is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy yêu cầu")
    return _receipt(request)
