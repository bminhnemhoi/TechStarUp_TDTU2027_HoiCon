"""Mã tham gia gian trưng bày (spec 050 FR-007): `POST /v1/booth/codes` (console), `POST /v1/booth/join` (khách).

Cùng cổng `HOICON_SIM_ENABLED` với `/v1/sim/*` (tắt ⇒ 404). Mã 6 ký tự không nhầm lẫn, ≤ 10 phút, ≤ 50 khách, thu hồi
khi đặt lại gian; DB chỉ giữ HMAC của mã. Đổi mã lấy phiên người giám hộ demo CHỈ XEM + quyết định (cờ `guest` ở JWT:
route cấu hình/đặt lịch dùng `get_current_full_guardian` nên trả 403). Mã sai/hết hạn/hủy/đầy cùng một 404
`{"detail": "join_code_invalid"}`; thử sai quá ngưỡng ⇒ 429 (kể cả mã đúng, chống dò). Khớp `booth_join.v1.json`.
"""

import hashlib
import hmac
import ipaddress
import logging
import secrets
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from hoicon.api import auth
from hoicon.api.auth import GuardianClaims, get_current_full_guardian, require_same_origin
from hoicon.api.routers.guardian import NO_STORE, _cookie_flags
from hoicon.api.routers.sim import NOT_FOUND, require_sim_enabled
from hoicon.config import get_settings
from hoicon.db.models import BoothJoinCode, Family, RevokedSession
from hoicon.db.session import get_sessionmaker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/booth", tags=["booth"], dependencies=[Depends(require_sim_enabled)])

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # bỏ I, L, O, 0, 1 (dễ nhầm khi đọc trên màn hình gian)
CODE_LEN = 6
CODE_PATTERN = r"^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{6}$"
CODE_TTL = timedelta(minutes=10)
MAX_GUESTS = 50
GUEST_TTL = timedelta(hours=1)
JOIN_INVALID = "join_code_invalid"
TOO_MANY = "Bạn đã thử quá nhiều lần. Vui lòng đợi ít phút rồi thử lại."
WINDOW_S = 600
MAX_FAILURES_PER_CLIENT = 30  # nhiều khách cùng một Wi-Fi gian (NAT) dùng chung một IP
MAX_FAILURES_GLOBAL = 100
MAX_TRACKED_CLIENTS = 4096

_failures: dict[str, deque[float]] = {}
_global_failures: deque[float] = deque()


def reset_limits() -> None:
    _failures.clear()
    _global_failures.clear()


class BoothKeyMissingError(RuntimeError):
    """Ngoài dev chưa đặt `HOICON_BOOTH_CODE_KEY` (đã nêu ở /readyz)."""


def _code_key() -> bytes:
    """Khóa HMAC của mã: khóa riêng; ở dev để trống thì dùng khóa con dẫn xuất từ khóa JWT (không dùng chính nó)."""
    settings = get_settings()
    configured = settings.booth_code_key
    own = configured.get_secret_value() if configured is not None else ""
    if len(own) >= auth.MIN_KEY_LEN:
        return own.encode()
    if settings.is_dev_env:
        return hmac.new(auth._key().encode(), b"hoicon:booth-code-key:v1", hashlib.sha256).digest()
    raise BoothKeyMissingError("HOICON_BOOTH_CODE_KEY thiếu hoặc ngắn")


def code_hash(code: str) -> str:
    """HMAC-SHA256 theo khóa riêng: DB lộ ra cũng không suy được mã (không gian mã nhỏ nên hash trần dò được)."""
    return hmac.new(_code_key(), f"hoicon:booth-join:v1:{code}".encode(), hashlib.sha256).hexdigest()


def _client_key(host: str) -> str:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else host


def _prune(window: deque[float], now: float) -> None:
    while window and now - window[0] >= WINDOW_S:
        window.popleft()


def _locked_for(client: str, now: float) -> int | None:
    _prune(_global_failures, now)
    own = _failures.get(client)
    if own is not None:
        _prune(own, now)
    for window, limit in ((own, MAX_FAILURES_PER_CLIENT), (_global_failures, MAX_FAILURES_GLOBAL)):
        if window is not None and len(window) >= limit:
            return max(1, int(WINDOW_S - (now - window[0])))
    return None


def _record_failure(client: str, now: float) -> None:
    if client not in _failures and len(_failures) >= MAX_TRACKED_CLIENTS:  # bộ nhớ có trần
        for key in [k for k, w in _failures.items() if not w or now - w[-1] >= WINDOW_S]:
            del _failures[key]
    if client in _failures or len(_failures) < MAX_TRACKED_CLIENTS:
        _failures.setdefault(client, deque()).append(now)
    _global_failures.append(now)


class JoinIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Annotated[str, Field(pattern=CODE_PATTERN)]


class CodeOut(BaseModel):
    code: str
    expires_at: datetime
    max_guests: int
    is_demo: Literal[True] = True


class SessionOut(BaseModel):
    family_alias: str
    expires_at: datetime
    is_demo: Literal[True] = True


async def _demo_full(claims: Annotated[GuardianClaims, Depends(get_current_full_guardian)]) -> GuardianClaims:
    async with get_sessionmaker()() as session:
        family = await session.get(Family, claims.family_id)
    if family is None or not family.is_demo:  # gia đình thật ⇒ 404 như `/v1/sim/*`
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return claims


