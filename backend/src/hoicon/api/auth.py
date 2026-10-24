"""Xác thực thiết bị (spec 020, FR-004, plan T2): JWT HS256 sống 30 ngày + refresh token chỉ lưu băm.

`access_token` mang `device_id` (sub), `family_id`, `member_id`, `role = "protected"`. Máy người cao tuổi chạy nền liên
tục nên không bắt đăng nhập lại hằng ngày; đổi lại, `get_current_device` luôn đối chiếu DB (thiết bị còn tồn tại, chưa
`revoked_at`) nên thu hồi có hiệu lực ngay. `refresh_token` là 32 byte ngẫu nhiên, DB chỉ giữ SHA-256
(`devices.device_secret_hash`).
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from hoicon.config import get_settings
from hoicon.db.models import BoothJoinCode, Device, Member, RevokedSession
from hoicon.db.session import get_sessionmaker

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ISSUER = "hoicon"
AUDIENCE = "hoicon-device"
GUARDIAN_AUDIENCE = "hoicon-guardian"
ROLE = "protected"
GUARDIAN_ROLE = "guardian"
ACCESS_TTL = timedelta(days=30)
GUARDIAN_WEB_TTL = timedelta(days=7)  # phiên web của người giám hộ (spec 027); thiết bị vẫn 30 ngày
GUARDIAN_COOKIE = "hc_guardian"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
ACCESS_TTL_S = int(ACCESS_TTL.total_seconds())
MIN_KEY_LEN = 32  # ký tự; HS256 cần khóa ≥ 256 bit

_bearer = HTTPBearer(auto_error=False)


class DeviceTokenError(Exception):
    """Token thiết bị sai, hết hạn hoặc thiếu trường bắt buộc (không nêu lý do chi tiết ra ngoài)."""


class DeviceAuthNotConfiguredError(RuntimeError):
    """Thiếu `HOICON_DEVICE_JWT_SECRET` hoặc quá ngắn: lỗi của ta, không phải của người gọi."""


@dataclass(frozen=True)
class DeviceClaims:
    device_id: UUID
    family_id: UUID
    member_id: UUID


def _key() -> str:
    secret = get_settings().device_jwt_secret
    value = secret.get_secret_value() if secret is not None else ""
    if len(value) < MIN_KEY_LEN:
        raise DeviceAuthNotConfiguredError(f"HOICON_DEVICE_JWT_SECRET thiếu hoặc ngắn hơn {MIN_KEY_LEN} ký tự")
    return value


def ensure_configured() -> None:
    """Ném `DeviceAuthNotConfiguredError` nếu chưa ký được token; gọi TRƯỚC khi tiêu thụ mã ghép."""
    try:
        issue_access_token(UUID(int=0), UUID(int=0), UUID(int=0))  # ký thử: khóa sai định dạng cũng bị bắt ở đây
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise DeviceAuthNotConfiguredError(f"không ký được token thử ({type(exc).__name__})") from None


def issue_access_token(device_id: UUID, family_id: UUID, member_id: UUID, *, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(device_id),
        "family_id": str(family_id),
        "member_id": str(member_id),
        "role": ROLE,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": issued,
        "exp": issued + ACCESS_TTL,
    }
    return jwt.encode(payload, _key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> DeviceClaims:
    key = _key()  # thiếu khóa là lỗi cấu hình, không bị nuốt thành "token sai"
    try:
        raw = jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],  # cố định: chặn `alg: none` và nhầm thuật toán
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
        if raw.get("role") != ROLE:
            raise DeviceTokenError("role")
        return DeviceClaims(UUID(raw["sub"]), UUID(raw["family_id"]), UUID(raw["member_id"]))
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise DeviceTokenError(type(exc).__name__) from None


def new_refresh_token() -> tuple[str, str]:
    """⇒ (token gửi cho thiết bị, SHA-256 hex để lưu). 256 bit ngẫu nhiên nên băm không cần muối."""
    token = secrets.token_urlsafe(32)
    return token, hashlib.sha256(token.encode()).hexdigest()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Chưa xác thực thiết bị",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_device(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> DeviceClaims:
    """Dependency cho mọi route của thiết bị: token hợp lệ VÀ thiết bị còn hiệu lực trong DB."""
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_access_token(credentials.credentials)
    except DeviceAuthNotConfiguredError:
        logger.error("xác thực thiết bị: HOICON_DEVICE_JWT_SECRET thiếu hoặc quá ngắn ⇒ từ chối mọi token")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    except DeviceTokenError:
        raise _unauthorized() from None
    async with get_sessionmaker()() as session:
        alive = await session.scalar(
            select(Device.id).where(
                Device.id == claims.device_id,
                Device.family_id == claims.family_id,
                Device.member_id == claims.member_id,
                Device.revoked_at.is_(None),
            )
        )
    if alive is None:
        raise _unauthorized()
    return claims


@dataclass(frozen=True)
class GuardianClaims:
    member_id: UUID
    family_id: UUID
    role: str = GUARDIAN_ROLE
    expires_at: datetime | None = None
    booth_code: UUID | None = None  # mã tham gia đã cấp phiên khách (đặt lại gian thu hồi mã ⇒ phiên chết ngay)
    guest: bool = False  # phiên khách gian trưng bày (spec 050 FR-007): chỉ xem + quyết định, không cấu hình/đặt lịch
    jti: str | None = None  # mã phiên (token cũ phát trước 037 T018 không có ⇒ không thu hồi riêng được)


def issue_guardian_access_token(
    member_id: UUID,
    family_id: UUID,
    *,
    now: datetime | None = None,
    ttl: timedelta = ACCESS_TTL,
    guest: bool = False,
    booth_code: UUID | None = None,
) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": str(member_id),
        "family_id": str(family_id),
        "role": GUARDIAN_ROLE,
        "iss": ISSUER,
        "aud": GUARDIAN_AUDIENCE,
        "iat": issued,
        "exp": issued + ttl,
        "jti": uuid4().hex,
        **({"guest": True, "bc": str(booth_code)} if guest and booth_code else {"guest": True} if guest else {}),
    }
    return jwt.encode(payload, _key(), algorithm=ALGORITHM)


def decode_guardian_access_token(token: str) -> GuardianClaims:
    key = _key()
    try:
        raw = jwt.decode(
            token,
            key,
            algorithms=[ALGORITHM],
            audience=GUARDIAN_AUDIENCE,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
        if raw.get("role") != GUARDIAN_ROLE:
            raise DeviceTokenError("role")
        return GuardianClaims(
            UUID(raw["sub"]),
            UUID(raw["family_id"]),
            expires_at=datetime.fromtimestamp(raw["exp"], UTC),
            booth_code=UUID(raw["bc"]) if isinstance(raw.get("bc"), str) else None,
            guest=raw.get("guest") is True,
            jti=raw["jti"] if isinstance(raw.get("jti"), str) else None,
        )
    except (jwt.PyJWTError, KeyError, ValueError, TypeError) as exc:
        raise DeviceTokenError(type(exc).__name__) from None


def _unauthorized_guardian() -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Chưa xác thực người giám hộ",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_same_origin(request: Request) -> None:
    """Chống CSRF cho lệnh ghi xác thực bằng cookie (spec 027, FR-003): `Origin` thuộc danh sách cho phép, hoặc trình
    duyệt khẳng định `Sec-Fetch-Site: same-origin`. `SameSite=Strict` là lớp thứ nhất; đây là lớp phòng thủ chiều sâu
    cho trình duyệt cũ bỏ qua `SameSite`. Lệnh đọc (GET/HEAD/OPTIONS) không cần."""
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin", "").strip().rstrip("/").lower()
    same_origin = request.headers.get("sec-fetch-site", "").strip().lower() == "same-origin"
    if not ((origin and origin in get_settings().allowed_web_origins) or same_origin):
        logger.warning("CSRF: từ chối %s %s không có bằng chứng cùng nguồn", request.method, request.url.path)
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Yêu cầu không đến từ trang web của HỏiCon")


async def get_current_guardian(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    cookie: Annotated[str | None, Cookie(alias=GUARDIAN_COOKIE)] = None,
) -> GuardianClaims:
    """Dependency xác thực người giám hộ: token hợp lệ VÀ thành viên tồn tại với role='guardian'.

    Nhận `Authorization: Bearer` (ưu tiên, không rơi về cookie khi Bearer sai) hoặc cookie `hc_guardian` (web, 027).
    Xác thực bằng cookie mà là lệnh ghi ⇒ phải qua `require_same_origin`."""
    via_cookie = credentials is None
    token = cookie if via_cookie else credentials.credentials
    if not token:
        raise _unauthorized_guardian()
    if via_cookie:
        require_same_origin(request)
    try:
        claims = decode_guardian_access_token(token)
    except DeviceAuthNotConfiguredError:
        logger.error("xác thực người giám hộ: HOICON_DEVICE_JWT_SECRET thiếu hoặc quá ngắn")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None
    except DeviceTokenError:
        raise _unauthorized_guardian() from None
    async with get_sessionmaker()() as session:
        member = await session.get(Member, claims.member_id)
        revoked = claims.jti is not None and await session.get(RevokedSession, claims.jti) is not None
        if (
            claims.guest
        ):  # phiên khách gian: chỉ sống khi cổng mô phỏng bật VÀ mã đã cấp phiên chưa bị thu hồi (đặt lại)
            code = await session.get(BoothJoinCode, claims.booth_code) if claims.booth_code else None
            revoked = revoked or not get_settings().sim_enabled or code is None or code.revoked_at is not None
    # `deleted_at`: thành viên đã bị ẩn danh sau yêu cầu xóa dữ liệu (spec 034) ⇒ token cũ hết hiệu lực ngay.
    if (
        member is None
        or member.family_id != claims.family_id
        or member.role != GUARDIAN_ROLE
        or member.deleted_at is not None
        or revoked  # đã đăng xuất (037 T018): bản sao token/cookie bị lấy cắp cũng hết tác dụng
    ):
        raise _unauthorized_guardian()
    return claims


async def get_current_full_guardian(
    claims: Annotated[GuardianClaims, Depends(get_current_guardian)],
) -> GuardianClaims:
    """Như `get_current_guardian` nhưng từ chối phiên KHÁCH gian trưng bày (403): khách chỉ xem + quyết định."""
    if claims.guest:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Phiên khách không dùng được chức năng này")
    return claims
