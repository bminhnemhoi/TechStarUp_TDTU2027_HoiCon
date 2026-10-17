"""Xác minh số điện thoại / đường link bằng QUY TẮC TẤT ĐỊNH (spec 026 FR-004, plan §4). KHÔNG gọi LLM.

Lý do: "nguồn dẫn" phải là dữ kiện có thật (tên danh sách, phiên bản, mã quy tắc); LLM chỉ có thể bịa thêm nguồn
(luật 5 + AGENTS.md). Bảng kết luận cố định, xét từ trên xuống, dừng ở dòng khớp đầu tiên:

| chủ thể | điều kiện                                                       | verdict   | sàn nâng mức |
| phone   | trong danh sách, confidence ≥ 0,70                              | dangerous | critical     |
| phone   | trong danh sách, confidence < 0,70                              | warning   | high         |
| phone   | không có trong danh sách                                         | unknown   | —            |
| url     | đường dẫn kết thúc .apk/.xapk/.apks/.exe/.bat/.scr               | dangerous | critical     |
| url     | host là địa chỉ IP / punycode (xn--) / link rút gọn               | warning   | high         |
| url     | có "tên:mật khẩu@" trước host (cách che đích thật của link)       | warning   | high         |
| url     | host nhắc tên ngân hàng hoặc cơ quan nhà nước                     | warning   | high         |
| url     | scheme http (không TLS)                                           | warning   | high         |
| url     | còn lại                                                           | unknown   | —            |

`safe` CHỈ dành cho khớp sổ đăng ký chính thức (chưa có ở v1) ⇒ dịch vụ này KHÔNG BAO GIỜ trả `safe`.

Riêng tư: số điện thoại vào đây ở dạng h1 (máy băm), chủ thể được lưu là `HMAC(pepper[kid], h1)`. Với URL chỉ giữ
tên máy chủ (IDNA, chữ thường) trong bộ nhớ của request; chỉ lưu `HMAC(pepper, SHA-256("hoicon:url:v1:" + host))`.
Đường dẫn, truy vấn, mảnh và thông tin đăng nhập bị bỏ ngay sau khi phân tích; thông báo lỗi không lặp lại đầu vào.
"""

import hashlib
import ipaddress
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlsplit

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.db.ids import new_id
from hoicon.db.models import Verification
from hoicon.domain.pii import hmac_h1
from hoicon.mcp_servers.threat import NO_LIST_VERSION, ThreatVerdict, lookup_h1

DISCLAIMER = (
    "Đây là trợ lý AI HỏiCon. Kết quả chỉ để tham khảo, không thay cho ý kiến của con cháu hay cơ quan chức năng."
)
HIGH_CONFIDENCE = 0.70
URL_STRONG_CONFIDENCE = 0.9
URL_WEAK_CONFIDENCE = 0.6
MAX_URL_LENGTH = 2048
LIST_NAME = "Danh sách cảnh báo HỏiCon"

