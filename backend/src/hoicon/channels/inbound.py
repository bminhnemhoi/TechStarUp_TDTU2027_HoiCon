"""Cập nhật Zalo đến (spec 002): lấy phần cần dùng và phân loại văn bản NGAY ở webhook.

Văn bản do người giám hộ gõ là dữ liệu không tin cậy và KHÔNG được lưu (FR-010, spec "Quyền riêng tư"): webhook chỉ xếp
vào job loại lệnh + giá trị đã phân loại (băm mã ghép, hoặc lựa chọn 1/2/3). Hợp đồng: docs/schemas/zalo_update.v1.json.
"""

import re
from dataclasses import dataclass
from typing import Any

from hoicon.domain.pii import encrypt_chat_id, hmac_pairing_code, hmac_zalo

MAX_ID_LEN = 128
MAX_MESSAGE_ID_LEN = 100  # khóa job `zalo:{bot_id}:{message_id}` chỉ có 200 ký tự
CHOICES = ("1", "2", "3")
_CODE = re.compile(r"[0-9]{6}")  # chỉ chữ số ASCII (str.isdigit chấp nhận cả chữ số Ả Rập-Ấn Độ)
_START = re.compile(r"/start(?:@\S+)?", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedUpdate:
    message_id: str
    user_id: str
    chat_id: str
    text: str


def _text_id(value: Any, limit: int) -> str | None:
    return value if isinstance(value, str) and 0 < len(value) <= limit else None


def parse_update(body: Any) -> ParsedUpdate | None:
    """Tin chữ riêng tư từ người (không phải bot) có đủ mã tin; mọi thứ khác ⇒ None (bỏ qua, không lỗi)."""
    result = body.get("result") if isinstance(body, dict) else None
    if not isinstance(result, dict) or result.get("event_name") != "message.text.received":
        return None
    message = result.get("message")
    if not isinstance(message, dict):
        return None
    sender, chat = message.get("from"), message.get("chat")
    if not isinstance(sender, dict) or not isinstance(chat, dict):
        return None
    if chat.get("chat_type") != "PRIVATE" or sender.get("is_bot") is True:
        return None
    message_id = _text_id(message.get("message_id"), MAX_MESSAGE_ID_LEN)
    user_id = _text_id(sender.get("id"), MAX_ID_LEN)
    chat_id = _text_id(chat.get("id"), MAX_ID_LEN)
    text = message.get("text")
    if not (message_id and user_id and chat_id and isinstance(text, str)):
        return None
    return ParsedUpdate(message_id, user_id, chat_id, text)


def classify(text: str) -> tuple[str, str | None]:
    """⇒ ("start", mã 6 số) | ("start_no_code", None) | ("choice", "1"|"2"|"3") | ("other", None)."""
    tokens = text.split()
    if tokens and _START.fullmatch(tokens[0]):
        if len(tokens) == 2 and _CODE.fullmatch(tokens[1]):
            return "start", tokens[1]
        return "start_no_code", None
    if len(tokens) == 1 and tokens[0] in CHOICES:
        return "choice", tokens[0]
    return "other", None


def build_job_payload(bot_id: str, parsed: ParsedUpdate) -> dict[str, str | int]:
    """Payload job `zalo_update`: định danh chỉ ở dạng băm (tra cứu) + mã hóa (để trả lời), văn bản đã phân loại — không
    có chữ thô, tên hiển thị hay Zalo ID thô (FR-010: job nằm trong DB 30 ngày). Thiếu khóa/pepper ⇒ RuntimeError."""
    kind, value = classify(parsed.text)
    kid, user_hmac = hmac_zalo(bot_id, parsed.user_id)
    payload: dict[str, str | int] = {
        "bot_id": bot_id,
        "message_id": parsed.message_id,
        "user_hmac": user_hmac,
        "hmac_kid": kid,
        "chat_enc": encrypt_chat_id(parsed.chat_id, user_hmac),
        "kind": kind,
    }
    if kind == "start" and value:
        payload["code_hash"] = hmac_pairing_code(value)
    elif kind == "choice" and value:
        payload["choice"] = value
    return payload
