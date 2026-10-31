"""Diễn tập cho người giám hộ trên web (spec 028 FR-011): `POST/GET /v1/guardian/drills`.

Xác thực bằng phiên người giám hộ (cookie hoặc Bearer, như `/v1/guardian/*`); gia đình lấy từ phiên. Đặt lịch dùng chung
`DrillService.schedule` (khung 30 phút–4 giờ, không chồng lấn, hạn mức tháng, đồng ý `drills`); bị từ chối ⇒ 422
`{"detail": <mã DrillRefused>}` (mã ổn định, không dữ liệu cá nhân). Thân yêu cầu không có trường văn bản tự do. Khớp
`docs/schemas/guardian_drill_request.v1.json` / `guardian_drill_list.v1.json`. Không gọi LLM.
"""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.agents.runtime import safe_alias
from hoicon.api.auth import GuardianClaims, get_current_full_guardian
from hoicon.db.models import Drill, Member
from hoicon.db.session import get_sessionmaker
from hoicon.domain import drill as dr
from hoicon.services.drill_service import DrillRefused, DrillService, elders_for_form, schedulable_scripts

router = APIRouter(prefix="/v1/guardian/drills", tags=["guardian"])
NO_STORE = {"Cache-Control": "no-store"}
Guardian = Annotated[GuardianClaims, Depends(get_current_full_guardian)]  # phiên khách gian: 403


class GuardianDrillRequestIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    member_id: UUID
    script_id: Annotated[str, Field(pattern=r"^drill_[a-z0-9_]{3,40}$")]
    window_start: AwareDatetime
    window_end: AwareDatetime


class GuardianDrillOut(BaseModel):
    drill_id: UUID
    member_alias: str
    script_id: str
    script_title: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    status: Literal["scheduled", "offered", "in_progress", "passed", "failed", "aborted", "declined", "expired"]
    score: int | None
    is_drill: Literal[True] = True


class FormElder(BaseModel):
    member_id: UUID
    alias: str
    drills_consent: bool


class FormScript(BaseModel):
    id: str
    title: str
    summary: str


class GuardianDrillListOut(BaseModel):
    drills: list[GuardianDrillOut]
    elders: list[FormElder] | None = None  # chỉ GET gửi
    scripts: list[FormScript] | None = None


def _summary(script: dict) -> str:
    agency = script.get("agency_fictional", "một cơ quan hư cấu")
    return f"Cuộc gọi giả từ “{agency}”, {len(script['steps'])} bước."[:280]


async def _view(session: AsyncSession, drills: list[Drill]) -> GuardianDrillListOut:
    members = (
        {
            m.id: m
            for m in (await session.scalars(select(Member).where(Member.id.in_({d.member_id for d in drills})))).all()
        }
        if drills
        else {}
    )
    out = []
    for d in drills:
        script = dr.get_script(d.script_id) or {}
        member = members.get(d.member_id)
        out.append(
            GuardianDrillOut(
                drill_id=d.id,
                member_alias=safe_alias(member.alias if member else None),
                script_id=d.script_id,
                script_title=str(script.get("title") or d.script_id)[:120],
                window_start=d.window_start,
                window_end=d.window_end,
                status=d.status,  # type: ignore[arg-type]
                score=d.score,
                is_drill=True,
            )
        )
    return GuardianDrillListOut(drills=out)


@router.get(
    "",
    response_model=GuardianDrillListOut,
    response_model_exclude_unset=True,
    summary="Lịch và lịch sử diễn tập của gia đình (spec 028)",
)
async def list_drills(claims: Guardian, response: Response) -> GuardianDrillListOut:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        view = await _view(session, await DrillService.list_for_family(session, claims.family_id))
        view.elders = [
            FormElder(member_id=m.id, alias=safe_alias(m.alias), drills_consent=ok)
            for m, ok in await elders_for_form(session, claims.family_id)
        ]
        view.scripts = [
            FormScript(id=s["id"], title=str(s["title"])[:120], summary=_summary(s)) for s in schedulable_scripts()
        ][:20]
        return view


@router.post(
    "",
    response_model=GuardianDrillListOut,
    response_model_exclude_unset=True,
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch một bài diễn tập (spec 028)",
    responses={422: {"description": "Bị từ chối: `{detail: <mã DrillRefused>}`"}},
)
async def schedule_drill(body: GuardianDrillRequestIn, claims: Guardian, response: Response) -> GuardianDrillListOut:
    response.headers.update(NO_STORE)
    try:
        async with get_sessionmaker().begin() as session:
            drill = await DrillService.schedule(
                session,
                family_id=claims.family_id,
                member_id=body.member_id,
                window_start=body.window_start,
                window_end=body.window_end,
                script_id=body.script_id,
                by=str(claims.member_id),
            )
            return await _view(session, [drill])
    except DrillRefused as refused:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=refused.code) from None
