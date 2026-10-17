"""`POST /v1/pair` (spec 020, FR-003, plan T3): đổi mã ghép 6 số lấy thiết bị + token.

Cùng một giao dịch: khóa dòng mã (`FOR UPDATE`), khóa dòng gia đình, tạo `devices`, đánh dấu `used_at`. Hai máy cùng
nhập một mã thì chỉ một máy thắng; mã không bị tiêu thụ nếu giao dịch hỏng. Mã sai/hết hạn/đã dùng trả cùng một câu 400.

Chống dò mã (10⁶ khả năng, mã sống ≤ 15 phút): đếm lần thử SAI trong bộ nhớ theo nguồn gọi (IPv6 gộp theo /64) và toàn
cục, quá ngưỡng ⇒ 429 kể cả khi mã đúng. Mỗi lần thử GIỮ CHỖ ngay khi vào (trước khi chạm DB) và trả lại nếu ghép được:
đếm sau khi có kết quả thì một loạt yêu cầu đồng thời đều lọt qua ngưỡng. Ngưỡng toàn cục là đánh đổi có chủ đích: kẻ lạ
có thể làm nghẽn việc ghép đôi tối đa 15 phút/lần (không mất dữ liệu), đổi lại không thể dò mã nhanh. Địa chỉ nguồn là
`request.client.host` do uvicorn đặt: sau reverse proxy cùng máy, cấu hình `--forwarded-allow-ips`/`--no-proxy-headers`
của uvicorn quyết định đó là IP thật hay IP proxy (nếu là IP proxy thì chỉ ngưỡng toàn cục có tác dụng). Đếm trong bộ
nhớ ⇒ chỉ đúng với một tiến trình (ADR-002).
"""

import ipaddress
import logging
import time
from collections import deque
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from hoicon.api import auth
from hoicon.db.ids import new_id
from hoicon.db.models import Device, Family, Member, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_pairing_code, mask_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["pairing"])

WINDOW_S = 15 * 60  # bằng hạn của mã
MAX_FAILURES_PER_CLIENT = 10
MAX_FAILURES_GLOBAL = 60
MAX_TRACKED_CLIENTS = 4096
BAD_CODE = "Mã ghép đôi không tồn tại hoặc đã hết hạn"
TOO_MANY = "Bạn đã thử quá nhiều lần. Vui lòng đợi ít phút rồi thử lại."

_failures: dict[str, deque[float]] = {}
_global_failures: deque[float] = deque()


def reset_limits() -> None:
    _failures.clear()
    _global_failures.clear()


def _prune(window: deque[float], now: float) -> None:
    while window and now - window[0] >= WINDOW_S:
        window.popleft()


def _retry_after(client: str, now: float) -> int | None:
    """Số giây phải đợi nếu nguồn này hoặc toàn hệ thống đã quá ngưỡng thử sai; None nếu được thử."""
    _prune(_global_failures, now)
    own = _failures.get(client)
    if own is not None:
        _prune(own, now)
    for window, limit in ((own, MAX_FAILURES_PER_CLIENT), (_global_failures, MAX_FAILURES_GLOBAL)):
        if window is not None and len(window) >= limit:
            return max(1, int(WINDOW_S - (now - window[0])))
    return None


def _client_key(host: str) -> str:
    """IPv6: cả /64 là một nguồn (một thuê bao thường có nguyên dải /64 để đổi địa chỉ)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else host


def _release(client: str, now: float) -> None:
    """Trả lại chỗ đã giữ (ghép thành công hoặc lỗi hạ tầng không phải do đoán mã)."""
    for window in (_failures.get(client), _global_failures):
        if window is not None and now in window:
            window.remove(now)


def _record_failure(client: str, now: float) -> None:
    if client not in _failures and len(_failures) >= MAX_TRACKED_CLIENTS:  # bộ nhớ có trần: bỏ các nguồn đã hết cửa sổ
        for key in [k for k, w in _failures.items() if not w or now - w[-1] >= WINDOW_S]:
            del _failures[key]
        if (
            len(_failures) >= MAX_TRACKED_CLIENTS
        ):  # vẫn đầy (bị tấn công từ rất nhiều nguồn): chỉ ngưỡng toàn cục còn tác dụng
            _global_failures.append(now)
            return
    _failures.setdefault(client, deque()).append(now)
    _global_failures.append(now)


class PairRequest(BaseModel):
    """Khớp `docs/schemas/pair_request.v1.json`."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(pattern=r"^[0-9]{6}$")
    app_version: str = Field(pattern=r"^[0-9A-Za-z._+-]{1,32}$")
    rules_version: str = Field(pattern=r"^[0-9A-Za-z._+-]{1,32}$")
    platform: Literal["android", "ios", "web"]
    device_label: str | None = Field(default=None, max_length=64)


