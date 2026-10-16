"""Bảng kết luận tất định của `VerificationService` (spec 026 FR-004, plan §4). Không LLM, không bao giờ `safe`."""

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path

import pytest

from hoicon.config import get_settings
from hoicon.domain.pii import hmac_h1
from hoicon.eval.checks import PANIC_PHRASES
from hoicon.mcp_servers.threat import ThreatVerdict
from hoicon.services import verification_service as vs
from hoicon.services.verification_service import (
    BRAND_KEYWORDS,
    DISCLAIMER,
    REASONS,
    InvalidUrlError,
    decide_phone,
    verify_url,
)

BANK_APPS = Path(__file__).resolve().parents[3] / "data" / "bank_apps.vn.json"
FAKE_PHONE_IN_URL = "0900000123"  # số hư cấu


@pytest.fixture(autouse=True)
def pepper(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "1")
    yield
    get_settings.cache_clear()


def flagged(confidence: float, *, demo: bool = False) -> ThreatVerdict:
    return ThreatVerdict(
        verdict="flagged",
        source="Nguồn thử nghiệm",
        confidence=confidence,
        tactic="impersonation_authority",
        list_version="v-test",
        is_demo=demo,
    )


UNKNOWN = ThreatVerdict(verdict="unknown", list_version="v-test")


# ---- phone ----


@pytest.mark.parametrize(
    ("confidence", "verdict", "floor", "code"),
    [
        (0.70, "dangerous", "critical", "listed_high"),
        (0.95, "dangerous", "critical", "listed_high"),
        (1.0, "dangerous", "critical", "listed_high"),
        (0.69, "warning", "high", "listed_low"),
        (0.30, "warning", "high", "listed_low"),
        (0.0, "warning", "high", "listed_low"),
    ],
)
def test_flagged_phone_follows_the_confidence_threshold(confidence: float, verdict: str, floor: str, code: str) -> None:
    decision = decide_phone(flagged(confidence))
    assert (decision.verdict, decision.floor, decision.code) == (verdict, floor, code)
    assert decision.confidence == confidence
    assert decision.kind == "phone"


def test_unknown_phone_is_unknown_and_never_raises_the_level() -> None:
    decision = decide_phone(UNKNOWN)
    assert (decision.verdict, decision.floor, decision.code, decision.confidence) == (
        "unknown",
        None,
        "not_listed",
        0.0,
    )
    assert decision.list_version == "v-test"


@pytest.mark.parametrize("confidence", [i / 100 for i in range(0, 101, 5)])
def test_phone_is_never_safe_at_any_confidence(confidence: float) -> None:
    assert decide_phone(flagged(confidence)).verdict in {"dangerous", "warning"}
    assert decide_phone(UNKNOWN).verdict == "unknown"


def test_flagged_phone_cites_the_list_it_came_from() -> None:
    decision = decide_phone(flagged(0.9))
    assert decision.sources == ({"name": "Nguồn thử nghiệm", "type": "threat_list", "list_version": "v-test"},)


def test_unknown_phone_cites_the_list_it_was_checked_against() -> None:
    (source,) = decide_phone(UNKNOWN).sources
    assert source["type"] == "threat_list"
    assert source["list_version"] == "v-test"


def test_unknown_phone_with_an_empty_list_cites_nothing() -> None:
    assert decide_phone(ThreatVerdict(verdict="unknown", list_version="none")).sources == ()


def test_demo_rows_are_marked_demo() -> None:
    assert decide_phone(flagged(0.9, demo=True)).is_demo is True
    assert decide_phone(flagged(0.9)).is_demo is False


# ---- url: bảng quy tắc ----


@pytest.mark.parametrize("ext", [".apk", ".xapk", ".apks", ".exe", ".bat", ".scr", ".APK"])
def test_downloadable_app_is_dangerous(ext: str) -> None:
    outcome = verify_url(f"https://tai-ung-dung.example/tải/bidv{ext}")
    assert (outcome.decision.verdict, outcome.decision.floor, outcome.decision.code) == (
        "dangerous",
        "critical",
        "app_download",
    )
    assert outcome.decision.confidence == 0.9


def test_extension_is_read_from_the_path_and_the_query_but_not_the_middle_of_a_word() -> None:
    assert verify_url("https://cua-hang.example/trang?file=a.apk").decision.code == "app_download"  # review 026 #1
    assert verify_url("https://cua-hang.example/a.apk?x=1#frag").decision.code == "app_download"
    assert verify_url("https://cua-hang.example/a.apk.html").decision.verdict != "dangerous"
    assert verify_url("https://cua-hang.example/trang?file=a.apkx").decision.verdict != "dangerous"


