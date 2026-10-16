"""Một cửa gọi Zalo Bot API (ADR-003, spec 002). Mọi lời gọi Zalo đi qua `ZaloClient`.

Zalo đặt **token trên đường dẫn URL** (`…/bot<TOKEN>/<method>`) nên:
- token chỉ được ghép vào URL ngay lúc gọi, không gán vào biến/thuộc tính sống lâu (giữ trong `SecretStr`);
- lỗi gói thành `ZaloError(status)` — không URL, không `description` của Zalo, không ngoại lệ httpx gốc (httpx ghi
  URL vào thông điệp lỗi): `raise` ở ngoài khối `except` nên `__context__` cũng rỗng;
- logger `httpx` đặt mức WARNING (httpx ghi `HTTP Request: POST <url>` ở INFO) và gắn thêm bộ lọc che `/bot***`
  phòng khi ai đó bật INFO.

Chỉ có `send_message` — các lệnh vận hành `setWebhook/getWebhookInfo/deleteWebhook` thuộc T019.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from pydantic import SecretStr

from hoicon.config import Settings

BASE_URL = "https://bot-api.zaloplatforms.com"
TIMEOUT_S = 5.0
MAX_TEXT = 2000  # sendMessage: text dài 1–2000 ký tự (docs/spikes/P1-S3-zalo.md §1)

# `(?<!/)`: bỏ qua `//bot-api.zaloplatforms.com` (tên miền), chỉ che đoạn `/bot<TOKEN>` đứng sau tên miền.
logger = logging.getLogger(__name__)

_TOKEN_IN_PATH = re.compile(r"(?<!/)/bot[^/\s\"']+")
_VALID_TOKEN = re.compile(r"^[A-Za-z0-9:_.~+=-]+$")  # không khoảng trắng, không / ? # % làm đổi cấu trúc URL


def redact(text: str) -> str:
    """Che đoạn token trên đường dẫn: `/bot<TOKEN>/sendMessage` ⇒ `/bot***/sendMessage`."""
    return _TOKEN_IN_PATH.sub("/bot***", text)


class RedactTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        return True


_httpx_logger = logging.getLogger("httpx")
_httpx_logger.setLevel(logging.WARNING)
_httpx_logger.addFilter(RedactTokenFilter())


class ZaloError(Exception):
    """Lỗi gọi Zalo. Chỉ mang mã trạng thái (None = mạng/timeout) — không bao giờ mang URL, token hay thân phản hồi."""

    def __init__(self, status: int | None) -> None:
        super().__init__(f"Zalo API lỗi (status={status})")
        self.status = status

    @property
    def retryable(self) -> bool:
        """Mạng, 408, 429, 5xx ⇒ thử lại. Còn lại (401/400/404/426…) là vĩnh viễn ⇒ `fallback_required`."""
        return self.status is None or self.status in (408, 429) or self.status >= 500


@dataclass(frozen=True)
class SentMessage:
    message_id: str
    date: int  # mili-giây epoch (Zalo)


class ZaloClient(Protocol):
    async def send_message(self, chat_id: str, text: str) -> SentMessage: ...


def _check(chat_id: str, text: str) -> None:
    if not chat_id:
        raise ValueError("chat_id rỗng")
    if not 1 <= len(text) <= MAX_TEXT:
        raise ValueError(f"text phải dài 1–{MAX_TEXT} ký tự")


class LiveZaloClient:
    simulated = False  # gửi thật

    def __init__(
        self,
        token: SecretStr,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_s: float = TIMEOUT_S,
    ) -> None:
        if not _VALID_TOKEN.fullmatch(token.get_secret_value()):  # fullmatch: `$` để lọt token có "\n" ở cuối
            raise RuntimeError("HOICON_ZALO_BOT_TOKEN có ký tự không hợp lệ (khoảng trắng/ký tự lạ) — dán lại")
        self._token = token
        self._transport = transport
        self._timeout_s = timeout_s

    async def _call(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST một phương thức Zalo; trả `result`. Token chỉ được ghép vào URL tại đây."""
        failed = False
        response: httpx.Response | None = None
        try:
            async with httpx.AsyncClient(transport=self._transport, timeout=self._timeout_s) as http:
                response = await http.post(
                    f"{BASE_URL}/bot{self._token.get_secret_value()}/{method}", json=payload or {}
                )
        except (httpx.HTTPError, httpx.InvalidURL):
            failed = True  # không giữ ngoại lệ gốc: thông điệp của nó chứa URL có token
        if failed or response is None:
            raise ZaloError(None) from None
        return _result(response)

    async def send_message(self, chat_id: str, text: str) -> SentMessage:
        _check(chat_id, text)
        result = await self._call("sendMessage", {"chat_id": chat_id, "text": text})
        message_id, date = result.get("message_id"), result.get("date")
        if not isinstance(message_id, str):
            raise ZaloError(200) from None
        return SentMessage(message_id=message_id, date=date if isinstance(date, int) else 0)

    # Lệnh vận hành (hoicon.ops.zalo_webhook): trả nguyên `result` của Zalo, nơi gọi tự chọn phần được in.
    async def set_webhook(self, url: str, shared_secret: str) -> dict[str, Any]:
        return await self._call("setWebhook", {"url": url, "secret_token": shared_secret})

    async def get_webhook_info(self) -> dict[str, Any]:
        return await self._call("getWebhookInfo")

    async def delete_webhook(self) -> dict[str, Any]:
        return await self._call("deleteWebhook")


