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


@pytest.mark.parametrize(
    "raw", ["0900000123 tr", "0900000123 k", "0900 000 123 ty", "1234567890123 đồng", "0900000123 đ"]
)
def test_a_long_number_is_not_excused_by_a_trailing_money_unit(raw: str) -> None:
    assert not re.search(r"\d{4}", mask_text(f"chuyển {raw}"))


@pytest.mark.parametrize(
    "raw", ["20.000.000 đồng", "1.500.000.000 đồng", "50.000₫", "500000 đồng", "50k", "2 tỷ", "300 nghìn"]
)
def test_real_money_amounts_are_kept(raw: str) -> None:
    assert raw in mask_text(f"phí {raw}")


@pytest.mark.parametrize(
    "raw",
    [
        "900000123 k",  # 9 chữ số, bỏ số 0 đầu
        "900000123 đồng",
        "0.900.000.123 đ",  # nhóm nghìn giả, bắt đầu bằng 0
        "090.000.123 đ",
        "0,900,000,123 k",
        "84900000123 tr",
        "+84900000123 tr",
        "1.234.567.890.123 k",  # số tài khoản 13 chữ số
        "912345678 vnd",
    ],
)
def test_phone_and_account_numbers_dressed_as_money_are_masked(raw: str) -> None:
    assert len(re.sub(r"\D", "", mask_text(f"chuyển {raw}"))) <= 3, raw  # chỉ còn 3 số cuối trong nhãn


def test_fuzz_no_phone_survives_a_money_unit() -> None:
    import random

    rng = random.Random(25)  # noqa: S311 — dữ liệu thử, không phải mật mã
    units = ["k", "tr", "đ", "đồng", "vnd", "ty", "nghìn", "triệu"]
    for _ in range(3000):
        tail = "".join(rng.choice("0123456789") for _ in range(8))
        number = rng.choice(["09", "03", "07", "08", "05"]) + tail
        forms = [number, number[1:], "84" + number[1:], "+84" + number[1:]]
        raw = rng.choice(forms)
        if rng.random() < 0.5:  # chèn dấu nhóm
            raw = ".".join(
                raw[max(0, i - 3) : i] for i in range(len(raw) % 3 or 3, len(raw) + 3, 3) if raw[max(0, i - 3) : i]
            )
        text = f"gửi {raw} {rng.choice(units)}"
        assert len(re.sub(r"\D", "", mask_text(text))) <= 3, text


@pytest.mark.parametrize(
    "raw", ["1500000000 đ", "1000000000 đồng", "2000000000 đồng", "12345678 đ", "2,5 triệu", "20k"]
)
def test_large_real_amounts_are_kept(raw: str) -> None:
    assert raw in mask_text(f"đòi {raw}")
