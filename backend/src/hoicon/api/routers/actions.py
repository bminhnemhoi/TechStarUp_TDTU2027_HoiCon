"""`GET /v1/action/{token}` và `POST /v1/action/{token}/decision` (spec 023, FR-004, FR-005, SC-003, SC-004).

Cho phép người giám hộ xem tóm tắt sự cố và ra quyết định xử lý khẩn cấp thông qua magic link dùng một lần.
Không yêu cầu đăng nhập mật khẩu, xác thực dựa trên SHA-256 hash của ActionToken.
Tuyệt đối không lộ số điện thoại thô hay PII trong dữ liệu trả về.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, StringConstraints

from hoicon.db.models import Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services.action_token_service import (
    ActionTokenService,
    InvalidTokenError,
    TokenExpiredError,
    TokenNotFoundError,
    TokenUsedError,
)
from hoicon.services.incident_service import (
    ConcurrencyConflictError,
    IncidentNotFoundError,
    InvalidTransitionError,
    apply_guardian_decision,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["actions"])
_TOKEN_IN_PATH = re.compile(r"(/action/|/login/)[^/\s?\"']+")


def redact_action_token(text: str) -> str:
    """`/v1/action/<token>/decision` ⇒ `/v1/action/***/decision`; `/login/<token>` ⇒ `/login/***`: token thô không bao
    giờ vào log."""
    return _TOKEN_IN_PATH.sub(r"\1***", text)


class RedactActionTokenFilter(logging.Filter):
    """Log truy cập của uvicorn ghi nguyên đường dẫn (trong `args`) ⇒ che token trước khi định dạng."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(redact_action_token(a) if isinstance(a, str) else a for a in record.args)
        elif isinstance(record.msg, str):
            record.msg = redact_action_token(record.msg)
        return True


logging.getLogger("uvicorn.access").addFilter(RedactActionTokenFilter())
ALREADY_HANDLED = "Sự cố này đã được xử lý trước đó."


class IncidentDecisionIn(BaseModel):
    decision: Literal["safe", "prevented", "false_alarm", "emergency_pause"]
    # Nhận theo hợp đồng nhưng KHÔNG lưu: chữ tự do của người giám hộ có thể chứa số điện thoại/tên thật (luật 1).
    note: Annotated[str, StringConstraints(max_length=256)] | None = None


class IncidentDecisionResult(BaseModel):
    success: bool
    incident_id: UUID
    state: str
    outcome: str | None = None


@router.get("/action/{token}")
async def get_action_view(token: str) -> dict[str, Any]:
    """Lấy dữ liệu hiển thị cho trang hành động `/a/[token]`.

    Trả về chi tiết sự cố không chứa PII. Nếu token đã dùng hoặc hết hạn,
    vẫn trả dữ liệu sự cố kèm token_valid=False để giao diện thông báo phù hợp.
    """
    clean_token = token.strip()
    async with get_sessionmaker()() as session:
        view = await ActionTokenService.get_action_view_data(session, clean_token)
        if view is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy liên kết hành động")
        return view


@router.post("/action/{token}/decision", response_model=IncidentDecisionResult)
async def post_action_decision(token: str, body: IncidentDecisionIn) -> IncidentDecisionResult:
    """Người giám hộ gửi quyết định xử lý sự cố qua magic link dùng một lần.

    Xác thực token, tiêu thụ token và chuyển trạng thái sự cố trong cùng một giao dịch CSDL nguyên tử.
    """
    clean_token = token.strip()
    try:
        async with get_sessionmaker().begin() as session:
            try:
                token_record = await ActionTokenService.verify_token(session, clean_token, lock=True)
            except TokenNotFoundError:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy liên kết hành động") from None
            except TokenExpiredError:
                raise HTTPException(status.HTTP_410_GONE, detail="Liên kết đã hết hạn") from None
            except TokenUsedError:
                raise HTTPException(status.HTTP_409_CONFLICT, detail="Liên kết đã được sử dụng") from None
            except InvalidTokenError:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Mã liên kết không hợp lệ") from None

            if token_record.incident_id is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Liên kết không gắn với sự cố")

            incident = await session.get(Incident, token_record.incident_id)
            if incident is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sự cố liên kết")

            try:
                incident = await apply_guardian_decision(session, incident, body.decision, "action_link")
            except ConcurrencyConflictError:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, detail="Sự cố đã được cập nhật bởi thao tác khác, vui lòng thử lại"
                ) from None
            except InvalidTransitionError:
                raise HTTPException(status.HTTP_409_CONFLICT, detail=ALREADY_HANDLED) from None

            token_record.used_at = datetime.now(
                UTC
            )  # cùng giao dịch với chuyển trạng thái: cả hai thành công hoặc không

            return IncidentDecisionResult(
                success=True,
                incident_id=incident.id,
                state=incident.state,
                outcome=incident.outcome,
            )
    except IncidentNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy sự cố") from None
