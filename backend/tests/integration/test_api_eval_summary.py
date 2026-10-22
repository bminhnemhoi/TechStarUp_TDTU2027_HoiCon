"""Spec 033 FR-012 (T010): `GET /v1/eval/summary` — sau cổng, chỉ baseline đã commit, không đọc `reports/`."""

import json
from pathlib import Path

import pytest
from consent_support import call
from test_api_sim import ORIGIN, sim_world  # noqa: F401  (fixture)

from hoicon.config import get_settings
from hoicon.eval import cases

pytestmark = pytest.mark.integration


async def test_gate_off_is_a_404_even_without_a_session(sim_world, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    monkeypatch.setenv("HOICON_SIM_ENABLED", "false")
    get_settings.cache_clear()
    assert (await call("GET", "/v1/eval/summary")).status_code == 404
    assert (await call("GET", "/v1/eval/summary", token=sim_world.demo.token)).status_code == 404


async def test_a_real_family_gets_404_and_no_session_gets_401(sim_world) -> None:  # noqa: F811
    assert (await call("GET", "/v1/eval/summary", token=sim_world.real.token)).status_code == 404
    assert (await call("GET", "/v1/eval/summary")).status_code == 401


async def test_summary_lists_the_committed_baselines_with_an_honest_gate(sim_world) -> None:  # noqa: F811
    res = await call("GET", "/v1/eval/summary", token=sim_world.demo.token, headers=ORIGIN)
    assert res.status_code == 200, res.text
    body = res.json()
    assert [s["suite"] for s in body["suites"]] == ["smoke", "full"] or {s["suite"] for s in body["suites"]} >= {
        "smoke",
        "full",
    }
    for suite in body["suites"]:
        assert suite["baseline"]["metrics"]["escalation_recall"] >= 0.9
        assert (
            suite["gate"]["verdict"] == "provisional" and suite["gate"]["reasons"]
        )  # synthetic + draft ⇒ chưa phải số M3
    assert "run_id" not in res.text and "reports" not in res.text


async def test_reports_directory_is_never_read(sim_world, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: F811
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports" / "2026-10-22-full.json").write_text(json.dumps({"run_id": "RUN-CANARY"}), encoding="utf-8")
    (tmp_path / "cassettes").mkdir()
    (tmp_path / "baseline.json").write_text(
        json.dumps(
            {
                "suite": "smoke",
                "created": "2026-10-22",
                "git_sha": "abc1234",
                "cassette_source": "recorded",
                "metrics": {"escalation_recall": 0.95, "note": "bỏ qua chuỗi"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cases, "EVAL_DIR", tmp_path)
    res = await call("GET", "/v1/eval/summary", token=sim_world.demo.token)
    assert res.status_code == 200 and "RUN-CANARY" not in res.text
    (suite,) = res.json()["suites"]
    assert suite["gate"] == {"verdict": "recorded", "reasons": []}
    assert suite["baseline"]["metrics"] == {"escalation_recall": 0.95}  # chỉ số, bỏ trường chữ
