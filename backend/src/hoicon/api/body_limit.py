"""Giới hạn thân yêu cầu ở tầng ứng dụng (spec 034 FR-006): chặn từ chối dịch vụ bằng thân rất lớn trước khi phân tích.

ASGI thuần (không đọc hết thân vào bộ nhớ): `Content-Length` khai quá hạn ⇒ 413 ngay, không đọc byte nào; thân chunked
(không có `Content-Length`) hoặc khai gian ⇒ đếm byte khi đọc, vượt hạn ⇒ ngắt và trả 413 nếu chưa gửi phản hồi nào.
Webhook Zalo có giới hạn riêng (`api/webhooks.py`); một lô sự kiện tối đa 50 sự kiện nhỏ hơn nhiều so với hạn này.
"""

import json
from typing import Any

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 256 * 1024
_BODY = json.dumps({"detail": "Dữ liệu gửi lên quá lớn."}, ensure_ascii=False).encode()


class PayloadTooLargeError(HTTPException):
    """Thân vượt hạn giữa chừng khi đang đọc. Là `HTTPException(413)`: FastAPI không đổi nó thành 400 "lỗi đọc thân" như
    với ngoại lệ thường; ứng dụng con không có trình xử lý HTTPException (MCP mount) thì middleware này tự trả 413."""

    def __init__(self) -> None:
        super().__init__(status_code=413, detail="Dữ liệu gửi lên quá lớn.")


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope["headers"]).get(b"content-length", b"")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return
        seen = 0
        started = False

        async def counting_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    raise PayloadTooLargeError
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except PayloadTooLargeError:
            if started:  # đã trả lời dở: không thể đổi mã trạng thái nữa
                raise
            await self._reject(send)

    async def _reject(self, send: Send) -> None:
        headers: list[Any] = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(_BODY)).encode()),
            (b"connection", b"close"),
        ]
        await send({"type": "http.response.start", "status": 413, "headers": headers})
        await send({"type": "http.response.body", "body": _BODY})
