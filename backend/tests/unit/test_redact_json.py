"""`redact_json` (spec 025, FR-002): lớp che thứ hai cho dữ liệu bước tác tử trước khi ra khỏi máy chủ."""

import re

import pytest

from hoicon.domain.pii import TRACE_DENY_KEYS, redact_json

HEX64 = "0123456789abcdef" * 4  # chuỗi hư cấu có hình dạng của h1/HMAC
TOKEN43 = "29KgWDAcHhzTs8TUOPWMx0Odx6Z5vZ0X_TyTcAV6t4M"  # gitleaks:allow — token GIẢ 43 ký tự (hình dạng action token)
FAKE_PHONE = "0900000123"  # số hư cấu


def test_deny_keys_are_dropped_at_any_depth() -> None:
    value = {"level": "high", "a": {"b": [{"h1": "x", "keep": 1, "c": {"phone": "y", "note": "z"}}]}}
    assert redact_json(value) == {"level": "high", "a": {"b": [{"keep": 1, "c": {}}]}}


def test_every_deny_key_is_dropped_case_insensitively() -> None:
    value = {key.upper(): "v" for key in TRACE_DENY_KEYS} | {key: "v" for key in TRACE_DENY_KEYS} | {"ok": 1}
    assert redact_json(value) == {"ok": 1}
    assert {"h1", "hmac", "phone", "token", "note", "text", "input_redacted", "package"} <= TRACE_DENY_KEYS


def test_hex_64_becomes_hash_label() -> None:
    assert redact_json({"ref": HEX64, "also": f"gọi {HEX64} xong"}) == {"ref": "[HASH]", "also": "gọi [HASH] xong"}


def test_hex_of_32_chars_is_still_hash() -> None:
    assert redact_json({"ref": HEX64[:32]}) == {"ref": "[HASH]"}


def test_token_43_becomes_token_label() -> None:
    assert len(TOKEN43) == 43
    assert redact_json({"link": f"/a/{TOKEN43}"}) == {"link": "/a/[TOKEN]"}


def test_fictional_mobile_number_is_masked_with_last_three_digits() -> None:
    assert redact_json({"line": f"gọi {FAKE_PHONE} ngay"}) == {"line": "gọi [SĐT ***123] ngay"}


def test_money_amount_with_unit_is_kept() -> None:
    assert redact_json({"amount": "20.000.000 đồng", "short": "50k"}) == {"amount": "20.000.000 đồng", "short": "50k"}


def test_long_string_is_cut_to_500_characters() -> None:
    result = redact_json({"summary": "chữ " * 600})
    assert len(result["summary"]) == 500


def test_cutting_does_not_leave_a_digit_run_behind() -> None:
    text = "a" * 497 + " 1234567"  # ranh giới cắt rơi giữa dãy số
    assert not re.search(r"\d{4}", redact_json({"x": text})["x"])


@pytest.mark.parametrize(
    "value",
    [
        {"level": "high", "n": 3, "f": 0.5, "ok": True, "none": None, "items": [1, "a", None]},
        {"deep": {"h1": HEX64, "a": [{"b": TOKEN43, "c": f"{FAKE_PHONE} / {HEX64}"}]}},
        {"summary": "x" * 2000},
        {"cut": "a" * 497 + " 1234567", "amount": "20.000.000 đồng", "mask": "[SĐT ***123]"},
        {HEX64: 1, FAKE_PHONE: 2},
    ],
)
def test_redact_json_is_idempotent(value: dict[str, object]) -> None:
    once = redact_json(value)
    assert redact_json(once) == once


def test_none_numbers_and_bools_are_kept_as_they_are() -> None:
    assert redact_json(None) is None
    assert redact_json(7) == 7 and redact_json(1.5) == 1.5
    assert redact_json(True) is True and redact_json(False) is False


def test_keys_are_masked_too() -> None:
    assert redact_json({FAKE_PHONE: 1, HEX64: 2}) == {"[SĐT ***123]": 1, "[HASH]": 2}


def test_does_not_mutate_the_input() -> None:
    value = {"a": {"h1": "x", "b": [FAKE_PHONE]}}
    snapshot = {"a": {"h1": "x", "b": [FAKE_PHONE]}}
    redact_json(value)
    assert value == snapshot


