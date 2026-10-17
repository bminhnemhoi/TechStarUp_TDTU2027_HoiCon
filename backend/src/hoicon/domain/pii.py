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
import math
import os
import re
import unicodedata

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from hoicon.config import get_settings

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# ≥ 4 chữ số, có thể xen dấu phân cách (cả dấu phẩy dính liền kiểu dấu nhóm nghìn: "0,900,000,123"); không đứng giữa
# một dãy số dài hơn.
_DIGITS = re.compile(r"(?<!\d)(?:\+\s*)?\d(?:(?:[\s.\-_/()]|(?<=\d),(?=\d{3}(?!\d)))*\d){3,}(?!\d)")
_MONEY_UNIT = re.compile(
    r"\s*(?:đ|₫|đồng|dong|vnd|vnđ|k|nghìn|nghin|ngàn|ngan|triệu|trieu|tr|tỷ|tỉ|ty)(?!\w)", re.IGNORECASE
)
_VN_MOBILE = re.compile(r"^(?:0|84)[35789]\d{8}$")
_H1 = re.compile(r"[0-9a-f]{64}")  # `fullmatch`: `$` của `re` cho lọt "\n" ở cuối


def _is_plausible_money(raw: str, digits: str) -> bool:
    """Chỉ miễn che khi trông đúng là số tiền, KHÔNG phải số điện thoại/tài khoản đội lốt đơn vị tiền: không mở đầu
    bằng 0/+ (kể cả nhóm đầu "0.900"), tối đa 12 chữ số; từ 10 chữ số (và 9 chữ số mở đầu 3/5/7/8/9 = số điện thoại bỏ
    số 0) chỉ khi tròn triệu — số tiền lớn thật luôn tròn, số điện thoại tròn triệu chỉ khoảng một phần triệu."""
    if raw.lstrip().startswith(("0", "+")):
        return False
    count = len(digits)
    if count > 12:
        return False
    if count >= 10 or (count == 9 and digits[0] in "35789"):
        return digits.endswith("000000")
    return True


def mask_text(text: str) -> str:
    """Thay email và dãy chữ số bằng nhãn; số điện thoại/số dài giữ 3 số cuối để người đọc còn đối chiếu được."""
    text = _EMAIL.sub("[EMAIL]", text)

    def replace(match: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", match.group())
        if _MONEY_UNIT.match(text, match.end()) and _is_plausible_money(match.group(), digits):
            return match.group()  # "20.000.000 đồng": số tiền cần cho đánh giá, không định danh ai

        if _VN_MOBILE.match(digits):
            return f"[SĐT ***{digits[-3:]}]"
        return f"[SỐ ***{digits[-3:]}]" if len(digits) >= 6 else "[MÃ]"

    return _DIGITS.sub(replace, text)


# Khóa không bao giờ ra khỏi máy chủ qua luồng truy vết (spec 025, ADR-006). `text` là thân tin Zalo trong payload job.
TRACE_DENY_KEYS = frozenset(
    {
        "h1",
        "hmac",
        "phone",
        "phone_hmac",
        "last3",
        "package",
        "caller",
        "token",
        "action_token",
        "chat_id",
        "zalo_user_id",
        "note",
        "text",
        "input_redacted",
    }
)
TRACE_MAX_STRING = 500
# Một khóa bị bỏ nếu có BẤT KỲ từ nào (tách theo ký tự không phải chữ/số và theo camelCase, sau NFKC) nằm trong tập này,
# hoặc ghép lại bằng một khóa cấm: bắt "H1 ", "ｈ1", "package_name", "note_text", "callerPhone", "x.token.y".
TRACE_DENY_WORDS = frozenset(
    {"h1", "hmac", "phone", "package", "caller", "token", "note", "text", "last3", "zalo", "chat"}
)
# ...trừ khi từ CUỐI của khóa cho biết đó chỉ là cờ/số đếm về thứ nhạy cảm (`note_flags`, `text_len`, `token_count`).
TRACE_SAFE_SUFFIXES = frozenset({"flags", "flag", "flagged", "len", "length", "count", "sent", "kind", "type"})
_TRACE_MAX_DEPTH = 20
_TRACE_BIG_INT = 2**63
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")
_NORMALIZED_DENY_KEYS = frozenset(_NON_ALNUM.sub("", key) for key in TRACE_DENY_KEYS)
_SPACED_HEX = re.compile(r"(?<![0-9A-Za-z])(?:[0-9a-fA-F]{2}[ :-]){15,}[0-9a-fA-F]{2}(?![0-9A-Za-z])")
_LONG_RUN = re.compile(r"[A-Za-z0-9_+=-]{32,}")
_HEX_RUN = re.compile(r"[0-9a-fA-F]{32,}")
_HEX_ONLY = re.compile(r"[0-9a-fA-F]+")
_KEEP_AS_IS = re.compile(
    # mốc giờ ISO-8601 đầy đủ (có `T`) và UUID chuẩn (id sự cố/lượt/bước, không phải PII): `mask_text` sẽ phá cả hai
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})?(?!\d)"
    r"|\b[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b)"
)