def _result(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        body = None
    if response.status_code >= 400 or not isinstance(body, dict) or body.get("ok") is not True:
        code = body.get("error_code", body.get("errorCode")) if isinstance(body, dict) else None
        raise ZaloError(code if isinstance(code, int) else response.status_code) from None
    result = body.get("result")
    if not isinstance(result, dict):
        raise ZaloError(response.status_code) from None
    return result


@dataclass(frozen=True)
class MockSent:
    chat_id: str
    text: str
    message_id: str


@dataclass
class MockZaloClient:
    """Mặc định khi thiếu token/CI: không gọi mạng, ghi tin vào bộ nhớ để test kiểm tra."""

    simulated = True  # KHÔNG gửi thật: `deliver` đánh dấu messages_out.error="mock"

    sent: list[MockSent] = field(default_factory=list)

    async def send_message(self, chat_id: str, text: str) -> SentMessage:
        _check(chat_id, text)
        message_id = f"mock-{len(self.sent) + 1}"
        self.sent.append(MockSent(chat_id=chat_id, text=text, message_id=message_id))
        return SentMessage(message_id=message_id, date=time.time_ns() // 1_000_000)


def mock_allowed(settings: Settings) -> bool:
    """Mock không gửi tin thật ⇒ chỉ dev/test (không cả `ci`); nơi khác phải `HOICON_ZALO_MODE=live`."""
    return settings.env.strip().lower() in ("dev", "test")


def build_zalo_client(settings: Settings) -> ZaloClient:
    """Chọn bản theo `HOICON_ZALO_MODE`. `live` thiếu token ⇒ lỗi (không âm thầm rơi về mock)."""
    if settings.zalo_mode == "mock":
        if not mock_allowed(
            settings
        ):  # mock không gửi tin thật: ngoài dev/test phải lỗi to, không âm thầm mất cảnh báo
            raise RuntimeError(f"HOICON_ENV={settings.env} phải đặt HOICON_ZALO_MODE=live (mock không gửi tin thật)")
        logger.warning("Zalo chạy chế độ MOCK: tin KHÔNG được gửi thật (đặt HOICON_ZALO_MODE=live để gửi thật)")
        return MockZaloClient()
    token = settings.zalo_bot_token
    if token is None or not token.get_secret_value():
        raise RuntimeError("HOICON_ZALO_MODE=live cần HOICON_ZALO_BOT_TOKEN (docs/setup/ACCOUNTS.md)")
    return LiveZaloClient(token)
