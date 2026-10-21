"""CLI `hoicon-eval`: mã thoát 0 đạt / 1 trượt / 2 lỗi dùng-cấu hình (spec 030, FR-001, FR-010)."""

import pytest

from hoicon.config import get_settings
from hoicon.eval.cases import load_case
from hoicon.eval.checks import CaseResult
from hoicon.eval.cli import exit_code, run
from hoicon.eval.runner import CaseOutcome

URL = "postgresql+psycopg://x:y@127.0.0.1:15432/hoicon_eval"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOICON_EVAL_DATABASE_URL", raising=False)
    monkeypatch.setenv("HOICON_ENV", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_missing_database_url_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(["--suite", "smoke"]) == 2
    assert "HOICON_EVAL_DATABASE_URL" in capsys.readouterr().err


def test_prod_environment_exits_2(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    assert run(["--suite", "smoke", "--database-url", URL]) == 2
    assert "prod" in capsys.readouterr().err


def test_same_database_as_the_application_exits_2_without_the_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HOICON_DATABASE_URL", URL)
    get_settings.cache_clear()
    assert run(["--suite", "smoke", "--database-url", URL]) == 2
    assert "--shared-db-ok" in capsys.readouterr().err


def test_unknown_argument_exits_2() -> None:
    assert run(["--suite", "smoke", "--nonsense"]) == 2


def outcome(violations: list[str], failures: list[str]) -> CaseOutcome:
    case = load_case("fake_police_drug_ring_001")
    return CaseOutcome(case, CaseResult(case_id=case.id), violations, failures)


def test_exit_code_is_1_for_any_violation_or_failure_or_failed_comparison() -> None:
    assert exit_code([outcome([], [])], baseline_failures=[]) == 0
    assert exit_code([outcome(["leak_pii"], [])], baseline_failures=[]) == 1
    assert exit_code([outcome([], ["below_min_level"])], baseline_failures=[]) == 1
    assert exit_code([outcome([], [])], baseline_failures=["recall tụt 5,0 điểm"]) == 1


# --- Báo cáo + baseline qua CLI (FR-008, FR-009) ------------------------------------------------------------------

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from test_eval_report import BENIGN_OK, SCAM_LOW, SCAM_OK  # noqa: E402

from hoicon.eval import cli, report  # noqa: E402


def full(*first: CaseOutcome) -> list[CaseOutcome]:
    """Đủ 20 ca (suite smoke) — CLI từ chối lượt thiếu ca."""
    return [*first, *[SCAM_OK() for _ in range(20 - len(first))]]


def fake_run(monkeypatch: pytest.MonkeyPatch, outcomes: list[CaseOutcome]) -> None:
    async def fake(cases: list, **_: object) -> list[CaseOutcome]:
        return outcomes

    monkeypatch.setattr(cli, "run_suite", fake)


def args(tmp_path: Path, *extra: str) -> list[str]:
    return [
        "--suite",
        "smoke",
        "--database-url",
        URL,
        "--out",
        str(tmp_path),
        "--baseline-file",
        str(tmp_path / "b.json"),
        *extra,
    ]


def test_smoke_writes_json_and_markdown_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run(monkeypatch, full(SCAM_OK(), BENIGN_OK()))
    assert run(args(tmp_path)) == 0
    (json_file,) = tmp_path.glob("*-smoke.json")
    assert json.loads(json_file.read_text(encoding="utf-8"))["passed"] is True
    assert json_file.with_suffix(".md").read_text(encoding="utf-8").startswith("# Eval smoke")
    assert not (tmp_path / "b.json").exists()  # không bao giờ tự ghi baseline


def test_compare_fails_with_exit_1_when_recall_drops_against_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    good = report.build_report(
        full(SCAM_OK(), BENIGN_OK()), started_at=cli.now(), git_sha="g", baseline=None, baseline_ref=""
    )
    report.write_baseline(tmp_path / "b.json", good)
    before = (tmp_path / "b.json").read_bytes()
    fake_run(monkeypatch, full(SCAM_OK(), SCAM_LOW(), BENIGN_OK()))  # recall 1.0 → 0.5
    assert run(args(tmp_path, "--compare", "baseline")) == 1
    assert "recall" in capsys.readouterr().out
    assert (tmp_path / "b.json").read_bytes() == before  # baseline không bị ghi đè


def test_compare_passes_when_equal_to_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outcomes = full(SCAM_OK(), BENIGN_OK())
    report.write_baseline(
        tmp_path / "b.json",
        report.build_report(outcomes, started_at=cli.now(), git_sha="g", baseline=None, baseline_ref=""),
    )
    fake_run(monkeypatch, outcomes)
    assert run(args(tmp_path, "--compare", "baseline")) == 0


def test_compare_without_a_baseline_file_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run(monkeypatch, [SCAM_OK()])
    assert run(args(tmp_path, "--compare", "baseline")) == 2


def test_write_baseline_writes_only_the_given_file_and_only_for_a_passing_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run(monkeypatch, full(SCAM_OK(), SCAM_LOW()))  # có ca lệch kỳ vọng ⇒ không đáng làm baseline
    assert run(args(tmp_path, "--write-baseline")) == 1 and not (tmp_path / "b.json").exists()
    fake_run(monkeypatch, full(SCAM_OK(), BENIGN_OK()))
    assert run(args(tmp_path, "--write-baseline")) == 0
    assert json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))["metrics"]["escalation_recall"] == 1.0