def _key_policy(key: object) -> str:
    """ "drop" (bỏ khóa), "flag" (chỉ giữ giá trị kiểu cờ/số đếm) hoặc "keep"."""
    name = unicodedata.normalize("NFKC", str(key))
    if _NON_ALNUM.sub("", name.lower()) in _NORMALIZED_DENY_KEYS:
        return "drop"
    words = [word.lower() for word in _NON_ALNUM.split(_CAMEL.sub("_", name)) if word]
    if not words or TRACE_DENY_WORDS.isdisjoint(words):
        return "keep"
    return "flag" if words[-1] in TRACE_SAFE_SUFFIXES else "drop"


_ENUM_LIKE = re.compile(r"[a-z_]{1,32}")


def _is_flag_value(value: object) -> bool:
    """Cờ/số đếm đúng nghĩa: bool/số/None, chuỗi giống enum ("transfer_mentioned"), hoặc dict/list chỉ gồm chúng."""
    if value is None or isinstance(value, bool | int | float):
        return True
    if isinstance(value, str):
        return _ENUM_LIKE.fullmatch(value) is not None
    if isinstance(value, dict):
        return all(_is_flag_value(item) for item in value.values())
    if isinstance(value, list):
        return all(_is_flag_value(item) for item in value)
    return False


def _looks_like_token(found: str) -> bool:
    """Giống token ngẫu nhiên hơn là định danh: từ 32 ký tự mà có CẢ chữ HOA lẫn thường (định danh snake_case thì không
    có chữ HOA), hoặc ≥ 40 ký tự chữ thường + số ít dấu `_`/`-` (< 10%). UUID thì đã được giữ riêng."""
    if any(ch.isupper() for ch in found) and any(ch.islower() for ch in found):
        return True
    separators = sum(ch in "_-" for ch in found)
    return len(found) >= 40 and any(ch.isdigit() for ch in found) and separators < 0.1 * len(found)


def _spaced_hex(match: re.Match[str]) -> str:
    # Chuỗi chỉ toàn chữ số tách cặp ("10 11 12 …") không phải hash; để `mask_text` lo.
    return "[HASH]" if re.search("[a-fA-F]", match.group()) else match.group()


def _mask_keeping_timestamps(text: str) -> str:
    """`mask_text` nhưng giữ mốc giờ ISO-8601 (có `T`) và UUID chuẩn; ngày sinh trần ("1980-05-12") vẫn bị che."""
    parts = _KEEP_AS_IS.split(text)  # phần tử lẻ = mốc giờ / UUID
    # UUID chứa dãy ≥ 10 chữ số liền nhau là đáng ngờ (số điện thoại đội lốt UUID): không miễn che.
    return "".join(
        part if index % 2 and not re.search(r"\d{10,}", part) else mask_text(part) for index, part in enumerate(parts)
    )


def _trace_string(text: str) -> str:
    """Che một chuỗi: hex (kể cả ngắt bằng dấu cách/`:`/`-`) ⇒ [HASH]; chuỗi giống token ngẫu nhiên ⇒ [TOKEN];
    `mask_text` (giữ mốc giờ ISO); cắt 500; rồi che lại phần đuôi bị cắt (chỗ cắt có thể để lại dãy số ngắn). Hai lượt
    là đủ để lũy đẳng."""

    def run(match: re.Match[str]) -> str:
        found = match.group()
        if _HEX_ONLY.fullmatch(found):
            return "[HASH]"
        return "[TOKEN]" if _looks_like_token(found) else found

    text = _HEX_RUN.sub("[HASH]", _LONG_RUN.sub(run, _SPACED_HEX.sub(_spaced_hex, text)))
    return _mask_keeping_timestamps(_mask_keeping_timestamps(text)[:TRACE_MAX_STRING])


def redact_json(value: object, *, _depth: int = 0) -> object:
    """Bản sao đã che của dữ liệu JSON để xuất ra ngoài (luồng SSE, `/steps`): bỏ khóa cấm ở mọi độ sâu (xem
    `_denied_key`), che mọi chuỗi và tên khóa, giữ số/bool/None (số nguyên cực lớn ⇒ "[SỐ LỚN]", NaN/∞ ⇒ None để
    luôn ra JSON hợp lệ). Lũy đẳng. Lớp này độc lập với danh sách trắng cột của `step_view`: một lớp sót thì lớp kia
    vẫn chặn."""
    if _depth > _TRACE_MAX_DEPTH:
        return "[…]"
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) < _TRACE_BIG_INT else "[SỐ LỚN]"
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        return _trace_string(value)
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, item in value.items():
            policy = _key_policy(key)
            if policy == "drop":
                continue
            result = redact_json(item, _depth=_depth + 1)
            if policy == "flag" and not _is_flag_value(result):
                continue
            cleaned[_trace_string(str(key))] = result
        return cleaned
    if isinstance(value, list | tuple):
        return [redact_json(item, _depth=_depth + 1) for item in value]
    return _trace_string(str(value))  # kiểu không phải JSON (Decimal, UUID…): chuỗi đã che


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
