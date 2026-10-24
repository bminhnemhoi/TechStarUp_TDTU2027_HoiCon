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
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from hoicon.api import auth
from hoicon.api.auth import GuardianClaims, get_current_full_guardian, require_same_origin
from hoicon.api.routers.guardian import NO_STORE, _cookie_flags
from hoicon.api.routers.sim import NOT_FOUND, require_sim_enabled
from hoicon.db.models import BoothJoinCode, Family
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
MAX_FAILURES_PER_CLIENT = 10
MAX_FAILURES_GLOBAL = 100
MAX_TRACKED_CLIENTS = 4096

_failures: dict[str, deque[float]] = {}
_global_failures: deque[float] = deque()


def reset_limits() -> None:
    _failures.clear()
    _global_failures.clear()


def code_hash(code: str) -> str:
    """HMAC-SHA256 theo khóa dịch vụ: DB lộ ra cũng không suy được mã (không gian mã nhỏ nên hash trần dò được)."""
    return hmac.new(auth._key().encode(), f"hoicon:booth-join:v1:{code}".encode(), hashlib.sha256).hexdigest()


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
            async with get_sessionmaker().begin() as session:
                await session.execute(
                    insert(BoothJoinCode).values(
                        family_id=claims.family_id,
                        created_by=claims.member_id,
                        code_hash=code_hash(code),
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
    stamp = datetime.now(UTC)
    async with get_sessionmaker().begin() as session:
        # Một câu lệnh nguyên tử: kiểm hạn/hủy/số khách và tăng bộ đếm (không vượt 50 dù nhiều khách vào cùng lúc).
        row = (
            await session.execute(
                update(BoothJoinCode)
                .where(
                    BoothJoinCode.code_hash == code_hash(body.code),
                    BoothJoinCode.revoked_at.is_(None),
                    BoothJoinCode.expires_at > stamp,
                    BoothJoinCode.guests < BoothJoinCode.max_guests,
                )
                .values(guests=BoothJoinCode.guests + 1)
                .returning(BoothJoinCode.family_id, BoothJoinCode.created_by)
            )
        ).one_or_none()
        family = await session.get(Family, row.family_id) if row is not None else None
    if row is None or family is None or not family.is_demo:
        _record_failure(client, now)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=JOIN_INVALID)
    token = auth.issue_guardian_access_token(row.created_by, row.family_id, now=stamp, ttl=GUEST_TTL, guest=True)
    max_age = int(GUEST_TTL.total_seconds())
    response.set_cookie(auth.GUARDIAN_COOKIE, token, max_age=max_age, **_cookie_flags())  # type: ignore[arg-type]
    logger.info("booth join: khách vào gian (đã cấp phiên xem)")
    return SessionOut(family_alias=family.display_name[:40], expires_at=stamp + GUEST_TTL)


async def revoke_all_codes(session) -> None:
    await session.execute(
        update(BoothJoinCode).where(BoothJoinCode.revoked_at.is_(None)).values(revoked_at=datetime.now(UTC))
    )