def test_a_suite_that_lost_cases_fails_even_if_the_metrics_look_perfect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_run(monkeypatch, [SCAM_OK(), BENIGN_OK()])  # chỉ 2 ca, recall/disclosure vẫn 100%
    assert run(args(tmp_path)) == 1
    assert "20" in capsys.readouterr().out


def test_compare_fails_when_the_case_set_differs_from_the_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    full = [SCAM_OK(), BENIGN_OK(), *[SCAM_OK() for _ in range(18)]]  # đủ 20 ca nhưng id khác baseline
    base = report.build_report(full, started_at=cli.now(), git_sha="g", baseline=None, baseline_ref="")
    base["cases"] = [{**c, "case_id": f"other_{i:03d}"} for i, c in enumerate(base["cases"])]
    report.write_baseline(tmp_path / "b.json", base)
    fake_run(monkeypatch, full)
    assert run(args(tmp_path, "--compare", "baseline")) == 1
    assert "baseline" in capsys.readouterr().out


def test_an_infrastructure_error_exits_2_without_leaking_the_connection_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def broken(cases: list, **_: object) -> list[CaseOutcome]:
        raise ConnectionError("connection to postgresql://hoicon:hoicon_dev@127.0.0.1:15432/hoicon_eval failed")

    monkeypatch.setattr(cli, "run_suite", broken)
    assert run(args(tmp_path)) == 2  # lỗi hạ tầng ≠ "trượt ngưỡng" (exit 1)
    captured = capsys.readouterr()
    assert "ConnectionError" in captured.err and "hoicon_dev" not in captured.err + captured.out


# --- Suite full / injection (spec 036, FR-001/FR-005/FR-006/FR-007) -----------------------------------------------

from test_eval_report import BENIGN_OVER, mk  # noqa: E402


def many(first: list[CaseOutcome], total: int) -> list[CaseOutcome]:
    """Đủ `total` ca bằng cách thêm ca lừa đảo đạt."""
    return [*first, *[SCAM_OK() for _ in range(total - len(first))]]


def low_without_failure() -> CaseOutcome:
    """Ca lừa đảo mức cuối thấp hơn kỳ vọng nhưng không ghi lỗi: chỉ kéo recall xuống (kiểm ngưỡng tuyệt đối)."""
    return mk("fake_evn_power_cut_001", "medium")


def args_for(tmp_path: Path, suite: str, *extra: str) -> list[str]:
    return [
        "--suite",
        suite,
        "--database-url",
        URL,
        "--out",
        str(tmp_path),
        "--baseline-file",
        str(tmp_path / "b.json"),
        *extra,
    ]


def test_full_suite_runs_and_writes_a_full_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run(monkeypatch, many([BENIGN_OK()], 100))
    assert run(args_for(tmp_path, "full")) == 0
    (json_file,) = tmp_path.glob("*-full.json")
    assert json.loads(json_file.read_text(encoding="utf-8"))["suite"] == "full"
    assert json_file.with_suffix(".md").read_text(encoding="utf-8").startswith("# Eval full")