@pytest.mark.parametrize("url", ["http://192.0.2.10/dang-nhap", "https://[2001:db8::1]/x", "http://3232235777/x"])
def test_ip_host_is_a_warning(url: str) -> None:
    decision = verify_url(url).decision
    assert (decision.verdict, decision.floor, decision.code, decision.confidence) == ("warning", "high", "ip_host", 0.6)


def test_punycode_host_is_a_warning() -> None:
    assert verify_url("https://xn--ngnhng-abc.example/x").decision.code == "punycode"


def test_vietnamese_idn_is_normalised_to_punycode_and_flagged() -> None:
    outcome = verify_url("https://ngân-hàng-việt.example/chào")
    assert outcome.decision.code == "punycode"
    assert outcome.decision.verdict == "warning"


@pytest.mark.parametrize(
    "host", ["bit.ly", "tinyurl.com", "t.ly", "shorturl.at", "is.gd", "cutt.ly", "rb.gy", "BIT.LY"]
)
def test_url_shorteners_are_warnings(host: str) -> None:
    decision = verify_url(f"https://{host}/abc123").decision
    assert (decision.verdict, decision.floor, decision.code) == ("warning", "high", "shortener")


@pytest.mark.parametrize(
    "host",
    [
        "vietcombank-xacthuc.example",
        "vcb-digibank.example",
        "congan-phatnguoi.example",
        "bocongan.example",
        "thue-hoantien.example",
        "evnhanoi.example",
        "baohiem-xahoi.example",
        "toaan-trieutap.example",
        "mbbank.example",
    ],
)
def test_bank_or_agency_lookalike_is_a_warning(host: str) -> None:
    decision = verify_url(f"https://{host}/nhan").decision
    assert (decision.verdict, decision.floor, decision.code, decision.confidence) == (
        "warning",
        "high",
        "brand_lookalike",
        0.6,
    )


def test_every_bank_app_in_the_catalogue_has_a_matching_keyword() -> None:
    """Danh mục `bank_apps.vn.json` đổi ⇒ test này nhắc cập nhật `BRAND_KEYWORDS`."""

    def fold(text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
        return "".join(c for c in decomposed if unicodedata.category(c) != "Mn").lower()

    skipped = {"co", "di", "nam", "ngan", "ung", "bac", "cake", "timo", "vps", "mbs"}
    apps = json.loads(BANK_APPS.read_text(encoding="utf-8"))["apps"]
    missing = []
    for app in apps:
        tokens = re.findall(r"[a-z0-9]+", fold(app["name"]))
        brand = tokens[0] if tokens else ""
        if brand in skipped or "hoicon" in fold(app["name"]):
            continue
        if verify_url(f"https://{brand}-xacthuc.example/").decision.code != "brand_lookalike":
            missing.append(app["name"])
    assert missing == []
    assert len(set(BRAND_KEYWORDS)) == len(BRAND_KEYWORDS)


def test_plain_http_without_other_signals_is_a_no_tls_warning() -> None:
    decision = verify_url("http://cua-hang-hoa-qua.example/gio-hang").decision
    assert (decision.verdict, decision.floor, decision.code) == ("warning", "high", "no_tls")


def test_https_without_signals_is_unknown_not_safe() -> None:
    decision = verify_url("https://cua-hang-hoa-qua.example/gio-hang").decision
    assert (decision.verdict, decision.floor, decision.code, decision.confidence) == ("unknown", None, "no_signal", 0.0)


def test_url_without_a_scheme_is_inspected_and_is_not_flagged_for_tls() -> None:
    assert verify_url("cua-hang-hoa-qua.example/gio-hang").decision.code == "no_signal"
    assert verify_url("bit.ly/abc").decision.code == "shortener"
    assert verify_url("bit.ly:8080/abc").decision.code == "shortener"


def test_rules_are_applied_top_down_first_match_wins() -> None:
    # vừa là tệp .apk, vừa là link rút gọn, vừa là http ⇒ dòng đầu tiên (app_download)
    assert verify_url("http://bit.ly/bidv.apk").decision.code == "app_download"
    # vừa rút gọn vừa http ⇒ shortener đứng trước no_tls
    assert verify_url("http://bit.ly/abc").decision.code == "shortener"
    # brand đứng trước no_tls
    assert verify_url("http://vcb-khuyen-mai.example/").decision.code == "brand_lookalike"


@pytest.mark.parametrize("url", [d for d in ("https://a.example/", "http://b.example/x.apk", "http://1.2.3.4/")])
def test_url_is_never_safe(url: str) -> None:
    assert verify_url(url).decision.verdict != "safe"


# ---- url: riêng tư ----


def test_only_the_host_is_hashed() -> None:
    plain = verify_url("https://cua-hang-hoa-qua.example/").subject
    noisy = verify_url(
        f"https://nguoi:matkhau@Cua-Hang-Hoa-Qua.EXAMPLE.:8443/gio-hang?sdt={FAKE_PHONE_IN_URL}&otp=123456#neo"
    ).subject
    assert noisy == plain
    host_digest = hashlib.sha256(b"hoicon:url:v1:cua-hang-hoa-qua.example").hexdigest()
    assert plain == hmac_h1(host_digest)


def test_nothing_from_path_query_or_credentials_survives_in_the_outcome() -> None:
    outcome = verify_url(
        f"https://nguoi:matkhau@cua-hang.example/bidv/{FAKE_PHONE_IN_URL}?token=abc123XYZ&sdt={FAKE_PHONE_IN_URL}"
    )
    blob = (
        repr(outcome) + json.dumps(outcome.decision.reasons, ensure_ascii=False) + json.dumps(outcome.decision.sources)
    )
    for needle in ("nguoi", "matkhau", FAKE_PHONE_IN_URL, "abc123XYZ", "token", "/bidv", "cua-hang.example"):
        assert needle not in blob


def test_userinfo_cannot_spoof_the_host() -> None:
    # `bidv.com.vn@xn--evil.example` thật sự trỏ tới xn--evil.example
    assert verify_url("https://bidv.com.vn@xn--evil.example/").decision.code == "punycode"


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://bit.ly\\@example.org/", "shortener"),  # trình duyệt coi \ là /: đích thật là bit.ly
        ("http://203.0.113.5\\@example.org/", "ip_host"),
        ("https://bit.ly%5c@example.org/", None),  # %5c trong authority: không được "lành" đi
        ("https://vietcombank.vn@evil.example/", "userinfo"),  # tên ngân hàng nằm trong userinfo
        ("https://shop.example/tai?f=app.apk", "app_download"),
        ("https://shop.example/app.apk;v=1", "app_download"),
        ("https://shop.example/app.apk?x=1#a", "app_download"),
        ("https://shop.example/files/app.APK/", "app_download"),
    ],
)  # fmt: skip
def test_browser_style_parsing_cannot_hide_a_signal(url: str, code: str | None) -> None:
    try:
        decision = verify_url(url).decision
    except InvalidUrlError:
        assert code is None  # từ chối hẳn cũng được: không bao giờ ra kết luận "lành"
        return
    assert decision.verdict != "unknown"
    if code is not None:
        assert decision.code == code


