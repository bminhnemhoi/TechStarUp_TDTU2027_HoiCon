"""Bucket k-ẩn danh của danh sách đe dọa (spec 026 FR-003, ADR-011).

Máy KHÔNG nhận tập h1 (dò ngược được cả danh sách): chỉ nhận vài bit đầu của h1.
`bucket24 = int(h1[:6], 16)` rồi dịch phải về `bucket_bits` (16–24, mặc định 22 ≈ 86 số di động/bucket).
Máy chủ không lưu bucket dạng rõ cạnh `last3` (kẻ có bản sao DB sẽ thử từng số để ra số điện thoại, vô hiệu pepper
ADR-006) mà lưu `bucket_enc`:
`"<kid>." + base64url(nonce ‖ AES-256-GCM(bucket24, HOICON_DATA_KEY_<kid>, aad))`,
`aad = "hoicon:threat:bucket:v1:<kid>:<value_hmac>"` (tráo bản mã giữa hai dòng ⇒ giải mã hỏng). Cùng mẫu
`encrypt_chat_id` của `domain/pii.py` (dùng lại `_aead`).
"""

import base64
import os
import re

from cryptography.exceptions import InvalidTag

from hoicon.config import get_settings
from hoicon.domain.pii import (
    _aead,
)

MIN_BITS = 16
MAX_BITS = 24
_H1 = re.compile(r"[0-9a-f]{64}")
_NONCE_BYTES = 12
_TAG_BYTES = 16
_BUCKET_BYTES = 3


def bucket24(h1: str) -> int:
    """24 bit đầu của h1 (SHA-256 nên phân bố đều)."""
    if not _H1.fullmatch(h1):
        raise ValueError("h1 phải là hex thường 64 ký tự")
    return int(h1[:6], 16)


def shift(value: int, bits: int) -> int:
    """Giữ `bits` bit đầu của bucket 24 bit."""
    if not MIN_BITS <= bits <= MAX_BITS:
        raise ValueError(f"bucket_bits phải nằm trong {MIN_BITS}–{MAX_BITS} bit")
    _check_range(value)
    return value >> (MAX_BITS - bits)


def _check_range(value: int) -> None:
    if not 0 <= value < 2**MAX_BITS:
        raise ValueError("bucket phải nằm trong 24 bit")


def _aad(kid: int, value_hmac: str) -> bytes:
    if not value_hmac:
        raise ValueError("thiếu value_hmac gắn bản mã bucket")
    return f"hoicon:threat:bucket:v1:{kid}:{value_hmac}".encode()


def encrypt_bucket(value: int, value_hmac: str, kid: int | None = None) -> str:
    """Mã hóa bucket 24 bit của một chỉ báo (`threat_indicators.bucket_enc`), nonce ngẫu nhiên mỗi lần."""
    _check_range(value)
    kid = kid or get_settings().data_key_kid
    aad = _aad(kid, value_hmac)
    nonce = os.urandom(_NONCE_BYTES)
    sealed = nonce + _aead(kid).encrypt(nonce, value.to_bytes(_BUCKET_BYTES, "big"), aad)
    return f"{kid}.{base64.urlsafe_b64encode(sealed).decode()}"


def decrypt_bucket(stored: str, value_hmac: str) -> int:
    """Giải mã `bucket_enc` lúc dựng ảnh chụp, không lưu kết quả. Hỏng/giả mạo/tráo dòng ⇒ ValueError rỗng dữ liệu."""
    kid_text, _, blob = stored.partition(".")
    if not (kid_text.isascii() and kid_text.isdecimal() and blob):
        raise ValueError("bucket mã hóa sai định dạng")
    kid = int(kid_text)
    aead = _aead(kid)  # thiếu khóa cho kid ⇒ RuntimeError (cấu hình), không nuốt thành lỗi dữ liệu
    plain: bytes | None = None
    try:
        sealed = base64.urlsafe_b64decode(blob)
        if len(sealed) == _NONCE_BYTES + _BUCKET_BYTES + _TAG_BYTES:
            plain = aead.decrypt(sealed[:_NONCE_BYTES], sealed[_NONCE_BYTES:], _aad(kid, value_hmac))
    except (ValueError, InvalidTag):  # binascii.Error là ValueError
        pass
    if plain is None:
        raise ValueError("không giải mã được bucket") from None  # ngoài `except`: không giữ __context__
    return int.from_bytes(plain, "big")