def test_full_suite_with_fewer_than_100_cases_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_run(monkeypatch, many([BENIGN_OK()], 99))
    assert run(args_for(tmp_path, "full")) == 1
    assert "100" in capsys.readouterr().out


def test_gate_m3_recall_boundary_without_a_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run(monkeypatch, many([low_without_failure() for _ in range(10)], 100))  # recall 0,90 ⇒ đạt
    assert run(args_for(tmp_path, "full")) == 0
    fake_run(monkeypatch, many([low_without_failure() for _ in range(11)], 100))  # recall 0,89 ⇒ trượt
    assert run(args_for(tmp_path, "full")) == 1


def test_gate_m3_false_escalation_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    over = lambda: mk("benign_bank_hotline_outgoing_004", "critical")  # noqa: E731  (vượt max nhưng không ghi lỗi)
    fake_run(monkeypatch, [*[over() for _ in range(10)], *[BENIGN_OK() for _ in range(90)], SCAM_OK()])
    assert run(args_for(tmp_path, "full")) == 0  # 10/100 = 0,10
    fake_run(monkeypatch, [*[over() for _ in range(11)], *[BENIGN_OK() for _ in range(89)], SCAM_OK()])
    assert run(args_for(tmp_path, "full")) == 1


def test_smoke_is_not_held_to_the_gate_m3_numbers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_run(monkeypatch, many([low_without_failure() for _ in range(5)], 20))  # recall 0,75
    assert run(args_for(tmp_path, "smoke")) == 0


@pytest.mark.parametrize(
    ("suite", "compare"), [("full", "baseline"), ("smoke", "baseline-full"), ("injection", "baseline-full")]
)
def test_compare_must_match_the_suite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], suite: str, compare: str
) -> None:
    fake_run(monkeypatch, many([], 100))
    assert run(args_for(tmp_path, suite, "--compare", compare)) == 2
    assert "--compare" in capsys.readouterr().err


def test_compare_baseline_full_detects_a_drop_and_a_changed_case_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    good = many([BENIGN_OK()], 100)
    report.write_baseline(
        tmp_path / "b.json",
        report.build_report(good, started_at=cli.now(), git_sha="g", baseline=None, baseline_ref="", suite="full"),
    )
    fake_run(monkeypatch, good)
    assert run(args_for(tmp_path, "full", "--compare", "baseline-full")) == 0
    fake_run(monkeypatch, many([BENIGN_OK(), SCAM_LOW(), SCAM_LOW(), SCAM_LOW(), SCAM_LOW()], 100))
    assert run(args_for(tmp_path, "full", "--compare", "baseline-full")) == 1  # recall 100% → 96%
    fake_run(monkeypatch, many([BENIGN_OK(), mk("fake_tax_debt_link_001", "high")], 100))  # tập ca khác baseline
    assert run(args_for(tmp_path, "full", "--compare", "baseline-full")) == 1
    assert "baseline" in capsys.readouterr().out


def test_write_baseline_for_full_goes_to_the_given_file_and_records_provisional(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_run(monkeypatch, many([BENIGN_OK()], 100))
    assert run(args_for(tmp_path, "full", "--write-baseline")) == 0
    saved = json.loads((tmp_path / "b.json").read_text(encoding="utf-8"))
    assert saved["suite"] == "full" and saved["provisional_cases"] == 100
    assert "provisional" in capsys.readouterr().out


def test_default_baseline_files_follow_the_suite() -> None:
    assert cli.baseline_path("smoke").name == "baseline.json"
    assert cli.baseline_path("full").name == "baseline-full.json"


def test_injection_suite_runs_with_its_own_minimum_and_no_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run(monkeypatch, many([], 10))
    assert run(args_for(tmp_path, "injection")) == 0
    fake_run(monkeypatch, many([], 9))
    assert run(args_for(tmp_path, "injection")) == 1


def test_a_full_run_that_ignores_benign_over_alarms_still_counts_the_failure_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run(monkeypatch, many([BENIGN_OVER()], 100))  # ca có lỗi ghi nhận ⇒ exit 1 dù ngưỡng chung còn đạt
    assert run(args_for(tmp_path, "full")) == 1
