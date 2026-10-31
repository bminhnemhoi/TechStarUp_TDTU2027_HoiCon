"""`spike bench --model --json` (spec 003 US3): báo cáo đúng hợp đồng, không nhầm số điều phối với số của model."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import SecretStr
from sqlalchemy import delete

from hoicon.agents import spike
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

SCHEMA = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "bench_report.v1.json"


@pytest.fixture(autouse=True)
async def no_api_key(
    require_db: None, seeded_threat: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[None]:
    """Không bao giờ gọi LLM thật trong test (kể cả khi máy dev có khóa trong tệp cấu hình) + dọn run do bench tạo."""
    started = datetime.now(UTC)
    monkeypatch.setattr(get_settings(), "anthropic_api_key", None)
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(AgentRun).where(AgentRun.started_at >= started, AgentRun.is_demo))


def validate(report: dict[str, Any]) -> None:
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker())
    assert [e.message for e in validator.iter_errors(report)] == []


async def test_without_a_key_the_report_says_fallback_and_matches_the_contract(tmp_path: Path) -> None:
    out = tmp_path / "bench.json"
    report = await spike.bench(3, model="claude-haiku-4-5", json_path=out)
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == report
    validate(on_disk)
    assert on_disk["model"] == "claude-haiku-4-5" and on_disk["n"] == 3
    assert on_disk["llm_mode"] == "fallback" and on_disk["fallback_rate"] == 1.0 and on_disk["cost_usd_avg"] == 0
    assert set(on_disk["turns"]) == {"start→ask_elder", "answer→await_guardian", "decision→done"}
    assert "hostname" not in on_disk and "\n" not in on_disk["host"]


async def test_an_empty_key_counts_as_no_key(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`HOICON_ANTHROPIC_API_KEY=` (dòng rỗng trong tệp cấu hình) = không có khóa, giống LlmRouter.from_settings."""
    monkeypatch.setattr(get_settings(), "anthropic_api_key", SecretStr(""))
    report = await spike.bench(1, model="claude-haiku-5-5")
    assert report["llm_mode"] == "fallback" and "có khóa API=False" in capsys.readouterr().out


async def test_only_runs_made_by_the_bench_are_counted() -> None:
    """Có run khác (cùng thời điểm) với chi phí và không rơi về mẫu: không được lẫn vào số đo (bản cũ dùng limit(n))."""
    other = AgentRun(graph="incident", thread_id=str(new_id()), is_demo=True, cost_usd=Decimal("9.5"))
    async with get_sessionmaker().begin() as session:
        session.add(other)
        await session.flush()
        session.add(AgentStep(run_id=other.id, node="risk_scorer", model_profile="fast", fallback_used=False))
    report = await spike.bench(2, model="claude-haiku-5-5")
    assert report["fallback_rate"] == 1.0 and report["cost_usd_avg"] == 0


async def test_unknown_model_exits_2_and_says_it_has_no_price(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        await spike.bench(1, model="claude-khong-ton-tai")
    assert exc.value.code == 2
    assert "chưa có giá" in capsys.readouterr().err


async def test_model_override_does_not_leak_into_global_settings() -> None:
    before = get_settings().llm_fast_model
    await spike.bench(1, model="claude-haiku-4-5" if before != "claude-haiku-4-5" else "claude-haiku-5-5")
    assert get_settings().llm_fast_model == before


def test_cli_parses_model_and_json_options() -> None:
    args = spike.build_parser().parse_args(["bench", "--n", "5", "--model", "claude-haiku-4-5", "--json", "out.json"])
    assert (args.cmd, args.n, args.model, args.json) == ("bench", 5, "claude-haiku-4-5", Path("out.json"))
    with pytest.raises(SystemExit):
        spike.build_parser().parse_args(["bench", "--n", "0"])
