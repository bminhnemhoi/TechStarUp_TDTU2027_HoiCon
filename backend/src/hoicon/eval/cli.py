"""`hoicon-eval`: chạy bộ eval tất định (spec 030). Mã thoát: 0 đạt · 1 trượt ngưỡng · 2 lỗi dùng/cấu hình.

uv run --directory backend hoicon-eval --suite smoke --compare baseline
uv run --directory backend hoicon-eval --suite full --compare baseline-full      # ≥ 100 ca, ngưỡng Gate M3 (spec 036)
uv run --directory backend hoicon-eval --suite injection                          # chỉ các ca chèn lệnh
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from hoicon.eval import report
from hoicon.eval.cases import EVAL_DIR, ROOT, load_suite
from hoicon.eval.runner import CaseOutcome, IsolationError, run_suite

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2
DEFAULT_REPORTS = EVAL_DIR / "reports"
MIN_CASES = {"smoke": 20, "full": 100, "injection": 10}  # lượt ít ca hơn thì chỉ số "xanh" vô nghĩa
BASELINES = {"smoke": EVAL_DIR / "baseline.json", "full": EVAL_DIR / "baseline-full.json"}
MIN_BENIGN_SHARE, MIN_INJECTION = 0.30, 10  # thành phần tối thiểu của suite full (Gate M3)
COMPARE_SUITE = {"baseline": "smoke", "baseline-full": "full"}  # `--compare X` chỉ đi với đúng suite của X


def baseline_path(suite: str) -> Path:
    return BASELINES[suite]


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # không in usage dài, luôn mã 2
        print(f"hoicon-eval: {message}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="hoicon-eval", description=__doc__.splitlines()[0])
    parser.add_argument("--suite", choices=["smoke", "full", "injection"], default="smoke")
    parser.add_argument(
        "--compare",
        choices=list(COMPARE_SUITE),
        help="baseline = smoke ↔ backend/eval/baseline.json · baseline-full = full ↔ backend/eval/baseline-full.json",
    )
    parser.add_argument("--write-baseline", action="store_true", help="ghi baseline mới (chỉ chạy tay, lượt phải đạt)")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORTS, help="thư mục báo cáo")
    parser.add_argument("--baseline-file", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("HOICON_EVAL_DATABASE_URL", ""),
        help="mặc định HOICON_EVAL_DATABASE_URL (đối số dòng lệnh lộ mật khẩu trong `ps`: ưu tiên biến môi trường)",
    )
    parser.add_argument("--shared-db-ok", action="store_true", help="cho phép DB eval trùng DB ứng dụng (CI)")
    return parser


def now() -> datetime:
    return datetime.now(UTC)


def git_sha() -> str:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
            cwd=ROOT, capture_output=True, text=True, timeout=5, check=False,
        )  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


def suite_failures(outcomes: list[CaseOutcome], baseline: dict | None, suite: str = "smoke") -> list[str]:
    """Lượt thiếu ca hoặc lệch tập ca với baseline thì chỉ số 100% vô nghĩa (xóa bớt ca cho dễ xanh)."""
    failures = []
    if len(outcomes) < MIN_CASES[suite]:
        failures.append(f"suite {suite} chỉ chạy {len(outcomes)} ca, cần đủ {MIN_CASES[suite]}")
    if suite == "full":  # thành phần không chỉ do test hợp đồng giữ: lượt chạy cũng phải đủ (xóa ca hợp lệ cho dễ xanh)
        benign = sum(o.case.is_benign for o in outcomes)
        injection = sum(o.case.injection for o in outcomes)
        if outcomes and benign / len(outcomes) < MIN_BENIGN_SHARE:
            failures.append(f"chỉ {benign}/{len(outcomes)} ca hợp lệ, cần ≥ {MIN_BENIGN_SHARE:.0%}")
        if injection < MIN_INJECTION:
            failures.append(f"chỉ {injection} ca chèn lệnh, cần ≥ {MIN_INJECTION}")
    if baseline is not None:
        ran, base = {o.case.id for o in outcomes}, set(baseline.get("cases", {}))
        if ran != base:
            failures.append(
                f"tập ca khác baseline (thiếu {sorted(base - ran) or '-'}, thừa {sorted(ran - base) or '-'})"
            )
    return failures


def exit_code(outcomes: list[CaseOutcome], baseline_failures: list[str]) -> int:
    failed = any(not o.passed for o in outcomes) or bool(baseline_failures)
    return EXIT_FAIL if failed else EXIT_OK


def render_table(outcomes: list[CaseOutcome]) -> str:
    lines = [f"{'ca':<44} {'sàn':<9} {'cuối':<9} {'kết cục':<20} kết quả"]
    for o in outcomes:
        r = o.result
        verdict = "đạt" if o.passed else "TRƯỢT: " + ", ".join([*o.violations, *o.failures])
        lines.append(f"{o.case.id:<44} {r.rule_floor:<9} {r.final_level:<9} {r.outcome:<20} {verdict}")
    return "\n".join(lines)


def _summary(rep: dict) -> str:
    m = rep["metrics"]
    return (
        f"\n{m['cases_total']} ca · recall {m['escalation_recall']:.1%} · báo nhầm {m['false_escalation_rate']:.1%} · "
        f"vi phạm {m['safety_violations']} · công khai AI {m['ai_disclosure_rate']:.1%} · "
        f"p50/p95 {m['latency_p50_ms']:.0f}/{m['latency_p95_ms']:.0f} ms · "
        f"{sum(c['draft'] for c in rep['cases'])}/{m['cases_total']} ca provisional · "
        f"{'ĐẠT' if rep['passed'] else 'TRƯỢT'}"
    )


def _load_baseline(path: Path) -> dict | None:
    if not path.is_file():
        print(f"hoicon-eval: chưa có baseline ({path}); tạo bằng --write-baseline", file=sys.stderr)
        return None
    return report.load_baseline(path)


def run(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:  # argparse (tham số sai, --help)
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    if args.compare and args.write_baseline:
        print("hoicon-eval: không dùng --compare cùng --write-baseline", file=sys.stderr)
        return EXIT_USAGE
    if args.suite == "injection" and (args.compare or args.write_baseline):
        print(
            "hoicon-eval: suite injection không dùng --compare hay --write-baseline (chỉ có ngưỡng tuyệt đối)",
            file=sys.stderr,
        )
        return EXIT_USAGE
    if args.compare and COMPARE_SUITE[args.compare] != args.suite:
        print(
            f"hoicon-eval: --compare {args.compare} chỉ đi với --suite {COMPARE_SUITE[args.compare]}"
            f" (đang chạy {args.suite})",
            file=sys.stderr,
        )
        return EXIT_USAGE
    baseline_file = args.baseline_file or BASELINES.get(args.suite)
    baseline = None
    if args.compare:
        baseline = _load_baseline(baseline_file)
        if baseline is None:
            return EXIT_USAGE
    started = now()
    try:
        outcomes = asyncio.run(
            run_suite(
                load_suite(args.suite), database_url=args.database_url, shared_db_ok=args.shared_db_ok, suite=args.suite
            ),
            loop_factory=asyncio.SelectorEventLoop,  # psycopg async không chạy trên ProactorEventLoop (Windows)
        )
    except IsolationError as exc:
        print(f"hoicon-eval: {exc}", file=sys.stderr)
        return EXIT_USAGE
    except Exception as exc:
        # Chỉ in tên lớp lỗi: thông điệp lỗi của driver có thể kèm chuỗi kết nối (mật khẩu DB).
        print(
            f"hoicon-eval: không chạy được lượt eval ({type(exc).__name__}); kiểm DB eval đã chạy và migrate chưa",
            file=sys.stderr,
        )
        return EXIT_USAGE
    ref = f"{baseline_file.name} ({baseline['created']}, {baseline['git_sha']})" if baseline else ""
    rep = report.build_report(
        outcomes, started_at=started, git_sha=git_sha(), baseline=baseline, baseline_ref=ref, suite=args.suite
    )
    args.out.mkdir(parents=True, exist_ok=True)
    stem = args.out / f"{started:%Y-%m-%d}-{rep['suite']}"
    stem.with_suffix(".json").write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stem.with_suffix(".md").write_text(report.render_markdown(rep, outcomes), encoding="utf-8")
    print(render_table(outcomes))
    print(_summary(rep))
    diff = rep["baseline_diff"]
    threshold_failures = diff["failures"] if diff else report.absolute_failures(rep["metrics"], args.suite)
    threshold_failures = [*threshold_failures, *suite_failures(outcomes, baseline, args.suite)]
    for failure in threshold_failures:
        print(f"  ✗ {failure}")
    if diff:
        print(
            f"  so baseline: recall {diff['recall_pp']:+.1f} điểm %, báo nhầm {diff['false_escalation_pp']:+.1f} điểm %"
        )
    if args.suite in report.GATE_SUITES and rep["cassette_source"] != "recorded":
        print(
            f"  ℹ Gate M3 trên cassette {rep['cassette_source']}: chỉ chứng minh rào tất định, "
            "chưa chứng minh bằng model thật (BLOCKED P0-08)"
        )
    print(f"báo cáo: {stem.with_suffix('.md')}")
    code = exit_code(outcomes, threshold_failures)
    if args.write_baseline:
        if code != EXIT_OK:
            print("hoicon-eval: lượt này trượt nên không ghi baseline", file=sys.stderr)
            return code
        report.write_baseline(baseline_file, rep)
        print(f"đã ghi baseline: {baseline_file}")
    return code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