def test_plain_userinfo_on_a_plain_host_is_still_flagged() -> None:
    decision = verify_url("https://nguoi:matkhau@cua-hang.example/").decision
    assert (decision.code, decision.verdict, decision.floor) == ("userinfo", "warning", "high")


def test_host_hash_uses_a_domain_prefix_distinct_from_phone_h1() -> None:
    host = "cua-hang-hoa-qua.example"
    assert verify_url(f"https://{host}/").subject != hmac_h1(hashlib.sha256(host.encode()).hexdigest())
    assert verify_url(f"https://{host}/").subject != hmac_h1(hashlib.sha256(b"hoicon:v1:" + host.encode()).hexdigest())


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "http://", "https:///path", "javascript:alert(1)", "ftp://a.example/x", "http://exa mple.com", "a.b",
     "http://" + "a" * 300 + ".example", "https://.example/", "http://a..example/"],
)  # fmt: skip
def test_unparseable_urls_are_rejected_without_echoing_the_input(bad: str) -> None:
    with pytest.raises(InvalidUrlError) as excinfo:
        verify_url(bad)
    assert bad.strip() == "" or bad not in str(excinfo.value)


# ---- câu chữ ----


def test_every_reason_code_has_a_text_and_no_panic_wording() -> None:
    assert set(REASONS) >= {
        "listed_high",
        "listed_low",
        "not_listed",
        "app_download",
        "ip_host",
        "punycode",
        "shortener",
        "brand_lookalike",
        "no_tls",
        "no_signal",
    }
    for code, text in REASONS.items():
        folded = unicodedata.normalize("NFC", text).lower()
        assert not any(p in folded for p in PANIC_PHRASES), code
        assert text.strip() and len(text) <= 400
        assert not re.search(r"\d{4}", text), code  # không chữ số dài (mask_text sẽ che)


def test_disclaimer_opens_with_the_ai_disclosure() -> None:
    assert DISCLAIMER.startswith("Đây là trợ lý AI HỏiCon.")
    assert len(DISCLAIMER) <= 400


def test_every_decision_is_phrased_from_the_reason_table() -> None:
    for decision in (
        decide_phone(flagged(0.9)),
        decide_phone(flagged(0.5)),
        decide_phone(UNKNOWN),
        verify_url("https://x-thue.example/").decision,
    ):
        (reason,) = decision.reasons
        assert reason == {"code": decision.code, "text": REASONS[decision.code]}


def test_service_never_calls_an_llm() -> None:
    source = Path(vs.__file__).read_text(encoding="utf-8")
    assert "llm_router" not in source
    assert "anthropic" not in source.lower()
