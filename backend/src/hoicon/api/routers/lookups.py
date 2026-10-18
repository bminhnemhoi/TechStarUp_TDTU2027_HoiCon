"""`POST /v1/lookups` (spec 026, FR-005/FR-006): tra một số điện thoại (đã băm trên máy) hoặc một đường link.

Khớp `docs/schemas/{lookup_request,lookup_result}.v1.json`. Người gọi là THIẾT BỊ (người cao tuổi) hoặc NGƯỜI GIÁM HỘ
(JWT khác audience). Kết luận do `verification_service` quyết định bằng quy tắc tất định, không LLM.

- Riêng tư (ADR-006): số điện thoại chỉ đến dạng h1; URL chỉ giữ tên máy chủ trong bộ nhớ. Phản hồi, log và job không
  có h1, HMAC, URL hay host. 422 do handler chung chỉ nêu vị trí lỗi.
- Đồng ý: đòi dòng `lookups` mới nhất của chính người gọi đang `granted` (403 nếu không).
- Hạn mức đếm trên `verifications` (bền qua khởi động lại, để lại vết kiểm toán) trong CÙNG giao dịch với việc ghi,
  dưới khóa tư vấn theo gia đình ⇒ yêu cầu đồng thời không cùng lọt qua mức "còn 1 lần".
  Thiết bị 20/giờ & 60/ngày; người giám hộ 60/giờ; cả gia đình 200/ngày. Yêu cầu bị từ chối không được ghi.
- Luật 5: router KHÔNG gửi tin. Có `incident_id` ⇒ chỉ NÂNG mức sự cố (`IncidentService.raise_level`); người cao tuổi
  tra ra `dangerous` thì xếp job `graph_resume {"evidence"}` để node `await_guardian` (được phép gửi tin) báo con,
  tối đa một lần mỗi sự cố (khóa `{incident}:evidence`).
"""

import base64
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from psycopg.errors import LockNotAvailable
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.api.auth import DeviceClaims, get_current_device, get_current_guardian
from hoicon.config import get_settings
from hoicon.db.models import Consent, Device, Incident, Verification
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import enqueue
from hoicon.services import threat_list_service
from hoicon.services import verification_service as vs
from hoicon.services.incident_service import GUARDIAN_DECIDABLE, IncidentService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["lookups"])
_bearer = HTTPBearer(auto_error=False)

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
MONTH = timedelta(days=30)
DEVICE_PER_HOUR = 20
DEVICE_PER_DAY = 60
GUARDIAN_PER_HOUR = 60
FAMILY_PER_DAY = 200
# Trần cuộn 30 ngày (review bảo mật 026 #1): trần giờ/ngày không chặn được việc dò danh sách đe dọa kéo dài (mỗi
# bucket bị gắn cờ chỉ còn ≈ 86 ứng viên ở b = 22, ADR-011). Ngưỡng rộng gấp ~10 lần cách dùng thật (vài lần/tuần);
# Tiến xác nhận.
DEVICE_PER_MONTH = 600
GUARDIAN_PER_MONTH = 600
FAMILY_PER_MONTH = 3000
LOCK_TIMEOUT_MS = 3000
BUSY = "Hệ thống đang bận, vui lòng thử lại sau ít giây."
TOO_MANY = "Bạn đã tra cứu nhiều lần, vui lòng thử lại sau."
CONSENT_REQUIRED = "Cần đồng ý cho HỏiCon tra cứu số điện thoại và đường link trước khi dùng tính năng này."
_H1 = "0123456789abcdef"

THREAT_LIST_PER_DAY = 24
THREAT_LIST_WINDOW_S = 86400
MAX_TRACKED_DEVICES = 4096
# Hạn mức `GET /v1/threat-list` đếm trong bộ nhớ (một tiến trình, ADR-002): danh sách đằng nào cũng phát cho mọi máy.
_threat_list_hits: dict[UUID, deque[float]] = {}


def reset_limits() -> None:
    """Xóa bộ đếm trong bộ nhớ (hạn mức tra cứu nằm trong DB nên không cần)."""
    _threat_list_hits.clear()