@router.post(
    "/codes",
    response_model=CodeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_same_origin)],
    summary="Console tạo mã tham gia gian (spec 050 FR-007)",
)
async def create_code(claims: Annotated[GuardianClaims, Depends(_demo_full)], response: Response) -> CodeOut:
    response.headers.update(NO_STORE)
    expires = datetime.now(UTC) + CODE_TTL
    for _ in range(5):  # trùng băm (hiếm) ⇒ sinh mã khác
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
        try:
            digest = code_hash(code)
        except BoothKeyMissingError:
            logger.error("booth: chưa cấu hình HOICON_BOOTH_CODE_KEY")
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
        try:
            async with get_sessionmaker().begin() as session:
                await session.execute(
                    insert(BoothJoinCode).values(
                        family_id=claims.family_id,
                        created_by=claims.member_id,
                        code_hash=digest,
                        expires_at=expires,
                        max_guests=MAX_GUESTS,
                    )
                )
            return CodeOut(code=code, expires_at=expires, max_guests=MAX_GUESTS)
        except IntegrityError:
            continue
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Hệ thống đang bận, vui lòng thử lại.")


@router.post(
    "/join",
    response_model=SessionOut,
    dependencies=[Depends(require_same_origin)],
    summary="Khách đổi mã lấy phiên xem gian (spec 050 FR-007)",
    responses={
        404: {"description": "`join_code_invalid` (mã sai/hết hạn/hủy/đầy)"},
        429: {"description": "Thử sai quá nhiều"},
    },
)
async def join(body: JoinIn, request: Request, response: Response) -> SessionOut:
    response.headers.update(NO_STORE)
    client = _client_key(request.client.host if request.client else "unknown")
    now = time.monotonic()
    wait = _locked_for(client, now)
    if wait is not None:
        logger.info("booth join: quá nhiều lần thử sai, tạm khóa")
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY, headers={"Retry-After": str(wait)})
    try:
        auth.ensure_configured()  # thiếu khóa ký là lỗi của ta, không tính vào lượt đoán
    except auth.DeviceAuthNotConfiguredError:
        logger.error("booth join: chưa cấu hình khóa ký JWT")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    try:
        digest = code_hash(body.code)
    except BoothKeyMissingError:
        logger.error("booth join: chưa cấu hình HOICON_BOOTH_CODE_KEY")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    stamp = datetime.now(UTC)
    # Khách còn phiên sống của CHÍNH mã này bấm vào lại: nhận lại đúng phiên đó (không sinh phiên mới, không kéo dài
    # hạn) và không tính thêm một khách. Phiên đã đăng xuất (jti bị thu hồi) thì không được miễn.
    live = _live_guest(request)
    room = BoothJoinCode.guests < BoothJoinCode.max_guests
    async with get_sessionmaker().begin() as session:
        if live is not None and live[1].jti is not None and await session.get(RevokedSession, live[1].jti):
            live = None
        own = live[1].booth_code if live is not None else None
        # Một câu lệnh nguyên tử: kiểm hạn/hủy/số khách và tăng bộ đếm (không vượt 50 dù nhiều khách vào cùng lúc).
        row = (
            await session.execute(
                update(BoothJoinCode)
                .where(
                    BoothJoinCode.code_hash == digest,
                    BoothJoinCode.revoked_at.is_(None),
                    BoothJoinCode.expires_at > stamp,
                    or_(room, BoothJoinCode.id == own) if own else room,
                )
                .values(guests=BoothJoinCode.guests + (case((BoothJoinCode.id == own, 0), else_=1) if own else 1))
                .returning(BoothJoinCode.id, BoothJoinCode.family_id, BoothJoinCode.created_by)
            )
        ).one_or_none()
        family = await session.get(Family, row.family_id) if row is not None else None
        # Mã từng tồn tại nhưng đã hết hạn/hủy/đầy (QR cũ dán sẵn) KHÔNG tính là đoán mò: không khóa cả Wi-Fi gian.
        known = row is not None or await session.scalar(
            select(BoothJoinCode.id).where(BoothJoinCode.code_hash == digest)
        )
    if row is None or family is None or not family.is_demo:
        if not known:
            _record_failure(client, now)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=JOIN_INVALID)
    if live is not None and own == row.id and live[1].expires_at is not None:
        token, expires = live[0], live[1].expires_at  # vào lại: giữ nguyên phiên cũ
        max_age = max(1, int((expires - stamp).total_seconds()))
    else:
        token = auth.issue_guardian_access_token(
            row.created_by, row.family_id, now=stamp, ttl=GUEST_TTL, guest=True, booth_code=row.id
        )
        expires, max_age = (stamp + GUEST_TTL).replace(microsecond=0), int(GUEST_TTL.total_seconds())  # JWT: giây
    response.set_cookie(auth.GUARDIAN_COOKIE, token, max_age=max_age, **_cookie_flags())  # type: ignore[arg-type]
    logger.info("booth join: khách vào gian (đã cấp phiên xem)")
    return SessionOut(family_alias=family.display_name[:40], expires_at=expires)


def _live_guest(request: Request) -> tuple[str, GuardianClaims] | None:
    token = request.cookies.get(auth.GUARDIAN_COOKIE)
    if not token:
        return None
    try:
        claims = auth.decode_guardian_access_token(token)
    except (auth.DeviceTokenError, auth.DeviceAuthNotConfiguredError):
        return None
    return (token, claims) if claims.guest and claims.booth_code is not None else None


async def revoke_all_codes(session) -> None:
    await session.execute(
        update(BoothJoinCode).where(BoothJoinCode.revoked_at.is_(None)).values(revoked_at=datetime.now(UTC))
    )
