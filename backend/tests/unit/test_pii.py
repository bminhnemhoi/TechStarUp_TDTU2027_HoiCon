"""Che/giảm thiểu PII (CLAUDE.md luật 1). Số trong file này là số hư cấu (data/fixtures/phones.json)."""

import re

import pytest

from hoicon.config import get_settings
from hoicon.domain.pii import hmac_h1, mask_text, note_flags

H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"


@pytest.mark.parametrize(
    "raw",
    ["0900000001", "090 000 0001", "090.000.0001", "(090) 000-0001", "+84 900 000 001", "84900000001", "SĐT0900000001"],
)
def test_phone_numbers_are_masked_keeping_last3(raw: str) -> None:
    masked = mask_text(f"Họ gọi từ số {raw} bảo chuyển tiền")
    assert "[SĐT ***001]" in masked
    assert not re.search(r"\d{4}", masked.replace("***001", "")), masked


@pytest.mark.parametrize(
    "text",
    [
        "mã OTP là 482913",
        "OTP123456",
        "OTP: 123 456",
        "Mã OTP là 4 8 2 9 1 3",
        "482913 la ma OTP",
        "mật khẩu 4829",
        "chuyển vào STK 1903 5678 9012 345",
        "stk1903567890123",
        "STK 12345678",
        "STK 1903_5678/9012",
        "CCCD 001190012345",
        "sinh ngày 12/03/1955",
    ],
)
def test_codes_accounts_and_ids_leave_no_digit_runs(text: str) -> None:
    masked = mask_text(text)
    assert not re.search(r"\d(?:[\s.\-_/()]*\d){3,}", masked.replace("***", "")), masked


def test_email_masked_and_amounts_with_unit_kept() -> None:
    masked = mask_text("gửi tới a.b+c@example.com 20.000.000 đồng, phí 50.000₫")
    assert "[EMAIL]" in masked
    assert "20.000.000 đồng" in masked and "50.000₫" in masked


def test_note_flags_match_with_or_without_diacritics() -> None:
    flags = note_flags("Ho noi la CONG AN, bảo tôi chuyển tiền và đọc mã OTP, đừng nói với ai")
    assert flags == {
        "mentions_authority": True,
        "mentions_transfer": True,
        "mentions_code": True,
        "mentions_secrecy": True,
        "mentions_app_or_link": False,
    }
    assert not any(note_flags("Cháu gọi hỏi thăm sức khỏe").values())


def test_hmac_h1_needs_pepper_and_valid_h1(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    try:
        kid, digest = hmac_h1(H1)
        assert kid == 1 and len(digest) == 64 and digest != H1
        assert hmac_h1(H1) == (kid, digest)  # tất định để so khớp
        with pytest.raises(ValueError):
            hmac_h1("0900000001")  # số thô không bao giờ được băm ở máy chủ
    finally:
        get_settings.cache_clear()


def test_hmac_h1_without_pepper_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "9")
    try:
        with pytest.raises(RuntimeError):
            hmac_h1(H1)
    finally:
        get_settings.cache_clear()