@dataclass(frozen=True)
class Actor:
    kind: Literal["device", "guardian"]
    actor_id: UUID  # devices.id | members.id (khóa hạn mức + cột `verifications.actor_id`)
    family_id: UUID
    member_id: UUID  # chủ của dòng đồng ý


async def get_lookup_actor(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> Actor:
    """Thiết bị trước, người giám hộ sau (hai audience JWT khác nhau); cả hai đều đối chiếu DB."""
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail="Chưa xác thực", headers={"WWW-Authenticate": "Bearer"}
    )
    if credentials is None:
        raise unauthorized
    try:
        device = await get_current_device(credentials)
        return Actor("device", device.device_id, device.family_id, device.member_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    try:
        guardian = await get_current_guardian(request, credentials)  # chỉ Bearer: không dùng cookie web ở đây
        return Actor("guardian", guardian.member_id, guardian.family_id, guardian.member_id)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    raise unauthorized


class LookupIn(BaseModel):
    """Một chủ thể tra cứu. Cấm mọi trường lạ (kể cả `number`/`phone`): số thô không được phép tới đây."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    via: Literal["typed", "qr"]
    h1: str | None = None
    last3: str | None = None
    url: str | None = Field(default=None, min_length=4, max_length=vs.MAX_URL_LENGTH)
    incident_id: UUID | None = None

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        if value not in {"phone", "url"}:
            raise PydanticCustomError("kind_not_supported", "kind chưa được hỗ trợ")
        return value

    @field_validator("h1")
    @classmethod
    def _h1(cls, value: str | None) -> str | None:
        if value is not None and not (len(value) == 64 and all(c in _H1 for c in value)):
            raise PydanticCustomError("h1_invalid", "h1 phải là SHA-256 hex chữ thường (64 ký tự)")
        return value

    @field_validator("last3")
    @classmethod
    def _last3(cls, value: str | None) -> str | None:
        if value is not None and not (len(value) == 3 and value.isascii() and value.isdigit()):
            raise PydanticCustomError("last3_invalid", "last3 phải đúng 3 chữ số")
        return value

    @model_validator(mode="after")
    def _shape(self) -> "LookupIn":
        if self.kind == "phone" and (self.h1 is None or self.last3 is None or self.url is not None):
            raise PydanticCustomError("subject_mismatch", "phone cần đúng h1 và last3")
        if self.kind == "url" and (self.url is None or self.h1 is not None or self.last3 is not None):
            raise PydanticCustomError("subject_mismatch", "url cần đúng url")
        return self


class Reason(BaseModel):
    code: str
    text: str


class Source(BaseModel):
    name: str
    type: Literal["threat_list", "heuristic", "registry"]
    list_version: str | None = None
    url: str | None = None


class LookupResult(BaseModel):
    verification_id: UUID
    kind: Literal["phone", "url"]
    verdict: Literal["safe", "warning", "dangerous", "unknown"]
    confidence: float
    reasons: list[Reason]
    sources: list[Source]
    disclaimer: str
    incident_level: Literal["low", "medium", "high", "critical"] | None = None
    is_demo: bool


async def _lock(session: AsyncSession, key: str) -> None:
    await session.execute(text("select pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


async def _require_consent(session: AsyncSession, actor: Actor) -> None:
    latest = await session.scalar(
        select(Consent.granted)
        .where(Consent.member_id == actor.member_id, Consent.purpose == "lookups")
        .order_by(Consent.recorded_at.desc(), Consent.id.desc())
        .limit(1)
    )
    if latest is not True:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=CONSENT_REQUIRED)


async def _owned_incident(session: AsyncSession, actor: Actor, incident_id: UUID) -> Incident:
    query = select(Incident).where(Incident.id == incident_id, Incident.family_id == actor.family_id)
    if actor.kind == "device":  # người được bảo vệ chỉ gắn vào sự cố CỦA MÌNH (nhà có thể có nhiều người cao tuổi)
        query = query.where(Incident.member_id == actor.member_id)
    incident = await session.scalar(query)
    if incident is None:  # của nhà khác và id lạ cùng một 404 (không lộ sự cố có tồn tại hay không)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sự cố")
    return incident


async def _wait_seconds(session: AsyncSession, window: timedelta, limit: int, *where: Any) -> int | None:
    """Số giây phải đợi cho tới khi dòng cũ nhất trong cửa sổ trôi ra ngoài, nếu đã đủ `limit` dòng; ngược lại None."""
    row = (
        await session.execute(
            select(
                func.count(),
                func.extract("epoch", func.min(Verification.at) + window - func.now()),
            ).where(*where, Verification.at > func.now() - window)
        )
    ).one()
    if row[0] < limit:
        return None
    return max(1, int(row[1] or 1))


async def _check_quota(session: AsyncSession, actor: Actor) -> None:
    """Gọi SAU khi giữ khóa theo người gọi và gia đình. Vượt mức ⇒ 429 + Retry-After (lớn nhất trong các mức vượt)."""
    mine = Verification.actor_id == actor.actor_id
    family = (Verification.family_id == actor.family_id, Verification.actor != "system")
    waits = [
        await _wait_seconds(session, DAY, FAMILY_PER_DAY, *family),
        await _wait_seconds(session, MONTH, FAMILY_PER_MONTH, *family),
    ]
    if actor.kind == "device":
        waits.append(await _wait_seconds(session, HOUR, DEVICE_PER_HOUR, mine))
        waits.append(await _wait_seconds(session, DAY, DEVICE_PER_DAY, mine))
        waits.append(await _wait_seconds(session, MONTH, DEVICE_PER_MONTH, mine))
    else:
        waits.append(await _wait_seconds(session, HOUR, GUARDIAN_PER_HOUR, mine))
        waits.append(await _wait_seconds(session, MONTH, GUARDIAN_PER_MONTH, mine))
    exceeded = [w for w in waits if w is not None]
    if exceeded:
        logger.info("lookups: %s vượt hạn mức", actor.kind)
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY, headers={"Retry-After": str(max(exceeded))}
        )


def _invalid_url() -> HTTPException:
    detail = [{"loc": ["body", "url"], "msg": "đường link không hợp lệ", "type": "url_invalid"}]
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)


@router.post(
    "/lookups",
    response_model=LookupResult,
    response_model_exclude_none=True,
    summary="Tra cứu một số điện thoại (đã băm) hoặc một đường link",
    responses={
        401: {"description": "Thiếu hoặc sai token"},
        403: {"description": "Chưa đồng ý mục đích `lookups`"},
        404: {"description": "Sự cố không thuộc gia đình"},
        429: {"description": "Vượt hạn mức tra cứu"},
    },
)
async def post_lookup(
    body: LookupIn, response: Response, actor: Annotated[Actor, Depends(get_lookup_actor)]
) -> LookupResult:
    response.headers["Cache-Control"] = "no-store"
    try:
        async with get_sessionmaker().begin() as session:
            await session.execute(text(f"SET LOCAL lock_timeout = {int(LOCK_TIMEOUT_MS)}"))
            await _require_consent(session, actor)
            incident = await _owned_incident(session, actor, body.incident_id) if body.incident_id else None
            # Một khóa theo GIA ĐÌNH đủ cho cả hạn mức theo người gọi lẫn theo gia đình (mọi người gọi cùng một nhà).
            await _lock(session, f"lookup-family:{actor.family_id}")
            await _check_quota(session, actor)
            try:
                if body.kind == "phone":
                    assert body.h1 is not None and body.last3 is not None  # noqa: S101 - đã kiểm ở LookupIn
                    outcome = await vs.verify_phone(session, body.h1, body.last3)
                else:
                    assert body.url is not None  # noqa: S101
                    outcome = vs.verify_url(body.url)
            except vs.InvalidUrlError:
                raise _invalid_url() from None
            except RuntimeError as exc:  # thiếu pepper: lỗi cấu hình của ta ⇒ 503, không nêu chi tiết
                logger.error("lookups: không băm được chủ thể (%s)", type(exc).__name__)
                raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
            decision = outcome.decision
            verification_id = await vs.record(
                session,
                family_id=actor.family_id,
                incident_id=incident.id if incident else None,
                actor=actor.kind,
                actor_id=actor.actor_id,
                via=body.via,
                outcome=outcome,
            )
            assert verification_id is not None  # noqa: S101 - `via` typed/qr không có ràng buộc UNIQUE
            level: str | None = None
            if incident is not None:
                if decision.floor is not None:
                    incident = await IncidentService.raise_level(
                        session, incident.id, decision.floor, f"lookup_{decision.code}"
                    )
                level = incident.level
                if actor.kind == "device" and decision.verdict == "dangerous" and incident.state in GUARDIAN_DECIDABLE:
                    await enqueue(
                        session,
                        "graph_resume",
                        {
                            "thread_id": str(incident.id),
                            "expect": "await_guardian",
                            "value": {"evidence": str(verification_id)},
                        },
                        key=f"{incident.id}:evidence:{verification_id}",
                    )
    except OperationalError as exc:
        if not isinstance(exc.orig, LockNotAvailable):
            raise
        logger.warning("lookups: chờ khóa quá hạn")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=BUSY, headers={"Retry-After": "2"}) from None
    logger.info("lookups: kind=%s verdict=%s actor=%s", decision.kind, decision.verdict, actor.kind)
    return LookupResult(**vs.result_payload(verification_id, decision, level))


# --- GET /v1/threat-list (FR-009) --------------------------------------------------------------------------------


class ThreatListOut(BaseModel):
    version: str
    bucket_bits: int
    count: int
    buckets_b64: str
    generated_at: datetime


def _threat_list_wait(device_id: UUID, now: float) -> int | None:
    if device_id not in _threat_list_hits and len(_threat_list_hits) >= MAX_TRACKED_DEVICES:  # bộ nhớ có trần
        for key in [k for k, w in _threat_list_hits.items() if not w or now - w[-1] >= THREAT_LIST_WINDOW_S]:
            del _threat_list_hits[key]
    if device_id not in _threat_list_hits and len(_threat_list_hits) >= MAX_TRACKED_DEVICES:
        del _threat_list_hits[next(iter(_threat_list_hits))]
    window = _threat_list_hits.setdefault(device_id, deque())
    while window and now - window[0] >= THREAT_LIST_WINDOW_S:
        window.popleft()
    if len(window) >= THREAT_LIST_PER_DAY:
        return max(1, int(THREAT_LIST_WINDOW_S - (now - window[0])))
    window.append(now)
    return None


def _threat_list_refund(device_id: UUID) -> None:
    window = _threat_list_hits.get(device_id)
    if window:
        window.pop()


@router.get(
    "/threat-list",
    response_model=ThreatListOut,
    summary="Ảnh chụp bucket k-ẩn danh của danh sách đe dọa (ADR-011)",
    responses={
        304: {"description": "`since` trùng phiên bản hiện tại: không có thân"},
        401: {"description": "Thiếu hoặc sai token thiết bị"},
        429: {"description": "Quá 24 lần/ngày/thiết bị"},
        503: {"description": "Thiếu/sai khóa dữ liệu hoặc phần lớn `bucket_enc` không giải mã được (không đệm)"},
    },
)
async def get_threat_list(
    claims: Annotated[DeviceClaims, Depends(get_current_device)],
    since: Annotated[str | None, Query(pattern=r"^[0-9a-f]{16}$")] = None,
) -> Response | ThreatListOut:
    wait = _threat_list_wait(claims.device_id, time.monotonic())
    if wait is not None:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY, headers={"Retry-After": str(wait)})
    settings = get_settings()
    try:
        snapshot = await threat_list_service.get_snapshot(get_sessionmaker(), settings.threat_bucket_bits, settings.env)
    except RuntimeError as exc:  # thiếu khóa dữ liệu: lỗi cấu hình của ta
        _threat_list_refund(claims.device_id)  # lỗi phía ta không được tốn lượt trong ngày của máy
        logger.error("threat-list: không giải mã được danh sách (%s)", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    async with get_sessionmaker().begin() as session:  # ops xem được máy nào còn giữ danh sách cũ
        await session.execute(
            update(Device)
            .where(Device.id == claims.device_id, Device.threat_list_version.is_distinct_from(snapshot.version))
            .values(threat_list_version=snapshot.version)
        )
    if since == snapshot.version:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    return ThreatListOut(
        version=snapshot.version,
        bucket_bits=snapshot.bucket_bits,
        count=snapshot.count,
        buckets_b64=base64.b64encode(snapshot.buckets).decode("ascii"),
        generated_at=snapshot.generated_at,
    )
