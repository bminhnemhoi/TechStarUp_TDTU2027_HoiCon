"""Spec 032 FR-003/005/007: mẫu tin Coach — công khai AI, không khẳng định "an toàn", độ phủ làm tròn, không số dài."""

import re

import pytest

from hoicon.agents import texts
from hoicon.agents.texts import AI_DISCLOSURE
from hoicon.domain.pii import mask_text
from hoicon.eval.checks import PANIC_PHRASES, REFUND_PHRASES

ALIAS = "Mẹ"
SAFE_CLAIM = re.compile(r"an toàn", re.IGNORECASE)  # không khẳng định; mẫu phủ định nếu cần phải được duyệt riêng
LONG_DIGITS = re.compile(r"\d{4,}")


def all_messages() -> dict[str, str]:
    base = {
        "silent": texts.guardian_protection_silent(ALIAS, "07:30 ngày 20 tháng 10"),
        "permission_off": texts.guardian_protection_permission_off(ALIAS),
        "off_ack": texts.digest_off_ack(),
        "on_ack": texts.digest_on_ack(),
    }
    digests = {
        "digest_incident": texts.weekly_digest(ALIAS, 2, 1, 0.9, 1, "Cúp máy rồi gọi lại bằng số đã lưu."),
        "digest_quiet": texts.weekly_digest(ALIAS, 0, 0, 1.0, 0, None),
        "digest_no_data": texts.weekly_digest(ALIAS, 0, 0, None, 0, None),
        "digest_incident_no_data": texts.weekly_digest(ALIAS, 1, 0, None, 3, None),
    }
    return {**base, **digests}


@pytest.mark.parametrize("name", list(all_messages()))
def test_every_message_opens_with_the_ai_disclosure(name: str) -> None:
    assert all_messages()[name].startswith(AI_DISCLOSURE)


@pytest.mark.parametrize("name", list(all_messages()))
def test_no_affirmative_safety_claim_no_panic_no_refund_no_hack(name: str) -> None:
    text = all_messages()[name]
    assert not SAFE_CLAIM.search(text), text
    lowered = text.lower()
    for phrase in (*PANIC_PHRASES, *REFUND_PHRASES, "bị hack", "bị chiếm"):
        assert phrase not in lowered, (name, phrase)


@pytest.mark.parametrize("name", list(all_messages()))
def test_no_long_digit_run_and_masking_changes_nothing(name: str) -> None:
    text = all_messages()[name]
    assert not LONG_DIGITS.search(text)
    assert mask_text(text) == text


@pytest.mark.parametrize(
    ("raw", "shown"), [(0.0, 0), (0.62, 60), (0.63, 65), (0.874, 85), (0.876, 90), (1.0, 100), (1.4, 100)]
)
def test_coverage_is_rounded_to_five_percent(raw: float, shown: int) -> None:
    assert texts.round_coverage(raw) == shown
    assert f"khoảng {shown}%" in texts.weekly_digest(ALIAS, 0, 0, raw, 0, None)


def test_a_quiet_week_never_says_safe_and_always_gives_the_coverage() -> None:
    text = texts.weekly_digest(ALIAS, 0, 0, 0.4, 0, None)
    assert "không thấy dấu hiệu đáng ngờ nào" in text and "khoảng 40%" in text


def test_missing_coverage_says_there_is_not_enough_data() -> None:
    assert "chưa có số liệu để tóm tắt" in texts.weekly_digest(ALIAS, 0, 0, None, 0, None)
    assert "khoảng" not in texts.weekly_digest(ALIAS, 0, 0, None, 0, None)


def test_the_digest_ends_with_the_opt_out_and_includes_the_tip_only_when_given() -> None:
    with_tip = texts.weekly_digest(ALIAS, 0, 0, 1.0, 0, "Một mẹo.")
    assert (
        with_tip.rstrip().endswith("Nhắn TẮT TIN TUẦN để ngừng nhận bản tin này.")
        and "Mẹo tuần này: Một mẹo." in with_tip
    )
    assert "Mẹo" not in texts.weekly_digest(ALIAS, 0, 0, 1.0, 0, None)


def test_the_opt_out_ack_says_alerts_keep_coming() -> None:
    assert "HỏiCon vẫn nhắn cho anh/chị ngay" in texts.digest_off_ack()
    assert "BẬT TIN TUẦN" in texts.digest_off_ack() and "TẮT TIN TUẦN" in texts.digest_on_ack()


def test_protection_messages_state_the_known_fact_a_possible_cause_and_one_action() -> None:
    silent = texts.guardian_protection_silent(ALIAS, "07:30 ngày 20 tháng 10")
    assert "chưa báo về HỏiCon từ 07:30 ngày 20 tháng 10" in silent and "Có thể" in silent and "gọi hỏi thăm" in silent
    off = texts.guardian_protection_permission_off(ALIAS)
    assert "quyền" in off and "đang bị tắt" in off and "gọi hỏi thăm" in off


def test_digest_gives_a_next_step_when_there_were_incidents_or_low_coverage() -> None:
    assert "hỏi thăm" in texts.weekly_digest(ALIAS, 2, 1, 1.0, 0, None)
    assert "mở lại ứng dụng" in texts.weekly_digest(ALIAS, 0, 0, 0.5, 0, None)
    assert "mở lại ứng dụng" not in texts.weekly_digest(ALIAS, 0, 0, 0.9, 0, None)
