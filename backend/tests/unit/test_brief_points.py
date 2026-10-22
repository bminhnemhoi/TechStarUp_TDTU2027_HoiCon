"""ADR-012 / spec 024 FR-011: LLM chỉ chọn mã điểm; máy chủ bỏ điểm có điều kiện dữ kiện sai và ghép câu cố định."""

import json
import re
import typing
from pathlib import Path
from typing import Any

import pytest

from hoicon.agents import texts
from hoicon.agents.incident_graph import _UNSAFE_SUMMARY, BriefPoint, brief_points
from hoicon.domain.pii import mask_text
from hoicon.domain.risk import RiskLevel
from hoicon.eval.checks import PANIC_PHRASES, REFUND_PHRASES

ALL_POINTS: tuple[str, ...] = typing.get_args(BriefPoint)
FULL_SUITE = Path(__file__).resolve().parents[2] / "eval" / "suites" / "full.v1.json"


def _state(
    *,
    app: str = "other",
    active: bool = False,
    caller_flagged: bool = False,
    threat: str = "unknown",
    answer: tuple[str, str] | None = None,
    flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    elder_answer: dict[str, Any] | None = None
    if answer or flags:
        elder_answer = {"question_id": answer[0] if answer else "none", "answer": answer[1] if answer else "unsure"}
        if flags:
            elder_answer["note_flags"] = flags
    return {
        "event": {"app": {"category": app}, "call": {"active": active}, "caller": {"flagged": caller_flagged}},
        "threat": {"verdict": threat},
        "elder_answer": elder_answer,
    }


def _kept(point: str, state: dict[str, Any], level: RiskLevel = RiskLevel.HIGH) -> bool:
    return point in brief_points(state, level, [point, "common_scam_pattern"])


@pytest.mark.parametrize("category", ["bank", "wallet", "securities"])
def test_finance_app_point_follows_app_category(category: str) -> None:
    assert _kept("unknown_call_then_finance_app", _state(app=category))
    assert not _kept("unknown_call_then_finance_app", _state(app="other"))
    assert not _kept("unknown_call_then_finance_app", _state(app="sideloaded"))


def test_sideloaded_point_follows_app_category() -> None:
    assert _kept("sideloaded_app", _state(app="sideloaded"))
    assert not _kept("sideloaded_app", _state(app="bank"))


def test_call_still_ongoing_follows_call_active() -> None:
    assert _kept("call_still_ongoing", _state(active=True))
    assert not _kept("call_still_ongoing", _state(active=False))


def test_flagged_number_from_threat_or_caller() -> None:
    assert _kept("flagged_number", _state(threat="flagged"))
    assert _kept("flagged_number", _state(caller_flagged=True))
    assert not _kept("flagged_number", _state(threat="unknown"))


def test_authority_from_answer_or_flag() -> None:
    assert _kept("caller_claims_authority", _state(answer=("q_caller_authority", "yes")))
    assert _kept("caller_claims_authority", _state(flags={"mentions_authority": True}))
    assert not _kept("caller_claims_authority", _state(answer=("q_caller_authority", "no")))
    assert not _kept("caller_claims_authority", _state())


def test_transfer_or_code_from_answer_or_flags() -> None:
    assert _kept("asked_transfer_or_code", _state(answer=("q_asked_transfer", "yes")))
    assert _kept("asked_transfer_or_code", _state(flags={"mentions_transfer": True}))
    assert _kept("asked_transfer_or_code", _state(flags={"mentions_code": True}))
    assert not _kept("asked_transfer_or_code", _state(answer=("q_asked_transfer", "no")))
    assert not _kept("asked_transfer_or_code", _state(flags={"mentions_transfer": False}))


def test_secrecy_and_install_come_only_from_flags() -> None:
    assert _kept("asked_secrecy", _state(flags={"mentions_secrecy": True}))
    assert not _kept("asked_secrecy", _state())
    assert _kept("asked_install_app", _state(flags={"mentions_app_or_link": True}))
    assert not _kept("asked_install_app", _state())


@pytest.mark.parametrize("answer", ["no", "unsure"])
def test_elder_unsure_of_caller(answer: str) -> None:
    assert _kept("elder_unsure_of_caller", _state(answer=("q_know_caller", answer)))


def test_elder_unsure_dropped_when_elder_knows_caller_or_never_asked() -> None:
    assert not _kept("elder_unsure_of_caller", _state(answer=("q_know_caller", "yes")))
    assert not _kept("elder_unsure_of_caller", _state())


def test_common_scam_pattern_is_always_kept() -> None:
    assert brief_points(_state(), RiskLevel.CRITICAL, ["common_scam_pattern"]) == ["common_scam_pattern"]


@pytest.mark.parametrize("level", [RiskLevel.HIGH, RiskLevel.CRITICAL])
def test_may_be_routine_is_dropped_at_high_and_critical(level: RiskLevel) -> None:
    assert "may_be_routine" not in brief_points(_state(app="bank"), level, ["may_be_routine", "common_scam_pattern"])


@pytest.mark.parametrize("level", [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM])
def test_may_be_routine_is_kept_at_medium_or_below(level: RiskLevel) -> None:
    assert "may_be_routine" in brief_points(_state(), level, ["may_be_routine", "common_scam_pattern"])


def test_llm_order_is_preserved() -> None:
    state = _state(app="bank", active=True)
    got = brief_points(
        state, RiskLevel.HIGH, ["call_still_ongoing", "common_scam_pattern", "unknown_call_then_finance_app"]
    )
    assert got == ["call_still_ongoing", "common_scam_pattern", "unknown_call_then_finance_app"]


def test_empty_after_filtering_gives_default_set_with_app_point() -> None:
    got = brief_points(_state(app="bank"), RiskLevel.HIGH, ["asked_secrecy"])
    assert got == ["unknown_call_then_finance_app", "common_scam_pattern"]
    got = brief_points(_state(app="sideloaded"), RiskLevel.HIGH, ["asked_secrecy"])
    assert got == ["sideloaded_app", "common_scam_pattern"]


def test_default_set_without_app_is_just_the_common_pattern() -> None:
    assert brief_points(_state(), RiskLevel.HIGH, ["asked_secrecy"]) == ["common_scam_pattern"]
    assert brief_points(_state(app="bank"), RiskLevel.HIGH, []) == [
        "unknown_call_then_finance_app",
        "common_scam_pattern",
    ]


def test_unknown_code_never_survives() -> None:
    assert brief_points(_state(), RiskLevel.HIGH, ["skip_guardian"]) == ["common_scam_pattern"]


def test_duplicates_are_collapsed() -> None:
    assert brief_points(_state(), RiskLevel.HIGH, ["common_scam_pattern", "common_scam_pattern"]) == [
        "common_scam_pattern"
    ]


def test_every_point_has_exactly_one_sentence() -> None:
    assert set(texts.BRIEF_POINT_VI) == set(ALL_POINTS)


@pytest.mark.parametrize("point", ALL_POINTS)
def test_sentence_is_safe_for_the_guardian(point: str) -> None:
    sentence = texts.BRIEF_POINT_VI[point].replace("{alias}", "bác Hùng")
    assert not _UNSAFE_SUMMARY.search(sentence)
    assert mask_text(sentence) == sentence
    plain = sentence.lower()
    for phrase in (*PANIC_PHRASES, *REFUND_PHRASES):
        assert phrase.lower() not in plain, phrase
    assert sentence.endswith(".")


def test_sentences_do_not_contain_any_injection_marker() -> None:
    markers = json.loads(FULL_SUITE.read_text(encoding="utf-8"))["markers"].values()
    blob = " ".join(texts.BRIEF_POINT_VI.values()).lower()
    for marker in markers:
        assert marker.lower() not in blob, marker


def test_brief_summary_joins_sentences_and_fills_alias() -> None:
    out = texts.brief_summary("bác Hùng", ["unknown_call_then_finance_app", "common_scam_pattern"])
    assert out == (
        f"{texts.BRIEF_POINT_VI['unknown_call_then_finance_app'].format(alias='bác Hùng')} "
        f"{texts.BRIEF_POINT_VI['common_scam_pattern']}"
    )
    assert "{alias}" not in out
    assert re.search(r"bác Hùng", out)


@pytest.mark.parametrize(
    "state",
    [
        _state(threat="flagged"),
        _state(answer=("q_caller_authority", "yes")),
        _state(answer=("q_asked_transfer", "yes")),
        _state(flags={"mentions_secrecy": True}),
        _state(flags={"mentions_code": True}),
        _state(flags={"mentions_app_or_link": True}),
    ],
)
def test_may_be_routine_is_dropped_when_danger_facts_exist_even_at_low_level(state: dict[str, Any]) -> None:
    got = brief_points(state, RiskLevel.MEDIUM, ["may_be_routine", "common_scam_pattern"])
    assert "may_be_routine" not in got


def test_summary_sentences_start_with_a_capital_even_when_the_alias_is_lowercase() -> None:
    out = texts.brief_summary("bác Hùng", ["unknown_call_then_finance_app", "elder_unsure_of_caller"])
    assert all(s[0].isupper() for s in out.split(". ") if s)
    assert "Bác Hùng cho biết chưa rõ người gọi là ai." in out
