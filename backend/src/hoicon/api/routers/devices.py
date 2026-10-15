"""`GET /v1/devices/me` (spec 020, FR-004): thông tin thiết bị đang gọi + trạng thái đồng ý HIỆN TẠI (dòng mới nhất của
mỗi purpose trong sổ). Khớp `docs/schemas/device_me.v1.json`. Không trả token, băm bí mật hay FCM token."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import distinct_on

from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.models import Consent, Device, Family
from hoicon.db.session import get_sessionmaker

router = APIRouter(prefix="/v1", tags=["devices"])


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
