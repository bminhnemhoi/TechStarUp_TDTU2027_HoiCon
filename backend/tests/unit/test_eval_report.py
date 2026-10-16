"""Chỉ số, so baseline, báo cáo JSON/Markdown của eval (spec 030, FR-007/008/009)."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from hoicon.agents.texts import AI_DISCLOSURE
from hoicon.eval import report
from hoicon.eval.cases import load_case
from hoicon.eval.checks import CaseResult
from hoicon.eval.runner import CaseOutcome

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads((ROOT / "docs/schemas/eval_report.v1.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
MSG = f"{AI_DISCLOSURE} Mẹ vừa nghe một cuộc gọi lạ rồi mở ứng dụng ngân hàng."
CASSETTE = {
    "source": "synthetic",
    "behavior": "honest",
    "prompt_versions": {"risk_scorer": "risk_scorer@1", "intervention": "intervention@1"},
}


def mk(
    case_id: str,
    final: str,
    *,
    notified: bool = True,
    violations: list[str] | None = None,
    failures: list[str] | None = None,
    fallbacks: int = 0,
    llm_calls: int = 3,
    ms: int = 100,
    messages: list[str] | None = None,
    questions: list[str] | None = None,
    cassette: dict | None = None,
) -> CaseOutcome:
    case = load_case(case_id)
    result = CaseResult(
        case_id=case_id,
        run_id=f"run-{case_id[:12]}",
        incident_started=True,
        rule_floor="high",
        levels=["high", final],
        final_level=final,
        notified=notified,
        outcome="resolved_safe" if case.is_benign else "case_open",
        messages=[MSG] if messages is None else messages,
        questions=[MSG] if questions is None else questions,
        fallbacks=fallbacks,
        llm_calls=llm_calls,
        duration_ms=ms,
    )
    return CaseOutcome(case, result, violations or [], failures or [], cassette or CASSETTE)


SCAM_OK = lambda: mk("fake_police_drug_ring_001", "critical")  # noqa: E731
SCAM_LOW = lambda: mk("fake_evn_power_cut_001", "medium", failures=["below_min_level"])  # noqa: E731  (min high)
BENIGN_OK = lambda: mk("benign_family_vegetables_001", "high", ms=300)  # noqa: E731  (max high)
BENIGN_OVER = lambda: mk("benign_bank_hotline_outgoing_004", "critical", failures=["above_max_level"])  # noqa: E731


def metrics(outcomes: list[CaseOutcome]) -> dict:
    return report.compute_metrics(outcomes)


# --- Chỉ số (FR-007) --------------------------------------------------------------------------------------------------


def test_metrics_count_recall_false_alarm_and_disclosure() -> None:
    m = metrics([SCAM_OK(), SCAM_LOW(), BENIGN_OK(), BENIGN_OVER()])
    assert (m["cases_total"], m["cases_scam"], m["cases_benign"]) == (4, 2, 2)
    assert m["escalation_recall"] == 0.5  # chỉ một ca lừa đảo đạt min_risk_level và có báo người giám hộ
    assert m["false_escalation_rate"] == 0.5  # một ca hợp lệ vượt max_risk_level
    assert m["safety_violations"] == 0 and m["ai_disclosure_rate"] == 1.0 and m["cost_usd"] == 0


def test_recall_needs_the_guardian_to_be_notified() -> None:
    assert (
        metrics([mk("fake_police_drug_ring_001", "critical", notified=False, failures=["notify_mismatch"])])[
            "escalation_recall"
        ]
        == 0.0
    )


def test_benign_alarm_when_notified_against_expectation() -> None:
    quiet = mk("benign_official_tax_reminder_001", "none", notified=True, failures=["notify_mismatch"])
    assert metrics([quiet])["false_escalation_rate"] == 1.0  # notify_guardian: false mà vẫn báo


def test_violations_are_counted_and_disclosure_is_per_message() -> None:
    bad = mk("fake_police_drug_ring_001", "critical", violations=["leak_pii", "panic_wording"], messages=[MSG, "Chào"])
    m = metrics([bad])
    assert m["safety_violations"] == 2
    assert m["ai_disclosure_rate"] == pytest.approx(2 / 3)  # 3 mục (2 tin + 1 câu hỏi), 1 mục thiếu


def test_fallback_rate_and_latency_percentiles() -> None:
    m = metrics([mk("fake_police_drug_ring_001", "critical", fallbacks=3, llm_calls=3, ms=50), BENIGN_OK(), SCAM_OK()])
    assert m["fallback_rate"] == pytest.approx(3 / 9)
    assert (m["latency_p50_ms"], m["latency_p95_ms"]) == (100, 300)


def test_empty_groups_do_not_divide_by_zero() -> None:
    m = metrics([BENIGN_OK()])
    assert m["escalation_recall"] == 1.0 and m["cases_scam"] == 0


# --- So baseline (FR-009) ---------------------------------------------------------------------------------------------


def base(recall: float = 1.0, false_rate: float = 0.0) -> dict:
    return {"escalation_recall": recall, "false_escalation_rate": false_rate}


def current(recall: float = 1.0, false_rate: float = 0.0, violations: int = 0, disclosure: float = 1.0) -> dict:
    return {
        "escalation_recall": recall,
        "false_escalation_rate": false_rate,
        "safety_violations": violations,
        "ai_disclosure_rate": disclosure,
    }


def test_recall_drop_over_three_points_fails_and_exactly_three_passes() -> None:
    assert report.compare(current(recall=0.969), base(), "b")["failures"] != []
    assert report.compare(current(recall=0.97), base(), "b")["failures"] == []
    assert report.compare(current(recall=0.969), base(), "b")["recall_pp"] == pytest.approx(-3.1)


def test_false_escalation_up_over_three_points_fails() -> None:
    assert report.compare(current(false_rate=0.031), base(), "b")["failures"] != []
    assert report.compare(current(false_rate=0.03), base(), "b")["failures"] == []


def test_one_violation_or_disclosure_below_100_fails() -> None:
    assert report.compare(current(violations=1), base(), "b")["failures"] != []
    assert report.compare(current(disclosure=0.99), base(), "b")["failures"] != []


def test_better_than_baseline_passes() -> None:
    diff = report.compare(current(recall=1.0, false_rate=0.0), base(recall=0.9, false_rate=0.2), "b")
    assert diff["failures"] == [] and diff["recall_pp"] == pytest.approx(10.0)


def test_absolute_failures_apply_even_without_a_baseline() -> None:
    assert report.absolute_failures(current()) == []
    assert report.absolute_failures(current(violations=2)) and report.absolute_failures(current(disclosure=0.5))


def test_baseline_is_only_written_on_request(tmp_path: Path) -> None:
    outcomes = [SCAM_OK(), BENIGN_OK()]
    path = tmp_path / "baseline.json"
    rep = report.build_report(outcomes, started_at=NOW, git_sha="abc1234", baseline=None, baseline_ref="")
    report.compare(rep["metrics"], base(), "x")
    assert not path.exists()  # tính toán/so sánh không bao giờ ghi baseline
    report.write_baseline(path, rep)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert (
        saved["git_sha"] == "abc1234" and saved["cassette_source"] == "synthetic" and saved["created"] == "2026-10-15"
    )
    assert saved["metrics"]["escalation_recall"] == 1.0 and set(saved["cases"].values()) == {"pass"}


# --- Báo cáo JSON + Markdown (FR-008) ---------------------------------------------------------------------------------


def validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def test_report_matches_the_contract_with_and_without_baseline() -> None:
    outcomes = [SCAM_OK(), SCAM_LOW(), BENIGN_OK(), BENIGN_OVER()]
    plain = report.build_report(outcomes, started_at=NOW, git_sha="abc1234", baseline=None, baseline_ref="")
    assert [e.message for e in validator().iter_errors(plain)] == [] and plain["baseline_diff"] is None
    compared = report.build_report(
        outcomes,
        started_at=NOW,
        git_sha="abc1234",
        baseline={"metrics": base()},
        baseline_ref="backend/eval/baseline.json",
    )
    assert [e.message for e in validator().iter_errors(compared)] == []
    assert compared["baseline_diff"]["recall_pp"] == pytest.approx(-50.0) and compared["passed"] is False


def test_report_groups_by_category_and_region_and_flags_drafts() -> None:
    rep = report.build_report(
        [SCAM_OK(), BENIGN_OK(), BENIGN_OVER()], started_at=NOW, git_sha="g", baseline=None, baseline_ref=""
    )
    assert rep["by_category"]["fake_police"] == {"cases": 1, "passed": 1, "violations": 0}
    assert rep["by_category"]["benign_bank"]["passed"] == 0
    assert sum(g["cases"] for g in rep["by_region"].values()) == 3
    assert rep["has_draft_scenarios"] is True and rep["cassette_source"] == "synthetic"
    assert "messages" not in rep["cases"][0]  # JSON không chứa nội dung tin


def test_report_passes_only_when_every_case_and_threshold_pass() -> None:
    good = report.build_report([SCAM_OK(), BENIGN_OK()], started_at=NOW, git_sha="g", baseline=None, baseline_ref="")
    assert good["passed"] is True
    worse = report.build_report([SCAM_OK(), SCAM_LOW()], started_at=NOW, git_sha="g", baseline=None, baseline_ref="")
    assert worse["passed"] is False


def test_markdown_has_every_section_the_spec_asks_for() -> None:
    leaky = mk(
        "benign_bank_hotline_outgoing_004",
        "critical",
        failures=["above_max_level"],
        messages=[f"{MSG} Gọi 0900000001 nhé."],
    )
    outcomes = [SCAM_OK(), leaky, BENIGN_OK()]
    rep = report.build_report(
        outcomes,
        started_at=NOW,
        git_sha="abc1234",
        baseline={"metrics": base()},
        baseline_ref="backend/eval/baseline.json",
    )
    md = report.render_markdown(rep, outcomes)
    for heading in (
        "# Eval smoke",
        "## Chỉ số",
        "## Theo nhóm thủ đoạn",
        "## Theo vùng miền",
        "## 5 ca tệ nhất",
        "## So với baseline",
    ):
        assert heading in md, heading
    assert "kịch bản nháp" in md.lower()  # có ca draft:true
    assert "run-benign_bank_" in md and "/trace/" in md  # run_id + đường dẫn trace
    assert "0900000001" not in md and "[SĐT ***001]" in md  # tin in ra đã che
    assert "risk_scorer@1" in md and "R2" in md and "OTT" in md  # phiên bản prompt + giới hạn đã biết


def test_markdown_lists_at_most_five_worst_cases_worst_first() -> None:
    outcomes = [
        mk(c, "high", failures=["notify_mismatch"], ms=i)
        for i, c in enumerate(
            [
                "benign_family_vegetables_001",
                "benign_bank_hotline_outgoing_004",
                "benign_relative_friend_phone_002",
                "benign_official_hospital_003",
                "benign_family_son_rent_002",
                "fake_police_drug_ring_001",
                "fake_evn_power_cut_001",
            ]
        )
    ]
    outcomes[6] = mk("fake_evn_power_cut_001", "high", violations=["leak_pii"], failures=["notify_mismatch"])
    md = report.render_markdown(
        report.build_report(outcomes, started_at=NOW, git_sha="g", baseline=None, baseline_ref=""), outcomes
    )
    section = md.split("## 5 ca tệ nhất")[1].split("\n## ")[0]
    assert section.count("/trace/") == 5
    assert section.index("fake_evn_power_cut_001") < section.index("fake_police_drug_ring_001")  # có vi phạm ⇒ lên đầu
    assert "benign_family_vegetables_001" not in section  # ca nhẹ nhất (không vi phạm, chậm nhất) bị loại khỏi top 5


def test_markdown_warns_when_a_cassette_was_recorded_for_another_prompt_version() -> None:
    stale = mk(
        "fake_police_drug_ring_001",
        "critical",
        cassette={**CASSETTE, "prompt_versions": {"risk_scorer": "risk_scorer@0", "intervention": "intervention@1"}},
    )
    rep = report.build_report(
        [stale],
        started_at=NOW,
        git_sha="g",
        baseline=None,
        baseline_ref="",
        prompt_versions={"risk_scorer": "risk_scorer@1", "intervention": "intervention@1"},
    )
    md = report.render_markdown(rep, [stale])
    assert "cassette" in md.lower() and "risk_scorer@0" in md
