"""Web người giám hộ (spec 027): phiên đăng nhập bằng liên kết một lần qua Zalo và API đọc sự cố.

Khớp `docs/schemas/guardian_session.v1.json` và `incident_list.v1.json`.

Phiên: `POST /v1/guardian/session` đổi token `guardian_view` (gửi qua Zalo đã ghép, hạn 15 phút, dùng một lần) lấy
cookie `hc_guardian` = JWT người giám hộ 7 ngày, `HttpOnly; SameSite=Strict; Path=/v1` (+ `Secure` ngoài dev). Token
phiên KHÔNG nằm trong thân phản hồi. Token sai/đã dùng/quá hạn/sai scope/mồ côi đều trả cùng một 410 (không lộ lý do).
Mọi lệnh ghi bằng cookie phải qua `require_same_origin` (chống CSRF).
"""

import base64
import binascii
import logging
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field, computed_field
from sqlalchemy import String, and_, case, cast, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.api.auth import (
    GUARDIAN_COOKIE,
    GUARDIAN_ROLE,
    GUARDIAN_WEB_TTL,
    DeviceAuthNotConfiguredError,
    DeviceTokenError,
    GuardianClaims,
    _bearer,
    decode_guardian_access_token,
    ensure_configured,
    get_current_guardian,
    issue_guardian_access_token,
    require_same_origin,
)
from hoicon.api.routers.incidents import (
    IncidentDetail,
    IncidentSummary,
    _not_found,
    load_incident,
    load_transitions,
)
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, CaseFile, Family, Incident, Member, RevokedSession
from hoicon.db.session import get_sessionmaker
from hoicon.services import case_file_service, consent_gate
from hoicon.services.action_token_service import ActionTokenError, ActionTokenService
from hoicon.services.incident_service import ConcurrencyConflictError, InvalidTransitionError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/guardian", tags=["guardian"])

COOKIE_PATH = "/v1"
GONE_DETAIL = "Liên kết đăng nhập không dùng được. Nhắn 4 cho bot HỏiCon trên Zalo để nhận liên kết mới."
NO_STORE = {"Cache-Control": "no-store"}  # dữ liệu cá nhân: proxy/trình duyệt không được lưu


class SessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{32,64}$")]


class GuardianSession(BaseModel):
    member_id: UUID
    family_id: UUID
    family_name: str
    expires_at: datetime


def _gone() -> HTTPException:
    return HTTPException(status.HTTP_410_GONE, detail=GONE_DETAIL)


def _cookie_flags() -> dict[str, object]:
    return {
        "httponly": True,
        "secure": not get_settings().is_dev_env,  # dev qua http://localhost; ngoài dev luôn bật
        "samesite": "strict",
        "path": COOKIE_PATH,
    }


async def _session_view(claims: GuardianClaims, expires_at: datetime | None = None) -> GuardianSession:
    async with get_sessionmaker()() as session:
        family = await session.get(Family, claims.family_id)
    if family is None:  # gia đình đã bị xóa: phiên vô nghĩa
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực người giám hộ")
    when = expires_at or claims.expires_at
    assert when is not None  # noqa: S101 - decode luôn điền `exp`
    return GuardianSession(
        member_id=claims.member_id, family_id=claims.family_id, family_name=family.display_name, expires_at=when
    )