# Mã lý do → câu tiếng Việt, giọng ấm áp, có hành động cụ thể, không gây hoảng sợ (không cụm nào trong PANIC_PHRASES).
REASONS: dict[str, str] = {
    "listed_high": (
        "Số này nằm trong danh sách cảnh báo lừa đảo của HỏiCon. Xin đừng chuyển tiền hay đọc mã OTP; "
        "hãy gọi hỏi con hoặc người thân trước nhé."
    ),
    "listed_low": (
        "Số này có trong danh sách theo dõi của HỏiCon nhưng chưa chắc chắn. "
        "Hãy hỏi con trước khi làm theo bất cứ yêu cầu chuyển tiền nào."
    ),
    "not_listed": (
        "Số này chưa có trong danh sách cảnh báo của HỏiCon. "
        "Điều đó chưa có nghĩa là an toàn, vẫn nên hỏi con trước khi chuyển tiền."
    ),
    "app_download": (
        "Đường link này dẫn tới tệp cài ứng dụng ngoài kho chính thức. Xin đừng tải hay cài, hãy hỏi con trước nhé."
    ),
    "ip_host": (
        "Đường link này dùng dãy số thay cho tên trang web, cách các trang giả mạo hay dùng. "
        "Hãy hỏi con trước khi mở hoặc nhập thông tin."
    ),
    "punycode": (
        "Tên trang web này dùng ký tự lạ, dễ bị nhầm với trang thật. Hãy hỏi con trước khi mở hoặc nhập thông tin."
    ),
    "userinfo": (
        "Đường link này có thêm phần tên đăng nhập đứng trước tên trang web, cách các trang giả mạo hay dùng để "
        "che địa chỉ thật. Hãy hỏi con trước khi mở hoặc nhập thông tin."
    ),
    "shortener": "Đây là đường link rút gọn nên không biết nó dẫn tới đâu. Hãy hỏi con trước khi mở.",
    "brand_lookalike": (
        "Tên trang web nhắc đến ngân hàng hoặc cơ quan nhà nước, nhưng HỏiCon không xác nhận được đây là trang "
        "chính thức. Hãy hỏi con trước khi nhập thông tin."
    ),
    "no_tls": (
        "Trang web này không được mã hóa (http), thông tin nhập vào có thể bị lộ. Hãy hỏi con trước khi nhập thông tin."
    ),
    "no_signal": (
        "HỏiCon chưa thấy dấu hiệu lừa đảo rõ ràng ở đường link này, nhưng chưa thể xác nhận là an toàn. "
        "Vẫn nên hỏi con trước khi nhập thông tin hoặc chuyển tiền."
    ),
}

DOWNLOAD_EXTENSIONS = (".apk", ".xapk", ".apks", ".exe", ".bat", ".scr")
SHORTENERS = frozenset({"bit.ly", "tinyurl.com", "t.ly", "shorturl.at", "is.gd", "cutt.ly", "rb.gy"})
# Tên thương hiệu lấy từ `data/bank_apps.vn.json` (test đối chiếu danh mục) + cơ quan nhà nước hay bị mạo danh.
BANK_BRANDS = (
    "vietcombank", "vcb", "techcombank", "vietinbank", "bidv", "agribank", "mbbank", "mb", "vpbank", "tpbank",
    "sacombank", "acb", "hdbank", "shinhan", "eximbank", "ocb", "msb", "scb", "shb", "lpbank", "seabank",
    "seamobile", "vib", "myvib", "kienlongbank", "liobank", "tnex", "momo", "zalopay", "shopeepay", "vnpay",
    "viettel", "mobifone", "vnpt", "vikki", "digimi", "pvconnect", "tcinvest", "vndirect", "ssi", "ncb",
    "namabank", "bacabank",
)  # fmt: skip
AGENCY_WORDS = ("congan", "bocongan", "thue", "evn", "baohiem", "toaan")
BRAND_KEYWORDS = (*BANK_BRANDS, *AGENCY_WORDS)

_LEVEL_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_LAST3 = re.compile(r"[0-9]{3}")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_NUMERIC_LABEL = re.compile(r"[0-9]+|0x[0-9a-f]+")
_TLD = re.compile(r"[a-z]{2,63}|xn--[a-z0-9-]{1,59}")
_CONTROL = re.compile(r"[\x00-\x20\x7f-\x9f\s]")
_DOWNLOAD = re.compile(
    "(?:" + "|".join(re.escape(ext) for ext in DOWNLOAD_EXTENSIONS) + r")(?=$|[/?&;#=])"
)  # tệp cài đặt ở đường dẫn HOẶC chuỗi truy vấn (…?f=app.apk, app.apk;v=1)


class InvalidUrlError(ValueError):
    """Đường link không phân tích được. Thông điệp cố định, KHÔNG lặp lại đầu vào (có thể chứa số điện thoại/OTP)."""


@dataclass(frozen=True)
class Decision:
    """Kết luận tất định: không chứa h1, HMAC, URL hay host."""

    kind: str
    verdict: str
    confidence: float
    code: str
    floor: str | None
    sources: tuple[dict[str, str], ...]
    list_version: str | None = None
    is_demo: bool = False

    @property
    def reasons(self) -> list[dict[str, str]]:
        return [{"code": self.code, "text": REASONS[self.code]}]


