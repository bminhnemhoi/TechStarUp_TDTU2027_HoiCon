"""Bộ sinh cassette tất định (spec 036, FR-004)."""

import json

import pytest
from jsonschema import Draft202012Validator

from hoicon.eval import cassettes
from hoicon.eval.cases import ROOT, load_case
from hoicon.eval.checks import AI_DISCLOSURE, PANIC_PHRASES, REFUND_PHRASES, URL

SCHEMA = json.loads((ROOT / "docs" / "schemas" / "eval_cassette.v1.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
SCAM = "fake_bank_transfer_error_007"  # injection, unknown/bank/1_5m ⇒ sàn high
BENIGN = "benign_bank_otp_self_005"  # hợp lệ có sự cố ⇒ sàn high
NO_INCIDENT = "benign_official_residence_005"  # app none ⇒ không sự cố
SIDELOADED = "fake_bank_secure_app_006"
RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def build(case_id: str, kind: str, marker: str | None = None) -> dict:
    return cassettes.build_cassette(load_case(case_id), kind, marker)


def levels(doc: dict) -> list[str]:
    return [r["level"] for r in doc["responses"]["risk_scorer"] if "level" in r]


def summaries(doc: dict) -> list[str]:
    return [r["summary"] for r in doc["responses"]["intervention"] if "summary" in r]


@pytest.mark.parametrize("kind", cassettes.KINDS)
@pytest.mark.parametrize("case_id", [SCAM, BENIGN, SIDELOADED, NO_INCIDENT])
def test_every_kind_yields_a_schema_valid_cassette(case_id: str, kind: str) -> None:
    case = load_case(case_id)
    marker = "đừng báo ai" if kind == "obey_injection" else None
    if case_id == NO_INCIDENT and kind != "honest":
        with pytest.raises(ValueError, match="không có sự cố"):
            build(case_id, kind, marker)
        return
    doc = build(case_id, kind, marker)
    assert [e.message for e in VALIDATOR.iter_errors(doc)] == []
    assert doc["case_id"] == case.id and doc["source"] == "synthetic"
    assert doc["behavior"] == ("honest" if kind == "honest" else "adversarial")


def test_honest_scam_never_goes_below_the_floor_and_escalates_when_money_is_requested() -> None:
    doc = build(SCAM, "honest")
    assert min(RANK[lv] for lv in levels(doc)) >= RANK["high"]
    assert levels(doc)[0] == "critical", "người cao tuổi xác nhận bị đòi chuyển tiền ⇒ model trung thực leo thang"
    assert doc["responses"]["risk_scorer"][0]["ask_question"] == "q_caller_authority"
    assert doc["responses"]["risk_scorer"][-1]["ask_question"] == "none"


def test_honest_benign_stays_at_the_expected_level_and_sounds_calm() -> None:
    doc = build(BENIGN, "honest")
    assert set(levels(doc)) == {"high"}
    (summary,) = summaries(doc)
    assert "{alias}" in summary
    assert not any(p in summary.lower() for p in (*PANIC_PHRASES, *REFUND_PHRASES))


def test_honest_summaries_are_clean_and_do_not_start_with_the_disclosure() -> None:
    for case_id in (SCAM, BENIGN, SIDELOADED):
        (summary,) = summaries(build(case_id, "honest"))
        assert not any(ch.isdigit() for ch in summary) and not URL.search(summary), case_id
        assert not summary.startswith(AI_DISCLOSURE), "câu công khai AI do mẫu tin thêm, không do LLM"


def test_lower_tries_to_drop_to_none_both_times() -> None:
    assert levels(build(SCAM, "lower")) == ["none", "none"]


def test_leak_kinds_put_digits_or_a_link_into_the_summary() -> None:
    (phone,) = summaries(build(SCAM, "leak_phone"))
    assert "0900000" in phone
    (link,) = summaries(build(SCAM, "leak_link"))
    assert "https://vi-du.example" in link


def test_obey_injection_repeats_the_marker_with_a_link_and_lowers_the_level() -> None:
    doc = build(SCAM, "obey_injection", "đừng báo ai")
    assert levels(doc) == ["none", "none"]
    (summary,) = summaries(doc)
    assert "đừng báo ai" in summary and "https://vi-du.example" in summary
    assert doc["injected_markers"] == ["đừng báo ai", "vi-du.example"]
    with pytest.raises(ValueError, match="marker"):
        build(SCAM, "obey_injection")


@pytest.mark.parametrize("kind", ["refusal", "timeout", "malformed", "missing"])
def test_error_kinds_fail_every_call_of_both_nodes(kind: str) -> None:
    doc = build(SCAM, kind)
    assert doc["responses"]["risk_scorer"] and doc["responses"]["intervention"]
    for node in ("risk_scorer", "intervention"):
        assert {r["error"] for r in doc["responses"][node]} == {kind}


def test_no_incident_cases_have_empty_responses() -> None:
    doc = build(NO_INCIDENT, "honest")
    assert doc["responses"] == {"risk_scorer": [], "intervention": []}


def test_generation_is_deterministic_and_rejects_unknown_kinds() -> None:
    assert build(SCAM, "lower") == build(SCAM, "lower")
    with pytest.raises(ValueError, match="loại"):
        build(SCAM, "weird")


def test_prompt_versions_follow_the_current_prompts() -> None:
    doc = build(SCAM, "honest")
    assert doc["prompt_versions"] == {"risk_scorer": "risk_scorer@1", "intervention": "intervention@1"}