class PairResponse(BaseModel):
    """Khớp `docs/schemas/pair_response.v1.json`."""

    device_id: str
    family_id: str
    member_id: str
    family_name: str
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — loại token, không phải mật khẩu
    expires_in: int


@router.post("/pair", response_model=PairResponse)
async def pair(payload: PairRequest, request: Request) -> PairResponse:
    client = _client_key(request.client.host if request.client else "unknown")
    now = time.monotonic()
    wait = _retry_after(client, now)
    if wait is not None:
        logger.info("ghép đôi: quá nhiều lần thử sai, tạm khóa")  # info: kẻ lạ gửi bao nhiêu cũng không ngập log
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail=TOO_MANY, headers={"Retry-After": str(wait)})
    try:
        auth.ensure_configured()  # trước khi tiêu thụ mã: thiếu khóa ký thì mã còn nguyên cho lần sau
    except auth.DeviceAuthNotConfiguredError:
        logger.error("ghép đôi: HOICON_DEVICE_JWT_SECRET thiếu hoặc quá ngắn")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Dịch vụ chưa sẵn sàng") from None

    refresh_token, refresh_hash = auth.new_refresh_token()
    _record_failure(client, now)  # giữ chỗ TRƯỚC khi chạm DB (xem docstring); trả lại nếu ghép được
    try:
        redeemed = await _redeem(payload, refresh_hash)
    except BaseException:  # lỗi hạ tầng/hủy yêu cầu không phải do đoán mã: không tính vào ngưỡng
        _release(client, now)
        raise
    if redeemed is None:
        logger.info("ghép đôi: mã không dùng được")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=BAD_CODE)
    _release(client, now)
    device_id, family_id, member_id, family_name = redeemed
    logger.info("ghép đôi thành công: thiết bị %s", device_id)
    return PairResponse(
        device_id=str(device_id),
        family_id=str(family_id),
        member_id=str(member_id),
        family_name=family_name,
        access_token=auth.issue_access_token(device_id, family_id, member_id),
        refresh_token=refresh_token,
        expires_in=auth.ACCESS_TTL_S,
    )


async def _redeem(payload: PairRequest, refresh_hash: str) -> tuple[UUID, UUID, UUID, str] | None:
    """Một giao dịch: khóa mã, khóa gia đình, tạo thiết bị, đánh dấu mã đã dùng. ⇒ None nếu mã không dùng được."""
    async with get_sessionmaker().begin() as session:
        code = (
            await session.scalars(
                select(PairingCode)
                .where(
                    PairingCode.code_hash == hmac_pairing_code(payload.code),
                    PairingCode.used_at.is_(None),
                    PairingCode.expires_at > func.now(),
                )
                .with_for_update()
            )
        ).one_or_none()
        if code is None:
            return None
        # Khóa gia đình: hai mã của cùng một gia đình xử lý song song không được tạo hai người được bảo vệ.
        family = (await session.scalars(select(Family).where(Family.id == code.family_id).with_for_update())).one()
        member = (
            await session.scalars(
                select(Member)
                .where(Member.family_id == family.id, Member.role == "protected")
                .order_by(Member.created_at, Member.id)
                .limit(1)
            )
        ).first()
        if member is None:
            member = Member(id=new_id(), family_id=family.id, role="protected")
            session.add(member)
            await session.flush()  # không có relationship() nên ORM không tự sắp thứ tự INSERT theo FK
        device = Device(
            id=new_id(),
            family_id=family.id,
            member_id=member.id,
            platform=payload.platform,
            # Nhãn do người dùng gõ có thể chứa số điện thoại/tên: che trước khi lưu (luật 1, DATA-MODEL "không PII").
            label=mask_text(payload.device_label) if payload.device_label else None,
            app_version=payload.app_version,
            rules_version=payload.rules_version,
            device_secret_hash=refresh_hash,
        )
        session.add(device)
        code.used_at = func.now()
        return device.id, family.id, member.id, family.display_name
