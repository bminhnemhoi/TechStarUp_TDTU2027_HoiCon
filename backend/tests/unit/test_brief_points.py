"""ADR-012 / spec 024 FR-011: LLM chỉ chọn mã điểm; máy chủ bỏ điểm có điều kiện dữ kiện sai và ghép câu cố định."""

import itertools
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


def test_common_scam_pattern_needs_at_least_one_kept_point_before_it() -> None:
    assert brief_points(_state(), RiskLevel.CRITICAL, ["common_scam_pattern"]) == []
    assert brief_points(
        _state(app="bank"), RiskLevel.HIGH, ["unknown_call_then_finance_app", "common_scam_pattern"]
    ) == [
        "unknown_call_then_finance_app",
        "common_scam_pattern",
    ]


@pytest.mark.parametrize("level", [RiskLevel.HIGH, RiskLevel.CRITICAL])
def test_may_be_routine_is_dropped_at_high_and_critical(level: RiskLevel) -> None:
    assert "may_be_routine" not in brief_points(_state(app="bank"), level, ["may_be_routine", "common_scam_pattern"])


@pytest.mark.parametrize("level", [RiskLevel.NONE, RiskLevel.LOW, RiskLevel.MEDIUM])
def test_may_be_routine_is_kept_at_medium_or_below(level: RiskLevel) -> None:
    assert "may_be_routine" in brief_points(
        _state(app="bank"), level, ["unknown_call_then_finance_app", "may_be_routine"]
    )


def test_order_follows_the_table_not_the_llm() -> None:
    state = _state(app="bank", active=True)
    got = brief_points(
        state, RiskLevel.HIGH, ["call_still_ongoing", "common_scam_pattern", "unknown_call_then_finance_app"]
    )
    assert got == ["unknown_call_then_finance_app", "call_still_ongoing", "common_scam_pattern"]


def test_empty_after_filtering_gives_default_set_with_app_point() -> None:
    got = brief_points(_state(app="bank"), RiskLevel.HIGH, ["asked_secrecy"])
    assert got == ["unknown_call_then_finance_app", "common_scam_pattern"]
    got = brief_points(_state(app="sideloaded"), RiskLevel.HIGH, ["asked_secrecy"])
    assert got == ["sideloaded_app", "common_scam_pattern"]


def test_default_set_without_app_is_just_the_common_pattern() -> None:
    assert brief_points(_state(), RiskLevel.HIGH, ["asked_secrecy"]) == []
    assert brief_points(_state(app="bank"), RiskLevel.HIGH, []) == [
        "unknown_call_then_finance_app",
        "common_scam_pattern",
    ]


def test_unknown_code_never_survives() -> None:
    assert brief_points(_state(), RiskLevel.HIGH, ["skip_guardian"]) == []


def test_duplicates_are_collapsed() -> None:
    state = _state(app="bank")
    got = brief_points(state, RiskLevel.HIGH, ["unknown_call_then_finance_app"] * 2)
    assert got == ["unknown_call_then_finance_app"]


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


# --- FR-013: thứ tự ghép cố định, nhóm nhận định, tóm tắt rỗng, câu "máy bận" ------------------------------------

# Chép bảng spec 024 §5 (23/10/2026), đúng chữ. Đổi câu ⇒ sửa spec và hằng số này cùng lúc.
SPEC_TABLE: dict[str, str] = {
    "unknown_call_then_finance_app": "Vừa rồi {alias} nghe một số lạ gọi rồi mở ứng dụng ngân hàng hoặc ví điện tử.",
    "sideloaded_app": "Vừa rồi {alias} mở một ứng dụng không tải từ cửa hàng CH Play, sau cuộc gọi lạ.",
    "call_still_ongoing": "Cuộc gọi lạ với {alias} có thể vẫn đang diễn ra.",
    "flagged_number": "Số điện thoại này nằm trong danh sách số bị báo nghi lừa đảo.",
    "caller_claims_authority": "{alias} cho biết người gọi xưng là công an, ngân hàng hoặc cơ quan nhà nước.",
    "asked_transfer_or_code": "{alias} cho biết người gọi bảo chuyển tiền hoặc đọc mã xác thực.",
    "asked_secrecy": "{alias} cho biết người gọi dặn giữ kín, đừng kể với ai.",
    "asked_install_app": "{alias} cho biết người gọi bảo cài ứng dụng hoặc mở một đường dẫn lạ.",
    "elder_unsure_of_caller": "{alias} cho biết chưa rõ người gọi là ai.",
    "common_scam_pattern": "Những điểm trên thường gặp trong các cuộc gọi giả danh để lừa chuyển tiền.",
    "may_be_routine": "Cũng có thể đây chỉ là việc bình thường, anh/chị cứ nhẹ nhàng hỏi thăm {alias} xem chuyện gì.",
}
CONTRACT = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "guardian_brief.v2.json"
JUDGMENT = ("common_scam_pattern", "may_be_routine")
# Mọi điều kiện dữ kiện đúng cùng lúc (trừ #2 và may_be_routine, loại trừ với #1 / mức cao).
ALL_FACTS = _state(
    app="bank",
    active=True,
    threat="flagged",
    answer=("q_know_caller", "no"),
    flags={
        "mentions_authority": True,
        "mentions_transfer": True,
        "mentions_secrecy": True,
        "mentions_app_or_link": True,
    },
)
EVENT_ONLY = _state(app="bank", active=True)  # đủ điều kiện may_be_routine ở mức trung bình


