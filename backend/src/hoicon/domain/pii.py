"""Che, băm và giảm thiểu dữ liệu cá nhân (CLAUDE.md luật 1–2, ADR-006).

- `mask_text`: mọi văn bản tự do đi ra log/LLM/tin nhắn phải qua đây. Che MỌI dãy ≥ 4 chữ số (cho phép dấu cách, chấm,
  gạch, ngoặc xen giữa) — số điện thoại, OTP, số tài khoản, CCCD, ngày sinh — trừ số tiền có đơn vị ngay sau. Che thừa
  (năm, mã ngắn) được chấp nhận: an toàn hơn tiện.
- `note_flags`: lời kể tự do của người cao tuổi KHÔNG được lưu hay gửi cho LLM (tên thật, địa chỉ, số đọc bằng chữ không
  che được). Máy chủ chỉ giữ vài cờ tất định rút từ đó.
- `hmac_h1`: máy chủ chỉ lưu `HMAC(pepper[kid], h1)` + 3 số cuối, không lưu h1.
- `hmac_zalo`, `encrypt_chat_id`/`decrypt_chat_id` (spec 002 D1): Zalo ID không lưu thô. HMAC (cùng pepper, tiền tố miền
  riêng) để tra cứu; `chat_id` mã hóa AES-256-GCM (khóa ngoài DB) vì còn phải giải mã để gửi tin.
"""

import base64
import hashlib
import hmac
import os
import re
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from hoicon.config import get_settings

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# ≥ 4 chữ số, có thể xen dấu phân cách; không đứng giữa một dãy số dài hơn.
_DIGITS = re.compile(r"(?<!\d)(?:\+\s*)?\d(?:[\s.\-_/()]*\d){3,}(?!\d)")
_MONEY_UNIT = re.compile(
    r"\s*(?:đ|₫|đồng|dong|vnd|vnđ|k|nghìn|nghin|ngàn|ngan|triệu|trieu|tr|tỷ|tỉ|ty)(?!\w)", re.IGNORECASE
)
_VN_MOBILE = re.compile(r"^(?:0|84)[35789]\d{8}$")
_H1 = re.compile(r"[0-9a-f]{64}")  # `fullmatch`: `$` của `re` cho lọt "\n" ở cuối


def mask_text(text: str) -> str:
    """Thay email và dãy chữ số bằng nhãn; số điện thoại/số dài giữ 3 số cuối để người đọc còn đối chiếu được."""
    text = _EMAIL.sub("[EMAIL]", text)

    def replace(match: re.Match[str]) -> str:
        if _MONEY_UNIT.match(text, match.end()):
            return match.group()  # "20.000.000 đồng": số tiền cần cho đánh giá, không định danh ai
        digits = re.sub(r"\D", "", match.group())
        if _VN_MOBILE.match(digits):
            return f"[SĐT ***{digits[-3:]}]"
        return f"[SỐ ***{digits[-3:]}]" if len(digits) >= 6 else "[MÃ]"

    return _DIGITS.sub(replace, text)


