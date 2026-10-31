"""`/v1/sim/*` (spec 033): mô phỏng một kịch bản hư cấu cho BGK, khớp `docs/schemas/sim_*.v1.json`.

Cổng `HOICON_SIM_ENABLED` (mặc định tắt ⇒ MỌI route trả 404, kể cả khi chưa đăng nhập: không lộ sự tồn tại). Cần phiên
người giám hộ của gia đình DEMO (gia đình thật ⇒ 404). Lệnh ghi qua `require_same_origin`. Logic ở
`services.sim_service`.
"""

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

from hoicon.api.auth import GuardianClaims, get_current_full_guardian, get_current_guardian, require_same_origin
from hoicon.api.routers.elder import ElderAnswerIn, resume_value
from hoicon.config import get_settings
from hoicon.db.models import Family
from hoicon.db.session import get_sessionmaker
from hoicon.ops import booth
from hoicon.services import sim_service
from hoicon.services.sim_service import SimError

NOT_FOUND = "Không tìm thấy"


def require_sim_enabled() -> None:
    if not get_settings().sim_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)


async def demo_guardian(claims: Annotated[GuardianClaims, Depends(get_current_guardian)]) -> GuardianClaims:
    async with get_sessionmaker()() as session:
        family = await session.get(Family, claims.family_id)
    if family is None or not family.is_demo:  # gia đình thật ⇒ 404, không lộ sự tồn tại của tính năng
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return claims


async def demo_full_guardian(
    claims: Annotated[GuardianClaims, Depends(get_current_full_guardian)],
) -> GuardianClaims:
    """Như `demo_guardian` nhưng từ chối phiên KHÁCH gian (chỉ xem + quyết định): dùng cho route ghi/cấu hình."""
    return await demo_guardian(claims)


router = APIRouter(prefix="/v1/sim", tags=["sim"], dependencies=[Depends(require_sim_enabled)])
Guardian = Annotated[GuardianClaims, Depends(demo_guardian)]
FullGuardian = Annotated[GuardianClaims, Depends(demo_full_guardian)]


class SimScenarioOut(BaseModel):
    id: str
    category: str
    title_vi: str
    is_benign: bool
    injection: bool
    draft: bool
    script_vi: str


class SimScenariosOut(BaseModel):
    scenarios: list[SimScenarioOut]


class SimQuestionOut(BaseModel):
    incident_id: UUID
    question_id: Literal["q_caller_authority", "q_asked_transfer", "q_know_caller"]
    text: str
    is_drill: bool
    answers: list[Literal["yes", "no", "unsure"]]
    expires_at: datetime


class SimMessageOut(BaseModel):
    at: datetime
    template: str
    text: str


class SimRunOut(BaseModel):
    """Khớp `docs/schemas/sim_run.v1.json`."""

    scenario_id: str
    is_demo: Literal[True]
    llm_mode: Literal["replay", "live", "fallback"]
    incident_id: UUID | None
    run_id: UUID | None
    state: str | None
    level: Literal["none", "low", "medium", "high", "critical"]
    pending_question: SimQuestionOut | None
    guardian_messages: list[SimMessageOut]
    note: str | None


class SimRunIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(pattern=r"^[a-z0-9]+(_[a-z0-9]+)*_[0-9]{3}$")
    llm: Literal["replay", "live"] = "replay"


def _http(exc: SimError) -> HTTPException:
    headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
    return HTTPException(exc.status, detail=exc.detail, headers=headers)


@router.get("/scenarios", response_model=SimScenariosOut)
async def get_scenarios(_: Guardian) -> dict[str, Any]:
    return {"scenarios": sim_service.list_scenarios()}


@router.post("/runs", response_model=SimRunOut, dependencies=[Depends(require_same_origin)])
async def post_run(body: SimRunIn, claims: FullGuardian) -> dict[str, Any]:
    try:
        return await sim_service.start_run(claims.member_id, claims.family_id, body.scenario_id, body.llm)
    except SimError as exc:
        raise _http(exc) from None


class SimResetOut(BaseModel):
    """Khớp `docs/schemas/sim_reset.v1.json`."""

    incidents: int
    devices: int
    seconds: float
    is_demo: Literal[True] = True


@router.post("/reset", response_model=SimResetOut, dependencies=[Depends(require_same_origin)])
async def post_reset(_: FullGuardian, response: Response) -> dict[str, Any]:
    """Nút Đặt lại của `/demo/console` (spec 050 FR-005c): cùng `ops.booth.reset_sim` — xóa mọi lượt mô phỏng của
    gia đình demo (sự cố, chạy, job, checkpoint, thiết bị `sim:`); không đụng gì khác."""
    response.headers["Cache-Control"] = "no-store"
    done = await booth.reset_sim(get_sessionmaker())
    await sim_service.drop_all()
    return done | {"is_demo": True}


@router.get("/runs/{incident_id}", response_model=SimRunOut)
async def get_run(incident_id: UUID, claims: Guardian) -> dict[str, Any]:
    try:
        return await sim_service.view(incident_id, claims.family_id)
    except SimError as exc:
        raise _http(exc) from None


@router.post("/runs/{incident_id}/answer", response_model=SimRunOut, dependencies=[Depends(require_same_origin)])
async def post_answer(incident_id: UUID, body: ElderAnswerIn, claims: FullGuardian) -> dict[str, Any]:
    try:
        return await sim_service.answer(incident_id, claims.family_id, resume_value(body), body.question_id)
    except SimError as exc:
        raise _http(exc) from None