def test_sentences_equal_the_spec_table_word_for_word() -> None:
    assert texts.BRIEF_POINT_VI == SPEC_TABLE


def test_table_order_equals_the_contract_enum_and_the_number_column() -> None:
    enum = json.loads(CONTRACT.read_text(encoding="utf-8"))["properties"]["points"]["items"]["enum"]
    assert list(texts.BRIEF_POINT_VI) == enum == list(SPEC_TABLE) == list(ALL_POINTS)


def _subsets(upto: int = 3) -> list[tuple[str, ...]]:
    return [c for n in range(1, upto + 1) for c in itertools.combinations(ALL_POINTS, n)]


@pytest.mark.parametrize(
    ("state", "level"),
    [(ALL_FACTS, RiskLevel.HIGH), (EVENT_ONLY, RiskLevel.MEDIUM), (_state(app="sideloaded"), RiskLevel.LOW)],
)
def test_any_permutation_of_the_same_codes_gives_the_same_summary(state: dict[str, Any], level: RiskLevel) -> None:
    for subset in _subsets():
        summaries = {
            texts.brief_summary("bác Hùng", brief_points(state, level, list(order)))
            for order in itertools.permutations(subset)
        }
        assert len(summaries) == 1, subset


@pytest.mark.parametrize("state", [ALL_FACTS, EVENT_ONLY, _state(app="sideloaded"), _state()])
def test_the_summary_never_starts_with_a_judgment_sentence(state: dict[str, Any]) -> None:
    for subset in _subsets():
        got = brief_points(state, RiskLevel.MEDIUM, list(subset))
        assert not got or got[0] not in JUDGMENT, subset
        assert len(got) <= 3 and got == sorted(got, key=ALL_POINTS.index)


def test_both_judgment_codes_keep_only_the_cautious_one() -> None:
    got = brief_points(
        EVENT_ONLY, RiskLevel.MEDIUM, ["may_be_routine", "unknown_call_then_finance_app", "common_scam_pattern"]
    )
    assert got == ["unknown_call_then_finance_app", "common_scam_pattern"]
    assert "may_be_routine" not in got


@pytest.mark.parametrize(
    "codes", [["common_scam_pattern"], ["may_be_routine"], ["may_be_routine", "common_scam_pattern"]]
)
def test_only_judgment_codes_fall_back_to_the_default_set(codes: list[str]) -> None:
    assert brief_points(EVENT_ONLY, RiskLevel.MEDIUM, codes) == [
        "unknown_call_then_finance_app",
        "common_scam_pattern",
    ]


@pytest.mark.parametrize("codes", [[], ["asked_secrecy"], ["common_scam_pattern"], ["not_a_code"]])
def test_an_incident_without_an_app_and_a_bad_llm_answer_has_no_summary_and_a_clean_message(codes: list[str]) -> None:
    kept = brief_points(_state(), RiskLevel.HIGH, codes)
    summary = texts.brief_summary("Mẹ", kept)
    assert kept == [] and summary == ""
    message = texts.guardian_detail("Mẹ", RiskLevel.HIGH, summary, "call_now", False)
    assert "  " not in message and ". ." not in message
    assert "Mức nguy cơ: cao. Anh/chị gọi ngay cho Mẹ" in message


@pytest.mark.parametrize("action", ["call_now", "call_and_stay_on_line"])
def test_a_call_still_ongoing_adds_the_busy_sentence_to_the_call_actions(action: str) -> None:
    busy = texts.ACTION_BUSY_VI.format(alias="Mẹ")
    assert busy in texts.guardian_detail("Mẹ", RiskLevel.HIGH, "Tóm tắt.", action, False, call_ongoing=True)
    assert busy not in texts.guardian_detail("Mẹ", RiskLevel.HIGH, "Tóm tắt.", action, False)


def test_the_busy_sentence_is_not_added_to_the_visit_action() -> None:
    message = texts.guardian_detail(
        "Mẹ", RiskLevel.HIGH, "Tóm tắt.", "visit_or_call_relative", False, call_ongoing=True
    )
    assert texts.ACTION_BUSY_VI.format(alias="Mẹ") not in message