@dataclass(frozen=True)
class Outcome:
    """Kết luận + chủ thể đã băm `(kid, HMAC)` để ghi `verifications`. `repr` không in `subject`/`last3`."""

    decision: Decision
    subject: tuple[int, str]
    last3: str | None = None

    def __repr__(self) -> str:
        return f"Outcome(kind={self.decision.kind}, verdict={self.decision.verdict}, code={self.decision.code})"


def raise_level(current: str, floor: str | None) -> str:
    """Mức sau khi gộp sàn của một kết luận: chỉ NÂNG (luật 5)."""
    if floor is None or _LEVEL_RANK.get(floor, 0) <= _LEVEL_RANK.get(current, 0):
        return current
    return floor


def decide_phone(threat: ThreatVerdict) -> Decision:
    if threat.verdict == "flagged":
        high = threat.confidence >= HIGH_CONFIDENCE
        source = {"name": threat.source or LIST_NAME, "type": "threat_list", "list_version": threat.list_version}
        return Decision(
            kind="phone",
            verdict="dangerous" if high else "warning",
            confidence=threat.confidence,
            code="listed_high" if high else "listed_low",
            floor="critical" if high else "high",
            sources=(source,),
            list_version=threat.list_version,
            is_demo=threat.is_demo,
        )
    cited = () if threat.list_version == NO_LIST_VERSION else (
        {"name": LIST_NAME, "type": "threat_list", "list_version": threat.list_version},
    )  # fmt: skip
    return Decision(
        kind="phone",
        verdict="unknown",
        confidence=0.0,
        code="not_listed",
        floor=None,
        sources=cited,
        list_version=threat.list_version,
    )


async def verify_phone(session: AsyncSession, h1: str, last3: str) -> Outcome:
    """Tra h1 trong danh sách đe dọa (dùng lại `lookup_h1`, không viết truy vấn mới). h1/last3 sai ⇒ ValueError."""
    if not _LAST3.fullmatch(last3):
        raise ValueError("last3 phải đúng 3 chữ số")
    threat = await lookup_h1(session, h1)  # h1 sai định dạng ⇒ ValueError ở đây
    return Outcome(decision=decide_phone(threat), subject=hmac_h1(h1), last3=last3)


def _is_ip_like(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return all(_NUMERIC_LABEL.fullmatch(label) for label in host.split("."))  # 3232235777, 0x7f000001, 0300.0.0.1
    return True


def _normalise_host(raw: str | None) -> str:
    if not raw:
        raise InvalidUrlError("đường link không hợp lệ")
    host = raw.rstrip(".")
    if not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")  # IDNA: tên tiếng Việt có dấu ⇒ xn--…
        except UnicodeError:
            raise InvalidUrlError("đường link không hợp lệ") from None
    host = host.lower()
    if len(host) > 253:
        raise InvalidUrlError("đường link không hợp lệ")
    if _is_ip_like(host):
        return host
    labels = host.split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels) or not _TLD.fullmatch(labels[-1]):
        raise InvalidUrlError("đường link không hợp lệ")
    return host


def _inspect_url(url: str) -> tuple[str, bool, bool, bool]:
    """(host đã chuẩn hóa, http thuần, tệp cài đặt, có userinfo). Mọi phần khác của URL bị bỏ ở đây.

    Trình duyệt coi `\\` như `/` (WHATWG) còn `urlsplit` thì không: đổi trước khi tách để host ta xét trùng host
    người dùng thực sự được đưa tới (`https://bit.ly\\@x.org` đi tới bit.ly, không phải x.org)."""
    text = url.strip()
    if not text or len(text) > MAX_URL_LENGTH or _CONTROL.search(text.replace("\\", "/")):
        raise InvalidUrlError("đường link không hợp lệ")
    text = text.replace("\\", "/")
    explicit = "://" in text
    try:
        parts = urlsplit(text if explicit else f"//{text}")
        raw_host = parts.hostname
    except ValueError:
        raise InvalidUrlError("đường link không hợp lệ") from None
    scheme = parts.scheme.lower() if explicit else ""
    if explicit and scheme not in {"http", "https"}:
        raise InvalidUrlError("đường link không hợp lệ")
    host = _normalise_host(raw_host)
    target = unquote(f"{parts.path}?{parts.query}").lower()
    return host, scheme == "http", _DOWNLOAD.search(target) is not None, "@" in parts.netloc