@router.post(
    "/session",
    response_model=GuardianSession,
    dependencies=[Depends(require_same_origin)],
    summary="Đổi token đăng nhập một lần (nhận qua Zalo) lấy cookie phiên",
    responses={
        403: {"description": "Không có bằng chứng cùng nguồn (Origin/Sec-Fetch-Site)"},
        410: {"description": "Token sai, đã dùng, quá hạn hoặc không dùng được (cùng một thông điệp)"},
    },
)
async def post_session(body: SessionIn, response: Response) -> GuardianSession:
    try:
        ensure_configured()  # TRƯỚC khi tiêu thụ token: thiếu khóa ký là lỗi của ta, không đốt liên kết của người dùng
    except DeviceAuthNotConfiguredError:
        logger.error("guardian session: chưa cấu hình khóa ký JWT")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    now = datetime.now(UTC)
    async with get_sessionmaker().begin() as session:
        try:
            record = await ActionTokenService.consume_token(session, body.token, expected_scope="guardian_view")
        except ActionTokenError:
            raise _gone() from None
        if (
            record.incident_id is not None
        ):  # `guardian_view` gắn một sự cố là liên kết XEM, không phải liên kết đăng nhập
            raise _gone()
        member = await session.get(Member, record.member_id)
        if member is None or member.role != GUARDIAN_ROLE:
            raise _gone()  # giao dịch hoàn tác: token không bị đốt oan
        family = await session.get(Family, member.family_id)
        if family is None:
            raise _gone()
        member_id, family_id, family_name = member.id, member.family_id, family.display_name
    token = issue_guardian_access_token(member_id, family_id, now=now, ttl=GUARDIAN_WEB_TTL)
    response.set_cookie(GUARDIAN_COOKIE, token, max_age=int(GUARDIAN_WEB_TTL.total_seconds()), **_cookie_flags())  # type: ignore[arg-type]
    response.headers.update(NO_STORE)
    logger.info("guardian session: đã cấp phiên web")
    return GuardianSession(
        member_id=member_id, family_id=family_id, family_name=family_name, expires_at=now + GUARDIAN_WEB_TTL
    )


@router.get("/me", response_model=GuardianSession, summary="Thông tin phiên hiện tại")
async def get_me(
    response: Response, claims: Annotated[GuardianClaims, Depends(get_current_guardian)]
) -> GuardianSession:
    response.headers.update(NO_STORE)
    return await _session_view(claims)


@router.delete(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_same_origin)],
    summary="Đăng xuất: xóa cookie phiên",
)
async def delete_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    cookie: Annotated[str | None, Cookie(alias=GUARDIAN_COOKIE)] = None,
) -> Response:
    """Xóa cookie VÀ thu hồi phía máy chủ `jti` của token (tới khi hết hạn): bản sao bị lấy cắp hết tác dụng. Không có
    token hợp lệ (đã hết hạn, đã xóa cookie) vẫn 204: đăng xuất luôn thành công."""
    token = cookie if credentials is None else credentials.credentials
    if token:
        try:
            claims = decode_guardian_access_token(token)
        except (DeviceTokenError, DeviceAuthNotConfiguredError):
            claims = None
        if claims is not None and claims.jti is not None and claims.expires_at is not None:
            async with get_sessionmaker().begin() as session:
                await session.execute(
                    insert(RevokedSession)
                    .values(jti=claims.jti, expires_at=claims.expires_at)
                    .on_conflict_do_nothing(index_elements=["jti"])
                )
    response = Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)
    response.delete_cookie(GUARDIAN_COOKIE, **_cookie_flags())  # type: ignore[arg-type]
    return response


# --- FR-004: API đọc sự cố ---------------------------------------------------------------------------------------

PAGE_SIZE = 20
OPEN_STATES = ("detected", "assessing", "awaiting_guardian", "verifying", "rescore", "case_open")


class GuardianIncidentSummary(IncidentSummary):
    elder_alias: str | None
    has_run: bool


class GuardianIncidentDetail(IncidentDetail):
    elder_alias: str | None
    run_id: UUID | None


class GuardianIncidentList(BaseModel):
    incidents: list[GuardianIncidentSummary]
    next_cursor: str | None


def _bad_cursor() -> HTTPException:
    detail = [{"loc": ["query", "cursor"], "msg": "cursor không hợp lệ", "type": "cursor_invalid"}]
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