def test_non_json_types_are_turned_into_cleaned_strings() -> None:
    from decimal import Decimal

    assert redact_json({"cost": Decimal("0.5"), "tup": (1, 2)}) == {"cost": "0.5", "tup": [1, 2]}


def test_runaway_nesting_is_cut_not_recursed() -> None:
    value: dict[str, object] = {"leaf": 1}
    for _ in range(100):
        value = {"n": value}
    text = str(redact_json(value))
    assert "leaf" not in text and "[…]" in text


# --- sau review độc lập lượt 1 (spec 025) -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "H1 ",
        "ｈ1",
        "package_name",
        "note_text",
        "caller_phone",
        "zalo_id",
        "packageName",
        "chatId",
        "Phone-Number",
        "x.token.y",
    ],
)
def test_deny_key_variants_are_dropped(key: str) -> None:
    assert redact_json({key: "bí mật", "level": "high"}) == {"level": "high"}


def test_innocent_keys_that_merely_contain_a_deny_word_inside_a_longer_word_stay() -> None:
    assert redact_json({"context": 1, "tokens_in": 2, "textual": 3, "phoneme": 4}) == {
        "context": 1,
        "tokens_in": 2,
        "textual": 3,
        "phoneme": 4,
    }


@pytest.mark.parametrize(
    "text",
    [
        " ".join(HEX64[i : i + 2] for i in range(0, 64, 2)),  # hex ngắt bằng dấu cách
        ":".join(HEX64[i : i + 2] for i in range(0, 64, 2)),  # kiểu vân tay 01:23:45…
        "-".join(HEX64[i : i + 2] for i in range(0, 64, 2)),
    ],
)
def test_separated_hex_is_hashed_whole(text: str) -> None:
    assert redact_json({"fp": text}) == {"fp": "[HASH]"}


def test_mixed_token_of_32_to_39_chars_and_standard_base64_padding_are_masked() -> None:
    short = "aB3dE5gH7jK9mN1pQ3sT5vW7yZ9bC1dE"  # 32 ký tự, có cả chữ lẫn số
    padded = "dGhpcyBpcyBhIHNlY3JldCB0b2tlbiB2YWx1ZQ=="  # base64 chuẩn có '='
    assert redact_json({"a": short, "b": padded}) == {"a": "[TOKEN]", "b": "[TOKEN]"}


def test_snake_case_identifiers_are_not_mistaken_for_tokens() -> None:
    word = "q_caller_authority_unknown_state_x"  # 34 ký tự nhưng không có chữ số
    assert redact_json({"q": word}) == {"q": word}


def test_phone_or_account_followed_by_a_money_unit_is_still_masked() -> None:
    for raw in ("0900000123 tr", "0900000123 k", "0900000123 đ", "0900 000 123 ty", "1234567890123 đồng"):
        masked = redact_json({"x": f"chuyển {raw}"})["x"]
        assert not re.search(r"\d{4}", masked), raw


def test_huge_integers_and_non_finite_floats_become_json_safe_values() -> None:
    import json

    result = redact_json({"big": 10**5000, "nan": float("nan"), "inf": float("inf"), "ok": 2**40})
    assert result["big"] == "[SỐ LỚN]" and result["nan"] is None and result["inf"] is None and result["ok"] == 2**40
    json.dumps(result, allow_nan=False)


# --- sau review độc lập lượt 2 (spec 025) -------------------------------------------------------------------------


def test_real_ask_elder_output_keeps_its_flags() -> None:
    """`note_flags` là cờ tất định (output thật của node ask_elder): bằng chứng vì sao mức rủi ro tăng."""
    output = {"question_id": "q_caller_authority", "answer": "yes", "note_flags": {"mentions_transfer": True}}
    assert redact_json(output) == output


@pytest.mark.parametrize("key", ["text_len", "token_count", "caller_flagged", "zalo_sent", "note_flags", "phone_count"])
def test_counters_and_flags_about_a_sensitive_thing_are_not_dropped(key: str) -> None:
    assert redact_json({key: 3}) == {key: 3}


@pytest.mark.parametrize(
    "key", ["note", "text", "caller", "package_name", "chatId", "zalo_id", "token_value", "note_body"]
)
def test_the_sensitive_things_themselves_are_still_dropped(key: str) -> None:
    assert redact_json({key: "x"}) == {}


