"""`GET /v1/incidents/{id}` và `GET /v1/families/{id}/incidents` (spec 021, FR-007).
Khớp `docs/schemas/incident.v1.json`.

Chỉ đọc, chỉ trong phạm vi GIA ĐÌNH của token thiết bị: sự cố/gia đình của nhà khác trả 404 (không phải 403) để không lộ
sự tồn tại. Không có số điện thoại/h1/HMAC trong phản hồi. Người giám hộ đọc qua `/a/[token]` (spec 022), không qua đây.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.api.auth import DeviceClaims, GuardianClaims, get_current_device, get_current_guardian
from hoicon.api.routers.actions import ALREADY_HANDLED, IncidentDecisionIn, IncidentDecisionResult
from hoicon.db.models import Incident, IncidentTransition
from hoicon.db.session import get_sessionmaker
from hoicon.services.incident_service import (
    ConcurrencyConflictError,
    InvalidTransitionError,
    apply_guardian_decision,
)

router = APIRouter(prefix="/v1", tags=["incidents"])

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


class TransitionOut(BaseModel):
    from_state: str | None
    to_state: str
    actor: str
    reason: str | None
    at: datetime


class IncidentSummary(BaseModel):
    id: UUID
    family_id: UUID
    member_id: UUID
    device_id: UUID | None
    state: str
    level: str
    rule_floor: str
    version: int
    is_drill: bool
    drill_id: UUID | None
    opened_by_event_id: UUID | None
    outcome: str | None
    opened_at: datetime
    closed_at: datetime | None


class IncidentDetail(IncidentSummary):
    transitions: list[TransitionOut]


class IncidentList(BaseModel):
    incidents: list[IncidentSummary]


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sự cố")


async def load_incident(session: AsyncSession, incident_id: UUID, family_id: UUID) -> Incident | None:
    """Sự cố CỦA gia đình này (nhà khác và id lạ cùng trả None ⇒ route trả 404, không lộ sự tồn tại). Dùng chung cho
    route thiết bị và route người giám hộ (spec 027)."""
    return await session.scalar(select(Incident).where(Incident.id == incident_id, Incident.family_id == family_id))


async def load_transitions(session: AsyncSession, incident_id: UUID) -> list[TransitionOut]:
    rows = await session.scalars(
        select(IncidentTransition)
        .where(IncidentTransition.incident_id == incident_id)
        .order_by(IncidentTransition.at, IncidentTransition.id)
    )
    return [TransitionOut.model_validate(row, from_attributes=True) for row in rows]


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: UUID, claims: Annotated[DeviceClaims, Depends(get_current_device)]
) -> IncidentDetail:
    async with get_sessionmaker()() as session:
        incident = await load_incident(session, incident_id, claims.family_id)
        if incident is None:
            raise _not_found()
        return IncidentDetail(
            **IncidentSummary.model_validate(incident, from_attributes=True).model_dump(),
            transitions=await load_transitions(session, incident.id),
        )


@router.get("/families/{family_id}/incidents", response_model=IncidentList)
async def list_family_incidents(
    family_id: UUID,
    claims: Annotated[DeviceClaims, Depends(get_current_device)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> IncidentList:
    if family_id != claims.family_id:
        raise _not_found()
    async with get_sessionmaker()() as session:
        rows = await session.scalars(
            select(Incident)
            .where(Incident.family_id == family_id)
            .order_by(Incident.opened_at.desc(), Incident.id.desc())
            .limit(limit)
        )
        return IncidentList(incidents=[IncidentSummary.model_validate(row, from_attributes=True) for row in rows])


@router.post("/incidents/{incident_id}/decision", response_model=IncidentDecisionResult)
async def post_incident_decision(
    incident_id: UUID,
    body: IncidentDecisionIn,
    claims: Annotated[GuardianClaims, Depends(get_current_guardian)],
) -> IncidentDecisionResult:
    """Người giám hộ đã đăng nhập JWT gửi quyết định xử lý sự cố (spec 023, FR-006).

    Chỉ cho phép người giám hộ thuộc cùng gia đình thao tác; sự cố gia đình khác trả 404.
    """
    async with get_sessionmaker().begin() as session:
        incident = await load_incident(session, incident_id, claims.family_id)
        if incident is None:
            raise _not_found()

        try:
            incident = await apply_guardian_decision(session, incident, body.decision, "guardian_jwt")
        except ConcurrencyConflictError:
            raise HTTPException(
                status.HTTP_409_CONFLICT, detail="Sự cố đã được cập nhật bởi thao tác khác, vui lòng thử lại"
            ) from None
        except InvalidTransitionError:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=ALREADY_HANDLED) from None

        return IncidentDecisionResult(
            success=True,
            incident_id=incident.id,
            state=incident.state,
            outcome=incident.outcome,
        )