def _plain(text: str) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (để khớp từ khóa có/không dấu)."""
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


NOTE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "mentions_authority": (
        "cong an",
        "canh sat",
        "toa an",
        "vien kiem sat",
        "dieu tra",
        "co quan",
        "thue",
        "ngan hang",
    ),
    "mentions_transfer": ("chuyen tien", "chuyen khoan", "nap tien", "nop tien", "rut tien", "tai khoan", "dong phi"),
    "mentions_code": ("otp", "ma xac thuc", "ma so", "mat khau", "ma pin", "doc ma"),
    "mentions_secrecy": ("bi mat", "dung noi", "khong duoc noi", "giu kin", "khong noi voi", "khong bao"),
    "mentions_app_or_link": ("cai ung dung", "tai ung dung", "link", "duong dan", "chia se man hinh", "ung dung la"),
}


def note_flags(note: str) -> dict[str, bool]:
    """Cờ tất định từ lời kể tự do — thứ duy nhất của lời kể được giữ lại và đưa cho LLM."""
    plain = _plain(note)
    return {flag: any(keyword in plain for keyword in keywords) for flag, keywords in NOTE_KEYWORDS.items()}


def _pepper(kid: int | None) -> tuple[int, bytes]:
    settings = get_settings()
    kid = kid or settings.phone_pepper_kid
    pepper = getattr(settings, f"phone_pepper_{kid}", None)
    if pepper is None:
        raise RuntimeError(f"thiếu HOICON_PHONE_PEPPER_{kid}")
    return kid, pepper.get_secret_value().encode()


def hmac_h1(h1: str, kid: int | None = None) -> tuple[int, str]:
    """`HMAC-SHA256(pepper[kid], h1)` (ADR-006) ⇒ (kid, hex). Pepper nằm ngoài DB (biến môi trường)."""
    if not _H1.fullmatch(h1):
        raise ValueError("h1 phải là SHA-256 hex chữ thường (64 ký tự)")
    kid, pepper = _pepper(kid)
    return kid, hmac.new(pepper, h1.encode(), hashlib.sha256).hexdigest()


def candidate_hmacs(h1: str) -> list[tuple[int, str]]:
    """HMAC của h1 theo MỌI kid đã cấu hình pepper (kid hiện hành đứng đầu): xoay pepper rồi vẫn tra được dòng cũ."""
    current = get_settings().phone_pepper_kid
    kids = [current] + [kid for kid in (1, 2) if kid != current and getattr(get_settings(), f"phone_pepper_{kid}")]
    return [hmac_h1(h1, kid) for kid in kids]


def hmac_zalo(bot_id: str, user_id: str, kid: int | None = None) -> tuple[int, str]:
    """`HMAC-SHA256(pepper[kid], "hoicon:zalo:v1:" + bot_id + ":" + user_id)` ⇒ (kid, hex) — khóa tra cứu người giám hộ.

    Tiền tố miền để không lẫn với HMAC của h1 số điện thoại (cùng pepper). `bot_id` không được chứa ":" để
    ("a:b", "c") không trùng ("a", "b:c").
    """
    if not bot_id or not user_id or ":" in bot_id:
        raise ValueError("bot_id/user_id không được rỗng, bot_id không chứa ':'")
    kid, pepper = _pepper(kid)
    message = f"hoicon:zalo:v1:{bot_id}:{user_id}".encode()
    return kid, hmac.new(pepper, message, hashlib.sha256).hexdigest()


def hmac_pairing_code(code: str) -> str:
    """Băm mã ghép Zalo 6 số để lưu (`pairing_codes.code_hash`) và so khớp; tiền tố miền riêng, cùng pepper.

    Lưu ý: 10⁶ khả năng nên băm chỉ chống lộ DB tình cờ, không chống dò; chống dò dựa vào hạn 15 phút + dùng một lần.
    """
    if not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError("mã ghép phải đúng 6 chữ số")
    _, pepper = _pepper(None)
    return hmac.new(pepper, f"hoicon:pairing:v1:{code}".encode(), hashlib.sha256).hexdigest()


_NONCE_BYTES = 12
_TAG_BYTES = 16


def _aead(kid: int) -> AESGCM:
    key = getattr(get_settings(), f"data_key_{kid}", None)
    if key is None:
        raise RuntimeError(f"thiếu HOICON_DATA_KEY_{kid}")
    hex_key = key.get_secret_value()
    if not _H1.fullmatch(hex_key):  # hex 64 ký tự = 32 byte; fullmatch vì `$` cho lọt "\n" ở cuối
        raise RuntimeError(f"HOICON_DATA_KEY_{kid} phải là chuỗi hex 64 ký tự (chạy init_env)")
    return AESGCM(bytes.fromhex(hex_key))


def _aad(kid: int, context: str) -> bytes:
    """Dữ liệu xác thực: gắn `kid` (đổi tiền tố kid ⇒ giải mã hỏng) và `context` = HMAC của chính người đó (tráo bản mã
    `zalo_chat_enc` giữa hai người giám hộ để chuyển hướng cảnh báo ⇒ giải mã hỏng)."""
    if not context:
        raise ValueError("thiếu context gắn bản mã chat_id")
    return f"hoicon:zalo:chat:v1:{kid}:{context}".encode()


def encrypt_chat_id(chat_id: str, context: str, kid: int | None = None) -> str:
    """AES-256-GCM, nonce 12 byte ngẫu nhiên ⇒ `"<kid>.<base64url(nonce‖ciphertext‖tag)>"` (`members.zalo_chat_enc`)."""
    if not chat_id:
        raise ValueError("chat_id rỗng")
    kid = kid or get_settings().data_key_kid
    nonce = os.urandom(_NONCE_BYTES)
    sealed = nonce + _aead(kid).encrypt(nonce, chat_id.encode(), _aad(kid, context))
    return f"{kid}.{base64.urlsafe_b64encode(sealed).decode()}"


def decrypt_chat_id(stored: str, context: str) -> str:
    """Giải mã giá trị của `encrypt_chat_id` lúc gửi tin, không lưu kết quả. Hỏng/giả mạo ⇒ ValueError rỗng dữ liệu."""
    kid_text, _, blob = stored.partition(".")
    if not (kid_text.isascii() and kid_text.isdecimal() and blob):
        raise ValueError("chat_id mã hóa sai định dạng")
    kid = int(kid_text)
    aead = _aead(kid)
    plain: str | None = None
    try:
        sealed = base64.urlsafe_b64decode(blob)
        if len(sealed) > _NONCE_BYTES + _TAG_BYTES:  # ngắn hơn nonce + tag + 1 byte ⇒ không thể là bản mã hợp lệ
            plain = aead.decrypt(sealed[:_NONCE_BYTES], sealed[_NONCE_BYTES:], _aad(kid, context)).decode()
    except (ValueError, InvalidTag):  # binascii.Error và UnicodeDecodeError đều là ValueError
        pass
    if plain is None:
        raise ValueError("không giải mã được chat_id") from None  # ngoài `except`: không giữ __context__
    return plain
