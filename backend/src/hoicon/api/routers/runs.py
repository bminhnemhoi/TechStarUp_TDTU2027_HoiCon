"""Truy vết tác tử cho người giám hộ (spec 025, FR-006/FR-007): lịch sử bước, luồng SSE, tìm lượt từ sự cố.

Khớp `docs/schemas/{agent_step,run_steps,run_done}.v1.json`. Chỉ ĐỌC. Xác thực bằng JWT người giám hộ (`Authorization`);
KHÔNG nhận token qua query string vì Caddy ghi log URL. Client dùng header `Authorization` (app/fetch) hoặc cookie phiên
`hc_guardian` cùng nguồn (web, `EventSource`, spec 027).

Quyền xem: `agent_runs.thread_id` phải là UUID của một sự cố thuộc gia đình của token. Lượt eval (`eval-…`), lượt
của gia đình khác và id lạ đều trả CÙNG một 404 (không lộ lượt có tồn tại hay không). 401/404/429/503 trả TRƯỚC khi
luồng bắt đầu.
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from hoicon.api.auth import GuardianClaims, get_current_guardian
from hoicon.db.models import AgentRun, Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate, trace_service
from hoicon.services.trace_service import StreamLimitError, TraceStreamResponse

router = APIRouter(prefix="/v1", tags=["trace"])

STREAM_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
}  # KHÔNG đặt `Connection` (hop-by-hop)


class EventStreamResponse(StreamingResponse):
    """Chỉ để OpenAPI khai báo `text/event-stream` cho route stream."""

    media_type = "text/event-stream"


class IncidentRun(BaseModel):
    run_id: UUID
    status: str


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lượt chạy")


def _uuid_or_none(raw: str) -> UUID | None:
    try:
        return UUID(raw)
    except ValueError:
        return None


async def _visible_run(session: AsyncSession, run_id: UUID, claims: GuardianClaims) -> AgentRun:
    run = await session.get(AgentRun, run_id)
    incident_id = _uuid_or_none(run.thread_id) if run is not None else None
    if run is None or incident_id is None:
        raise _not_found()
    owned = await session.scalar(
        select(Incident).where(Incident.id == incident_id, Incident.family_id == claims.family_id)
    )
    if owned is None or not await consent_gate.web_readable(
        session, owned.member_id, is_demo=owned.is_demo
    ):  # spec 011 D9: rút đồng ý ⇒ cùng 404
        raise _not_found()
    return run


@router.get(
    "/runs/{run_id}/steps",
    summary="Lịch sử các bước đã che của một lượt chạy",
    responses={401: {"description": "Thiếu hoặc sai token"}, 404: {"description": "Không thấy (hoặc không thuộc nhà)"}},
)
async def get_run_steps(
    run_id: UUID, response: Response, claims: Annotated[GuardianClaims, Depends(get_current_guardian)]
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"  # dữ liệu cá nhân: proxy/trình duyệt không được lưu
    async with get_sessionmaker()() as session:
        run = await _visible_run(session, run_id, claims)
        rows = await trace_service.list_steps(session, run.id)
        return {
            "run_id": str(run.id),
            "status": run.status,
            "is_drill": run.is_drill,
            "is_demo": run.is_demo,
            "steps": [trace_service.step_view(row) for row in rows],
        }


@router.get(
    "/runs/{run_id}/stream",
    response_class=EventStreamResponse,
    summary="Luồng SSE các bước của một lượt chạy",
    description=(
        "Khung: `retry: 3000`; `id/event: step/data` (agent_step.v1); `: ping` mỗi 15 s khi im lặng; `event: done` "
        "(run_done.v1) rồi đóng; `event: error` khi DB lỗi. Nối lại bằng header `Last-Event-ID`. Xác thực bằng "
        "`Authorization: Bearer` (app) hoặc cookie phiên `hc_guardian` cùng nguồn (web dùng `EventSource`, spec 027)."
    ),
    responses={
        200: {"description": "Luồng sự kiện", "content": {"text/event-stream": {}}},
        401: {"description": "Thiếu hoặc sai token"},
        404: {"description": "Không thấy (hoặc không thuộc nhà)"},
        429: {"description": "Người này đã mở đủ 3 luồng (có Retry-After)"},
        503: {"description": "Máy chủ đã đủ 20 luồng (có Retry-After)"},
    },
)
async def stream_run(
    run_id: UUID,
    request: Request,
    claims: Annotated[GuardianClaims, Depends(get_current_guardian)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> TraceStreamResponse:
    async with get_sessionmaker()() as session:  # đóng trước khi luồng bắt đầu: luồng không giữ kết nối pool
        run = await _visible_run(session, run_id, claims)
    thread_id = run.thread_id

    async def still_allowed() -> bool:
        """Kiểm lại đồng ý mỗi nhịp: người cao tuổi rút giữa chừng ⇒ luồng đang mở dừng (spec 011 D9)."""
        async with get_sessionmaker()() as check:
            incident = await check.get(Incident, UUID(thread_id))
            return incident is not None and await consent_gate.web_readable(
                check, incident.member_id, is_demo=incident.is_demo
            )

    try:
        slot = trace_service.acquire_slot(claims.member_id, claims.family_id)
    except StreamLimitError as exc:
        detail = {
            "member": "Bạn đang mở quá nhiều luồng theo dõi. Hãy đóng bớt rồi thử lại.",
            "family": "Gia đình đã mở đủ số luồng theo dõi. Hãy đóng bớt một luồng rồi thử lại.",
        }.get(exc.scope, "Máy chủ đang bận. Hãy thử lại sau vài giây.")
        raise HTTPException(exc.status_code, detail=detail, headers={"Retry-After": str(exc.retry_after_s)}) from None
    try:
        body = trace_service.stream_run(
            get_sessionmaker(), run.id, last_event_id, request.is_disconnected, still_allowed
        )
        return TraceStreamResponse(body, slot, media_type="text/event-stream", headers=STREAM_HEADERS)
    except BaseException:
        slot.release()
        raise


@router.get(
    "/incidents/{incident_id}/run",
    response_model=IncidentRun,
    summary="Tìm lượt chạy của một sự cố (để mở luồng truy vết)",
    responses={401: {"description": "Thiếu hoặc sai token"}, 404: {"description": "Chưa có lượt hoặc không thuộc nhà"}},
)
async def get_incident_run(
    incident_id: UUID, claims: Annotated[GuardianClaims, Depends(get_current_guardian)]
) -> IncidentRun:
    async with get_sessionmaker()() as session:
        owned = await session.scalar(
            select(Incident).where(Incident.id == incident_id, Incident.family_id == claims.family_id)
        )
        visible = owned is not None and await consent_gate.web_readable(session, owned.member_id, is_demo=owned.is_demo)
        run = await session.scalar(select(AgentRun).where(AgentRun.thread_id == str(incident_id))) if visible else None
        if run is None:
            raise _not_found()
        return IncidentRun(run_id=run.id, status=run.status)
