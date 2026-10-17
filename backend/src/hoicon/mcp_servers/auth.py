"""Bảo vệ `/mcp/*` (spec 003, ADR-009 §9): token Bearer + giới hạn tần suất theo client, ASGI thuần.

Vì sao tự viết (~100 dòng) thay cho `token_verifier` + `AuthSettings` của MCP SDK: SDK bắt khai `issuer_url` của một
máy chủ OAuth (HỏiCon không có ⇒ quảng bá metadata sai ở `/.well-known/oauth-protected-resource`) và không trả được
429. Không dùng `BaseHTTPMiddleware` vì nó đệm phản hồi, làm hỏng streamable HTTP.

- Máy chủ chỉ giữ SHA-256 của token theo tên client (`HOICON_MCP_THREAT_CLIENTS`), không bao giờ giữ token thô.
  Rỗng ⇒ 401.
- So sánh thời gian hằng, duyệt hết danh sách (không dừng sớm).
- Hạn mức: cửa sổ cố định theo phút và theo ngày giờ Việt Nam, mỗi client; đếm trong bộ nhớ tiến trình (ADR-002) ⇒
  chỉ đúng với MỘT tiến trình API; đổi sang bộ đếm chung khi scale. Yêu cầu bị từ chối (401/429) không tính vào hạn mức.
- Log: một dòng mỗi yêu cầu — tên client, mã trạng thái, tool, verdict, độ trễ. Không h1, không token/hash, không IP.
"""

import hmac
import json
import logging
import time
from collections.abc import Awaitable, Callable, MutableMapping
from contextvars import ContextVar
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any
from zoneinfo import ZoneInfo

from hoicon.config import get_settings

logger = logging.getLogger("hoicon.mcp")

VN = ZoneInfo("Asia/Ho_Chi_Minh")
MAX_BODY_BYTES = 64 * 1024  # một lời gọi tra cứu chỉ vài trăm byte
Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Ghi chú của yêu cầu đang xử lý (tool + verdict) để dòng log có đủ thông tin mà không đọc lại body phản hồi. Là dict
# DÙNG CHUNG: tác vụ con do MCP SDK sinh ra thừa kế tham chiếu tới cùng dict nên `note()` ở trong tool vẫn thấy.
_request_note: ContextVar[dict[str, str] | None] = ContextVar("mcp_request_note", default=None)


def note(**fields: str) -> None:
    """Tool gọi để ghi `tool=`/`verdict=` vào dòng log của yêu cầu hiện tại (không làm gì nếu ngoài guard)."""
    current = _request_note.get()
    if current is not None:
        current.update(fields)


def _bearer_token(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"authorization":
            scheme, _, token = value.decode("latin-1").partition(" ")
            token = token.strip()
            return token if scheme.lower() == "bearer" and token else None
    return None


def _content_length(scope: Scope) -> int:
    """`Content-Length` khai báo (0 nếu không có/không đọc được). Body chunked: Caddy (012) chặn tiếp."""
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return 0
    return 0


def _json_response(status: int, body: dict[str, str], extra: list[tuple[bytes, bytes]]) -> tuple[dict, dict]:
    payload = json.dumps(body).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode()), *extra]
    return {"type": "http.response.start", "status": status, "headers": headers}, {
        "type": "http.response.body",
        "body": payload,
    }


class McpGuard:
    def __init__(self, app: ASGIApp, *, clock: Callable[[], float] = time.time) -> None:
        self._app = app
        self._clock = clock
        self._minute: dict[str, tuple[int, int]] = {}  # client → (số phút kể từ epoch, đã đếm)
        self._day: dict[str, tuple[str, int]] = {}  # client → (ngày giờ VN, đã đếm)

    def _client_of(self, token: str | None) -> str | None:
        clients = get_settings().mcp_threat_clients
        if token is None or not clients:
            return None
        digest = sha256(token.encode()).hexdigest()
        found: str | None = None
        for name, expected in clients.items():  # duyệt hết, không dừng sớm
            if hmac.compare_digest(digest.encode(), expected.lower().encode()):
                found = name
        return found

    def _retry_after(self, client: str) -> int | None:
        """Còn trong hạn mức ⇒ tính vào và trả None; hết ⇒ số giây tới hết cửa sổ (≥ 1), KHÔNG tính vào."""
        settings = get_settings()
        now = self._clock()
        minute_id = int(now // 60)
        minute, count_min = self._minute.get(client, (minute_id, 0))
        if minute != minute_id:
            count_min = 0
        local = datetime.fromtimestamp(now, VN)
        day = local.date().isoformat()
        day_seen, count_day = self._day.get(client, (day, 0))
        if day_seen != day:
            count_day = 0
        if count_min >= settings.mcp_rate_per_min:
            return max(1, 60 - int(now % 60))
        if count_day >= settings.mcp_rate_per_day:
            midnight = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), tzinfo=VN)
            return max(1, int(midnight.timestamp() - now))
        self._minute[client] = (minute_id, count_min + 1)
        self._day[client] = (day, count_day + 1)
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "lifespan":
            await self._app(scope, receive, send)
            return
        if scope["type"] != "http":  # websocket... không có route nào cần: đóng, không để lọt qua token
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            return
        started = time.monotonic()
        client = self._client_of(_bearer_token(scope))
        status = 0
        fields = {"tool": "-", "verdict": "-"}

        async def tracking_send(message: MutableMapping[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            if client is None:
                for message in _json_response(401, {"error": "unauthorized"}, [(b"www-authenticate", b"Bearer")]):
                    await tracking_send(message)
            elif (retry := self._retry_after(client)) is not None:
                for message in _json_response(429, {"error": "rate_limited"}, [(b"retry-after", str(retry).encode())]):
                    await tracking_send(message)
            elif scope["method"] != "POST":  # stateless: GET sẽ mở luồng SSE treo vô hạn mà không có gì để gửi
                for message in _json_response(405, {"error": "method_not_allowed"}, [(b"allow", b"POST")]):
                    await tracking_send(message)
            elif _content_length(scope) > MAX_BODY_BYTES:
                for message in _json_response(413, {"error": "payload_too_large"}, []):
                    await tracking_send(message)
            else:
                reset = _request_note.set(fields)
                try:
                    await self._app(scope, receive, tracking_send)
                finally:
                    _request_note.reset(reset)
        finally:  # kể cả khi app ném lỗi/yêu cầu bị hủy
            logger.info(
                "mcp client=%s status=%s tool=%s verdict=%s ms=%d",
                client or "-",
                status,
                fields["tool"],
                fields["verdict"],
                (time.monotonic() - started) * 1000,
            )