def test_identifiers_with_digits_are_not_mistaken_for_tokens() -> None:
    kept = [
        "01a1430a-a6c9-7c3e-9d2b-5f1e8a7b6c40",  # UUID
        "intervention_guardian_brief_prompt_v2_final",
        "elder_confirmed_scam_signal_q1_transfer",
        "risk_scorer@3",
    ]
    assert redact_json({"ids": kept}) == {"ids": kept}
    assert "[TOKEN]" not in redact_json({"v": "v2026-10-16-risk-scorer-prompt-rev3"})["v"]


def test_a_realistic_token_is_still_masked() -> None:
    assert redact_json({"t": f"link {TOKEN43} hết"}) == {"t": "link [TOKEN] hết"}
    assert redact_json({"t": "aB3dE5gH7jK9mN1pQ3sT5vW7yZ9bC1dE"}) == {"t": "[TOKEN]"}


def test_iso_timestamps_survive_but_birth_dates_do_not() -> None:
    stamp = "2026-12-01T02:15:31.000000Z"
    assert redact_json({"at": stamp, "mix": f"lúc {stamp} gọi 0900000123"}) == {
        "at": stamp,
        "mix": f"lúc {stamp} gọi [SĐT ***123]",
    }
    assert "1980" not in redact_json({"dob": "sinh ngày 1980-05-12"})["dob"]


def test_pairs_of_plain_digits_are_not_a_hash() -> None:
    text = " ".join(f"{i:02d}" for i in range(10, 27))  # 17 cặp chữ số, không có a–f
    assert "[HASH]" not in redact_json({"x": text})["x"]


# --- sau review độc lập lượt 3 (spec 025) -------------------------------------------------------------------------


def _digits_left(text: object) -> int:
    return len(re.sub(r"\D", "", str(text)))


def test_uuid_and_timestamp_shapes_cannot_smuggle_a_number() -> None:
    for sneaky in (
        "00000000-0000-1000-8000-090000012345",  # 12 chữ số cuối là số điện thoại
        "2026-12-01T00:00:00.0900000123",
        "2026-12-01T00:00:00.09000001230900000124Z",
    ):
        shown = redact_json({"x": sneaky})["x"].replace("2026-12-01T00:00:00", "")  # bỏ phần mốc giờ hợp lệ
        assert _digits_left(shown) <= 6, sneaky
    real_uuid = "01a1430a-a6c9-7c3e-9d2b-5f1e8a7b6c40"
    assert redact_json({"x": real_uuid}) == {"x": real_uuid}
    assert redact_json({"x": "2026-12-01T02:15:31.123456Z"}) == {"x": "2026-12-01T02:15:31.123456Z"}


def test_random_urlsafe_tokens_are_always_masked() -> None:
    import secrets

    for size in (24, 28, 32, 40):  # 32, 38, 43, 54 ký tự
        for _ in range(2000):
            token = secrets.token_urlsafe(size)
            assert redact_json({"v": f"x {token} y"}) == {"v": "x [TOKEN] y"}, token


@pytest.mark.parametrize(
    "key", ["phone_type", "token_kind", "note_count", "text_flags", "h1_type", "caller_type", "package_kind"]
)
def test_flag_style_keys_only_keep_flag_like_values(key: str) -> None:
    assert redact_json({key: "Nguyễn Văn A, 0900000123, h1 abc"}) == {}
    assert redact_json({key: {"nested": "Nguyễn Văn A"}}) == {}
    assert redact_json({key: 3}) == {key: 3}
    assert redact_json({key: True}) == {key: True}
    assert redact_json({key: "transfer_mentioned"}) == {key: "transfer_mentioned"}
    assert redact_json({key: {"a": True, "b": 2}}) == {key: {"a": True, "b": 2}}


def test_vietnamese_decimals_and_lists_are_not_swallowed_but_thousand_groups_are() -> None:
    from hoicon.domain.pii import mask_text

    assert mask_text("bước 1,2,3,4,5 là") == "bước 1,2,3,4,5 là"
    assert mask_text("tỷ lệ 3,14 và 12,34%") == "tỷ lệ 3,14 và 12,34%"
    assert _digits_left(mask_text("gọi 0,900,000,123 nhé")) <= 3
    assert "1,500,000 đồng" in mask_text("phí 1,500,000 đồng")