def _encode_cursor(group: int, row: Incident) -> str:
    raw = f"{group}|{row.opened_at.isoformat()}|{row.id}".encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[int, datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        group, opened_at, incident_id = raw.split("|")
        if group not in ("0", "1"):
            raise ValueError
        moment = datetime.fromisoformat(opened_at)
        if moment.tzinfo is None:
            raise ValueError
        return int(group), moment, UUID(incident_id)
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise _bad_cursor() from None


@router.get(
    "/incidents",
    response_model=GuardianIncidentList,
    summary="Sự cố của gia đình, đang mở trước, phân trang bằng khóa (opened_at, id)",
    responses={401: {"description": "Chưa đăng nhập"}, 422: {"description": "cursor hoặc status không hợp lệ"}},
)
async def list_incidents(
    response: Response,
    claims: Annotated[GuardianClaims, Depends(get_current_guardian)],
    status_filter: Annotated[Literal["open", "closed"] | None, Query(alias="status")] = None,
    cursor: Annotated[str | None, Query(max_length=128)] = None,
) -> GuardianIncidentList:
    response.headers.update(NO_STORE)
    group = case((Incident.state.in_(OPEN_STATES), 0), else_=1)
    has_run = select(AgentRun.id).where(AgentRun.thread_id == cast(Incident.id, String)).correlate(Incident).exists()
    query = (
        select(Incident, Member.alias, has_run.label("has_run"), group.label("grp"))
        .join(Member, Member.id == Incident.member_id, isouter=True)
        .where(Incident.family_id == claims.family_id)
    )
    async with get_sessionmaker()() as session:
        consenting = await consent_gate.web_readable_members(session, claims.family_id)
    # Spec 011 FR-006/D9: người cao tuổi đã rút đồng ý ⇒ sự cố của họ không còn hiện trên web (demo hư cấu được miễn).
    query = query.where(or_(Incident.is_demo.is_(True), Incident.member_id.in_(consenting)))
    if status_filter == "open":
        query = query.where(Incident.state.in_(OPEN_STATES))
    elif status_filter == "closed":
        query = query.where(Incident.state.not_in(OPEN_STATES))
    if cursor is not None:
        g, opened_at, incident_id = _decode_cursor(cursor)
        query = query.where(
            or_(
                group > g,
                and_(
                    group == g,
                    or_(
                        Incident.opened_at < opened_at, and_(Incident.opened_at == opened_at, Incident.id < incident_id)
                    ),
                ),
            )
        )
    query = query.order_by(group, Incident.opened_at.desc(), Incident.id.desc()).limit(PAGE_SIZE + 1)
    async with get_sessionmaker()() as session:
        rows = (await session.execute(query)).all()
    page = rows[:PAGE_SIZE]
    items = [
        GuardianIncidentSummary(
            **IncidentSummary.model_validate(row.Incident, from_attributes=True).model_dump(),
            elder_alias=row.alias,
            has_run=bool(row.has_run),
        )
        for row in page
    ]
    next_cursor = _encode_cursor(page[-1].grp, page[-1].Incident) if len(rows) > PAGE_SIZE else None
    return GuardianIncidentList(incidents=items, next_cursor=next_cursor)


@router.get(
    "/incidents/{incident_id}",
    response_model=GuardianIncidentDetail,
    summary="Chi tiết một sự cố của gia đình (kèm lịch sử chuyển trạng thái và run_id)",
    responses={401: {"description": "Chưa đăng nhập"}, 404: {"description": "Không thấy (hoặc không thuộc nhà)"}},
)
async def get_incident_detail(
    incident_id: UUID, response: Response, claims: Annotated[GuardianClaims, Depends(get_current_guardian)]
) -> GuardianIncidentDetail:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        incident = await load_incident(session, incident_id, claims.family_id)
        if incident is None or not await consent_gate.web_readable(
            session, incident.member_id, is_demo=incident.is_demo
        ):
            raise _not_found()
        alias = await session.scalar(select(Member.alias).where(Member.id == incident.member_id))
        run_id = await session.scalar(select(AgentRun.id).where(AgentRun.thread_id == str(incident.id)))
        return GuardianIncidentDetail(
            **IncidentSummary.model_validate(incident, from_attributes=True).model_dump(),
            transitions=await load_transitions(session, incident.id),
            elder_alias=alias,
            run_id=run_id,
        )


# --- Hồ sơ vụ việc (spec 031, FR-007) -----------------------------------------------------------------------------
class CaseTimelineItem(BaseModel):
    at: datetime
    text: str


class CaseElderAnswer(BaseModel):
    question: str
    answer: str


class CaseVerification(BaseModel):
    kind: Literal["phone", "link"]
    verdict: Literal["dangerous", "warning", "unknown"]
    source: str
    list_version: str | None


class CaseLocalField(BaseModel):
    key: str
    label: str


class CaseFileContent(BaseModel):
    """Khớp `docs/schemas/case_file.v1.json#/$defs/content`."""

    schema_version: Literal[1]
    ai_label: str
    summary: str
    elder_alias: str
    level: Literal["low", "medium", "high", "critical"]
    reasons: list[str]
    rule: str
    caller_last3: str | None
    app_category: Literal["bank", "wallet", "securities", "sideloaded", "remote_control", "none"]
    timeline: list[CaseTimelineItem]
    elder_answers: list[CaseElderAnswer]
    verifications: list[CaseVerification]
    guardian_decision: Literal["scam", "emergency_pause"]
    local_fields: list[CaseLocalField]


class CaseGuidanceStep(BaseModel):
    id: str
    text_vi: str
    source_ref: str | None = None


class CaseGuidance(BaseModel):
    """Khớp `case_file.v1#/properties/guidance`; chưa duyệt ⇒ `steps` rỗng."""

    approved: bool
    steps: list[CaseGuidanceStep]
    fallback_vi: str


class CaseFileOut(BaseModel):
    """Khớp `docs/schemas/case_file.v1.json`."""

    id: UUID
    incident_id: UUID
    status: Literal["draft", "approved", "sent", "discarded"]
    summary_source: Literal["template", "llm"]
    created_at: datetime
    approved_at: datetime | None
    sent_at: datetime | None
    discarded_at: datetime | None
    is_demo: bool
    content: CaseFileContent

    @computed_field  # không thuộc dòng DB: đọc từ YAML đã nạp (một lần); computed ⇒ luôn có trong lược đồ OpenAPI
    @property
    def guidance(self) -> CaseGuidance:
        return CaseGuidance.model_validate(case_file_service.load_guidance())


class CaseFileActionIn(BaseModel):
    """Khớp `docs/schemas/case_file_action.v1.json`: không có trường nội dung nào."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "discard", "mark_sent"]


async def _own_case_file(session: AsyncSession, incident_id: UUID, family_id: UUID) -> CaseFile:
    incident = await load_incident(session, incident_id, family_id)
    row = None
    if incident is not None:
        row = await session.scalar(select(CaseFile).where(CaseFile.incident_id == incident_id))
    if row is None:  # sự cố nhà khác, không có hồ sơ: cùng một 404 (không lộ sự tồn tại)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ")
    # Hồ sơ thuộc mục đích `guardian_alerts`: chưa/không còn đồng ý ⇒ cùng 404 (dữ liệu demo hư cấu được miễn).
    if incident is not None and not await consent_gate.web_readable(session, incident.member_id, is_demo=row.is_demo):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ")
    return row


@router.get(
    "/incidents/{incident_id}/case-file",
    response_model=CaseFileOut,
    summary="Hồ sơ vụ việc của một sự cố (spec 031)",
    responses={401: {"description": "Chưa đăng nhập"}, 404: {"description": "Không thấy (hoặc không thuộc nhà)"}},
)
async def get_case_file(
    incident_id: UUID, response: Response, claims: Annotated[GuardianClaims, Depends(get_current_guardian)]
) -> CaseFileOut:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        row = await _own_case_file(session, incident_id, claims.family_id)
        return CaseFileOut.model_validate(row, from_attributes=True)


@router.post(
    "/incidents/{incident_id}/case-file",
    response_model=CaseFileOut,
    dependencies=[Depends(require_same_origin)],
    summary="Duyệt, bỏ hoặc đánh dấu đã nộp hồ sơ (spec 031)",
    responses={
        403: {"description": "Không có bằng chứng cùng nguồn"},
        404: {"description": "Không thấy (hoặc không thuộc nhà)"},
        409: {"description": "Lệnh không hợp lệ với trạng thái hiện tại"},
    },
)
async def post_case_file(
    incident_id: UUID,
    body: CaseFileActionIn,
    response: Response,
    claims: Annotated[GuardianClaims, Depends(get_current_guardian)],
) -> CaseFileOut:
    response.headers.update(NO_STORE)
    async with get_sessionmaker()() as session:
        await _own_case_file(session, incident_id, claims.family_id)  # 404 trước mọi thay đổi
    try:
        async with get_sessionmaker().begin() as session:
            row = await case_file_service.apply_action(
                session, incident_id, body.action, actor="guardian", member_id=claims.member_id
            )
            return CaseFileOut.model_validate(row, from_attributes=True)
    except (case_file_service.CaseFileConflictError, InvalidTransitionError, ConcurrencyConflictError):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Hồ sơ không còn ở trạng thái này. Anh/chị tải lại trang."
        ) from None
