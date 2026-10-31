"""`GET /v1/devices/me` (spec 020, FR-004): thông tin thiết bị đang gọi + trạng thái đồng ý HIỆN TẠI (dòng mới nhất của
mỗi purpose trong sổ). Khớp `docs/schemas/device_me.v1.json`. Không trả token, băm bí mật hay FCM token.

`POST /v1/heartbeat` (spec 029, FR-002): Android báo mỗi 15 phút còn sống + phiên bản + cờ quyền. Khớp
`docs/schemas/heartbeat.v1.json`. Kiểm đồng ý `core_protection` (spec 034) và hạn mức 8 lần/giờ/thiết bị."""

import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on

from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.api.rate_limit import SlidingWindowLimit
from hoicon.db.models import Consent, Device, Family
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import VersionName
from hoicon.services import consent_gate, heartbeat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["devices"])

HEARTBEATS_PER_HOUR = 8  # Android gửi 4 lần/giờ; dư để chịu lệch giờ/WorkManager dồn việc
BUSY = "Thiết bị báo tin quá nhiều lần, vui lòng thử lại sau."
CONSENT_WITHDRAWN = "consent_withdrawn"  # cùng mã với POST /v1/events (spec 034): app hiện "cần đồng ý lại"
_limit = SlidingWindowLimit(HEARTBEATS_PER_HOUR, 3600.0)


def reset_limits() -> None:
    _limit.reset()


class DeviceInfo(BaseModel):
    device_id: str
    family_id: str
    member_id: str
    family_name: str
    platform: str
    label: str | None
    app_version: str
    rules_version: str
    threat_list_version: str | None
    created_at: datetime
    last_heartbeat_at: datetime


class ConsentState(BaseModel):
    purpose: str
    granted: bool
    consent_version: str
    recorded_at: datetime


class DeviceMe(BaseModel):
    device: DeviceInfo
    consents: list[ConsentState]


@router.get("/devices/me", response_model=DeviceMe)
async def device_me(claims: Annotated[DeviceClaims, Depends(get_current_device)]) -> DeviceMe:
    async with get_sessionmaker()() as session:
        row = (
            await session.execute(
                select(Device, Family.display_name)
                .join(Family, Family.id == Device.family_id)
                .where(Device.id == claims.device_id, Device.revoked_at.is_(None))
            )
        ).one_or_none()
        if row is None:  # bị thu hồi giữa hai truy vấn
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực thiết bị")
        device, family_name = row
        latest = (
            await session.scalars(
                select(Consent)
                .ext(distinct_on(Consent.purpose))
                .where(Consent.member_id == claims.member_id)
                .order_by(Consent.purpose, Consent.recorded_at.desc(), Consent.id.desc())
            )
        ).all()
    return DeviceMe(
        device=DeviceInfo(
            device_id=str(device.id),
            family_id=str(device.family_id),
            member_id=str(device.member_id),
            family_name=family_name,
            platform=device.platform,
            label=device.label,
            app_version=device.app_version,
            rules_version=device.rules_version,
            threat_list_version=device.threat_list_version,
            created_at=device.created_at,
            last_heartbeat_at=device.last_heartbeat_at,
        ),
        consents=[
            ConsentState(
                purpose=c.purpose, granted=c.granted, consent_version=c.consent_version, recorded_at=c.recorded_at
            )
            for c in latest
        ],
    )


PermissionName = Annotated[str, StringConstraints(pattern=r"^[a-z_]{1,32}$")]


class HeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_version: VersionName
    rules_version: VersionName
    threat_list_version: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    permission_state: dict[PermissionName, StrictBool] = Field(max_length=16)


class HeartbeatOut(BaseModel):
    status: Literal["ok"] = "ok"


@router.post("/heartbeat", response_model=HeartbeatOut)
async def heartbeat(body: HeartbeatIn, claims: Annotated[DeviceClaims, Depends(get_current_device)]) -> HeartbeatOut:
    wait = _limit.retry_after(claims.device_id)
    if wait is not None:
        logger.info("heartbeat: thiết bị vượt hạn mức giờ")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=BUSY, headers={"Retry-After": str(wait)})
    async with get_sessionmaker().begin() as session:
        consent = await consent_gate.state_for(session, claims.member_id)
        if not consent.core_protection:  # đã rút (hoặc chưa có) đồng ý ⇒ không ghi gì, kể cả mốc giờ
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=CONSENT_WITHDRAWN)
        alive = await heartbeat_service.record(
            session,
            claims.device_id,
            app_version=body.app_version,
            rules_version=body.rules_version,
            threat_list_version=body.threat_list_version,
            permission_state=body.permission_state,
            now=datetime.now(UTC),
        )
    if not alive:  # bị thu hồi giữa lúc xác thực và ghi
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực thiết bị")
    return HeartbeatOut()
