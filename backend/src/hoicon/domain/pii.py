"""Che, băm và giảm thiểu dữ liệu cá nhân (CLAUDE.md luật 1–2, ADR-006).

- `mask_text`: mọi văn bản tự do đi ra log/LLM/tin nhắn phải qua đây. Che MỌI dãy ≥ 4 chữ số (cho phép dấu cách, chấm,
  gạch, ngoặc xen giữa) — số điện thoại, OTP, số tài khoản, CCCD, ngày sinh — trừ số tiền có đơn vị ngay sau. Che thừa
  (năm, mã ngắn) được chấp nhận: an toàn hơn tiện.
- `note_flags`: lời kể tự do của người cao tuổi KHÔNG được lưu hay gửi cho LLM (tên thật, địa chỉ, số đọc bằng chữ không
  che được). Máy chủ chỉ giữ vài cờ tất định rút từ đó.
- `hmac_h1`: máy chủ chỉ lưu `HMAC(pepper[kid], h1)` + 3 số cuối, không lưu h1.
"""

import hashlib
import hmac
import re
import unicodedata

from hoicon.config import get_settings

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# ≥ 4 chữ số, có thể xen dấu phân cách; không đứng giữa một dãy số dài hơn.
_DIGITS = re.compile(r"(?<!\d)(?:\+\s*)?\d(?:[\s.\-_/()]*\d){3,}(?!\d)")
_MONEY_UNIT = re.compile(
    r"\s*(?:đ|₫|đồng|dong|vnd|vnđ|k|nghìn|nghin|ngàn|ngan|triệu|trieu|tr|tỷ|tỉ|ty)(?!\w)", re.IGNORECASE
)
_VN_MOBILE = re.compile(r"^(?:0|84)[35789]\d{8}$")
_H1 = re.compile(r"^[0-9a-f]{64}$")


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


def hmac_h1(h1: str, kid: int | None = None) -> tuple[int, str]:
    """`HMAC-SHA256(pepper[kid], h1)` (ADR-006) ⇒ (kid, hex). Pepper nằm ngoài DB (biến môi trường)."""
    if not _H1.match(h1):
        raise ValueError("h1 phải là SHA-256 hex chữ thường (64 ký tự)")
    settings = get_settings()
    kid = kid or settings.phone_pepper_kid
    pepper = getattr(settings, f"phone_pepper_{kid}", None)
    if pepper is None:
        raise RuntimeError(f"thiếu HOICON_PHONE_PEPPER_{kid}")
    return kid, hmac.new(pepper.get_secret_value().encode(), h1.encode(), hashlib.sha256).hexdigest()