def _brand_in(host: str) -> bool:
    tokens = [t for t in re.split(r"[.\-_]", host) if t]
    for keyword in BRAND_KEYWORDS:
        if len(keyword) >= 4:
            if any(keyword in token for token in tokens):
                return True
        elif len(keyword) == 3:
            if any(token.startswith(keyword) for token in tokens):
                return True
        elif keyword in tokens:  # 2 chữ ("mb"): phải là cả một đoạn
            return True
    return False


def _url_decision(host: str, plain_http: bool, downloadable: bool, userinfo: bool) -> Decision:
    if downloadable:
        verdict, floor, code, confidence = "dangerous", "critical", "app_download", URL_STRONG_CONFIDENCE
    elif _is_ip_like(host):
        verdict, floor, code, confidence = "warning", "high", "ip_host", URL_WEAK_CONFIDENCE
    elif any(label.startswith("xn--") for label in host.split(".")):
        verdict, floor, code, confidence = "warning", "high", "punycode", URL_WEAK_CONFIDENCE
    elif host in SHORTENERS:
        verdict, floor, code, confidence = "warning", "high", "shortener", URL_WEAK_CONFIDENCE
    elif userinfo:
        verdict, floor, code, confidence = "warning", "high", "userinfo", URL_WEAK_CONFIDENCE
    elif _brand_in(host):
        verdict, floor, code, confidence = "warning", "high", "brand_lookalike", URL_WEAK_CONFIDENCE
    elif plain_http:
        verdict, floor, code, confidence = "warning", "high", "no_tls", URL_WEAK_CONFIDENCE
    else:
        verdict, floor, code, confidence = "unknown", None, "no_signal", 0.0
    return Decision(
        kind="url",
        verdict=verdict,
        confidence=confidence,
        code=code,
        floor=floor,
        sources=({"name": f"Quy tắc HỏiCon: {code}", "type": "heuristic"},),
    )


def verify_url(url: str) -> Outcome:
    """Phân tích URL tại chỗ (không I/O) ⇒ kết luận + `HMAC(pepper, SHA-256("hoicon:url:v1:" + host))`."""
    host, plain_http, downloadable, userinfo = _inspect_url(url)
    digest = hashlib.sha256(b"hoicon:url:v1:" + host.encode("ascii")).hexdigest()
    return Outcome(decision=_url_decision(host, plain_http, downloadable, userinfo), subject=hmac_h1(digest))


async def record(
    session: AsyncSession,
    *,
    family_id: uuid.UUID,
    incident_id: uuid.UUID | None,
    actor: str,
    actor_id: uuid.UUID | None,
    via: str,
    outcome: Outcome,
) -> uuid.UUID | None:
    """Ghi một dòng `verifications` (cùng giao dịch với người gọi). `None` ⇒ trùng dòng `via = 'call'` đã có."""
    decision = outcome.decision
    values: dict[str, Any] = {
        "id": new_id(),
        "family_id": family_id,
        "incident_id": incident_id,
        "actor": actor,
        "actor_id": actor_id,
        "kind": decision.kind,
        "via": via,
        "subject_kid": outcome.subject[0],
        "subject_hmac": outcome.subject[1],
        "last3": outcome.last3,
        "verdict": decision.verdict,
        "confidence": decision.confidence,
        "sources": list(decision.sources),
        "list_version": decision.list_version,
        "is_demo": decision.is_demo,
    }
    statement = insert(Verification).values(**values).on_conflict_do_nothing().returning(Verification.id)
    return await session.scalar(statement)


def result_payload(verification_id: uuid.UUID, decision: Decision, incident_level: str | None) -> dict[str, Any]:
    """Thân phản hồi `lookup_result.v1` (không có h1, HMAC, URL)."""
    payload: dict[str, Any] = {
        "verification_id": str(verification_id),
        "kind": decision.kind,
        "verdict": decision.verdict,
        "confidence": decision.confidence,
        "reasons": decision.reasons,
        "sources": [dict(source) for source in decision.sources],
        "disclaimer": DISCLAIMER,
        "is_demo": decision.is_demo,
    }
    if incident_level is not None:
        payload["incident_level"] = incident_level
    return payload
