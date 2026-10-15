"""`ActionTokenService` — Quản lý vòng đời Action Token một lần (`/a/[token]`, spec 023, P2-07).

Nguyên tắc bảo mật:
1. Chỉ lưu SHA-256 hash 64-hex của token vào bảng `action_tokens.token_hash` (ADR-006, ADR-010).
2. Token ngẫu nhiên (32 bytes entropy URL-safe) chỉ tồn tại trong bộ nhớ lúc tạo và trong liên kết gửi đi.
3. Token có thời hạn (`expires_at`, mặc định 24h) và sử dụng đúng một lần (`used_at`).
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.db.models import ActionToken, Device, Incident, Member
from hoicon.services.incident_service import GUARDIAN_DECIDABLE

VALID_SCOPES: Final = frozenset({"incident_decision", "guardian_view", "drill_debrief"})
DEFAULT_TTL: Final = timedelta(hours=24)


class ActionTokenError(Exception):
    """Gốc của lỗi Action Token."""


class InvalidTokenError(ActionTokenError):
    """Token sai định dạng."""


class TokenNotFoundError(ActionTokenError):
    """Không tìm thấy token trong CSDL."""


class TokenExpiredError(ActionTokenError):
    """Token đã hết hạn."""


class TokenUsedError(ActionTokenError):
    """Token đã được sử dụng trước đó."""


def hash_token(raw_token: str) -> str:
    """Băm SHA-256 cho token ngẫu nhiên ra chuỗi 64 ký tự hex thường."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class ActionTokenService:
    @staticmethod
    def generate_raw_token() -> str:
        """Sinh chuỗi token ngẫu nhiên an toàn (32 bytes URL-safe, ~43 ký tự)."""
        return secrets.token_urlsafe(32)

    @classmethod
    async def create_token(
        cls,
        session: AsyncSession,
        *,
        incident_id: UUID,
        member_id: UUID,
        scope: str = "incident_decision",
        ttl: timedelta = DEFAULT_TTL,
    ) -> tuple[ActionToken, str]:
        """Tạo ActionToken mới. Trả về (bản ghi CSDL, raw_token để gửi người dùng).

        Ghi chú: Service KHÔNG tự commit, người gọi sở hữu giao dịch.
        """
        if scope not in VALID_SCOPES:
            raise ValueError(f"Scope không hợp lệ: {scope} (phải là một trong {VALID_SCOPES})")

        raw_token = cls.generate_raw_token()
        token_hash = hash_token(raw_token)
        now = datetime.now(UTC)
        expires_at = now + ttl

        record = ActionToken(
            incident_id=incident_id,
            member_id=member_id,
            token_hash=token_hash,
            scope=scope,
            expires_at=expires_at,
            used_at=None,
        )
        session.add(record)
        await session.flush()
        return record, raw_token

    @staticmethod
    async def get_token_record(
        session: AsyncSession,
        raw_token: str,
        *,
        lock: bool = False,
    ) -> ActionToken | None:
        """Tra cứu bản ghi ActionToken theo raw token mà không kiểm tra hạn/đã dùng.

        `lock=True` khóa dòng tới hết giao dịch: hai lần bấm đồng thời không cùng lọt qua kiểm tra `used_at`.
        """
        if not raw_token or len(raw_token) < 16:
            return None
        token_hash = hash_token(raw_token)
        stmt = select(ActionToken).where(ActionToken.token_hash == token_hash)
        if lock:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).one_or_none()

    @classmethod
    async def verify_token(
        cls,
        session: AsyncSession,
        raw_token: str,
        *,
        expected_scope: str = "incident_decision",
        lock: bool = False,
    ) -> ActionToken:
        """Kiểm tra token có hợp lệ để thực hiện hành động không.

        Nếu hết hạn hay đã dùng thì ném ngoại lệ tương ứng.
        """
        record = await cls.get_token_record(session, raw_token, lock=lock)
        if record is None:
            raise TokenNotFoundError("Không tìm thấy liên kết hành động hoặc liên kết không hợp lệ.")

        if record.scope != expected_scope:
            raise InvalidTokenError(f"Phạm vi liên kết không khớp (yêu cầu {expected_scope}).")

        now = datetime.now(UTC)
        if record.expires_at < now:
            raise TokenExpiredError("Liên kết hành động này đã hết hạn (quá 24 giờ).")

        if record.used_at is not None:
            raise TokenUsedError("Liên kết hành động này đã được sử dụng trước đó.")

        return record

    @classmethod
    async def consume_token(
        cls,
        session: AsyncSession,
        raw_token: str,
        *,
        expected_scope: str = "incident_decision",
    ) -> ActionToken:
        """Xác thực và đánh dấu đã sử dụng token (ghi `used_at = now()`).

        Thực thi trong cùng giao dịch với chuyển đổi trạng thái sự cố.
        """
        record = await cls.verify_token(session, raw_token, expected_scope=expected_scope, lock=True)
        record.used_at = datetime.now(UTC)
        await session.flush()
        return record

    @classmethod
    async def get_action_view_data(
        cls,
        session: AsyncSession,
        raw_token: str,
    ) -> dict | None:
        """Lấy toàn bộ dữ liệu cho màn hình `/a/[token]` (tuân thủ schema action_view.v1.json).

        Trả None nếu token hoàn toàn không tồn tại trong CSDL.
        """
        record = await cls.get_token_record(session, raw_token)
        if record is None:
            return None

        # Lấy thông tin incident liên kết
        incident = await session.get(Incident, record.incident_id) if record.incident_id else None
        if incident is None:
            return None

        now = datetime.now(UTC)
        is_expired = record.expires_at < now
        is_used = record.used_at is not None
        # Sự cố đã được xử lý qua kênh khác (trả lời Zalo, JWT) ⇒ liên kết hết tác dụng dù chưa dùng.
        token_valid = not is_expired and not is_used and incident.state in GUARDIAN_DECIDABLE

        # Lấy thông tin thành viên được bảo vệ và thiết bị
        protected_member = await session.get(Member, incident.member_id)
        device = await session.get(Device, incident.device_id) if incident.device_id else None

        member_label = "Người thân"
        if protected_member:
            # Ưu tiên bí danh xưng hô (ví dụ "Mẹ", "Bố" - CLAUDE.md luật 1)
            member_label = protected_member.alias or ("Bố/Mẹ" if protected_member.role == "protected" else "Thành viên")

        device_label = None
        if device:
            device_label = device.label or "Thiết bị di động"

        # Soạn tóm tắt rủi ro dễ hiểu
        if incident.is_drill:
            summary = "Diễn tập tình huống cảnh giác lừa đảo cùng gia đình."
        elif incident.level in ("critical", "high"):
            summary = "Phát hiện cuộc gọi lạ kết hợp mở ứng dụng ngân hàng hoặc công cụ điều khiển từ xa."
        else:
            summary = "Phát hiện dấu hiệu bất thường trên thiết bị được bảo vệ."

        return {
            "token_valid": token_valid,
            "scope": record.scope,
            "expires_at": record.expires_at.isoformat().replace("+00:00", "Z"),
            "used_at": record.used_at.isoformat().replace("+00:00", "Z") if record.used_at else None,
            "incident": {
                "id": str(incident.id),
                "state": incident.state,
                "level": incident.level,
                "rule_floor": incident.rule_floor,
                "is_drill": incident.is_drill,
                "opened_at": incident.opened_at.isoformat().replace("+00:00", "Z"),
                "closed_at": incident.closed_at.isoformat().replace("+00:00", "Z") if incident.closed_at else None,
                "summary_text": summary,
                "protected_member_label": member_label,
                "device_label": device_label,
            },
        }
