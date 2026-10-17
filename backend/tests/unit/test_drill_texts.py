"""Spec 028 FR-006, SC-001: tin tổng kết bài luyện tập — luôn công khai AI, luôn [DIỄN TẬP], giọng ấm áp."""

import pytest

from hoicon.agents import texts
from hoicon.domain import drill as dr
from hoicon.eval.checks import PANIC_PHRASES, REFUND_PHRASES

FLAGS = ["Gọi điện rồi gửi link lạ", "Xin mã OTP"]


@pytest.mark.parametrize("passed", [True, False, None], ids=["passed", "failed", "aborted"])
def test_every_debrief_opens_with_the_ai_disclosure_then_the_drill_label(passed: bool | None) -> None:
    text = texts.drill_debrief("Mẹ", passed, FLAGS)
    assert text.startswith(texts.AI_DISCLOSURE)
    assert text.startswith(f"{texts.AI_DISCLOSURE} {texts.DRILL_LABEL}")
    assert texts.DRILL_NOTE in text
    assert "Mẹ" in text


@pytest.mark.parametrize("passed", [True, False, None], ids=["passed", "failed", "aborted"])
def test_every_debrief_lists_the_red_flags_and_keeps_a_warm_tone(passed: bool | None) -> None:
    text = texts.drill_debrief("Mẹ", passed, FLAGS)
    for flag in FLAGS:
        assert f"- {flag}" in text
    folded = text.lower()
    assert not any(p in folded for p in PANIC_PHRASES)
    assert not any(p in folded for p in REFUND_PHRASES)
    assert "điểm" not in folded  # không chấm điểm hay so sánh với ai


def test_the_three_outcomes_say_different_things() -> None:
    texts_ = {texts.drill_debrief("Mẹ", p, FLAGS) for p in (True, False, None)}
    assert len(texts_) == 3


def test_a_failed_debrief_does_not_blame_the_elder() -> None:
    text = texts.drill_debrief("Mẹ", False, FLAGS).lower()
    assert not any(word in text for word in ("sai", "thất bại", "trượt", "kém"))


def test_the_shipped_scripts_produce_clean_debriefs() -> None:
    for script in dr.load_scripts().values():
        text = texts.drill_debrief("Bà", True, dr.red_flags(script))
        assert text.startswith(texts.AI_DISCLOSURE) and texts.DRILL_LABEL in text
        assert len(text) < 1000  # vừa một tin Zalo
