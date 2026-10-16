"""Hợp đồng spec 025: `agent_step.v1.json`, `run_steps.v1.json`, `run_done.v1.json` (FR-001, FR-009)."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep
from hoicon.services.trace_service import run_done_view, step_view

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
NAMES = ["agent_step", "run_steps", "run_done"]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.glob("*.v1.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / f"{name}.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


def _fixture(name: str, kind: str) -> list[dict[str, Any]]:
    return _load(SCHEMAS / "fixtures" / f"{name}.v1.{kind}.json")


@pytest.mark.parametrize("name", NAMES)
def test_valid_fixtures_pass(name: str) -> None:
    validator = _validator(name)
    for doc in _fixture(name, "valid"):
        errors = [e.message for e in validator.iter_errors(_strip(doc))]
        assert errors == [], doc["_name"]


@pytest.mark.parametrize("name", NAMES)
def test_invalid_fixtures_fail(name: str) -> None:
    validator = _validator(name)
    for doc in _fixture(name, "invalid"):
        assert not validator.is_valid(_strip(doc)), doc["_why"]


def test_the_three_planned_leaks_are_each_caught() -> None:
    """T001: `input_redacted`, khóa `h1` trong output và `cost_usd` dạng số phải bị schema bắt — từng cái một."""
    validator = _validator("agent_step")
    by_why = {d["_why"]: _strip(d) for d in _fixture("agent_step", "invalid")}
    for why in ("còn trường input_redacted", "khóa h1 trong output", "cost_usd là số thực"):
        assert not validator.is_valid(by_why[why]), why


def _step(**changes: Any) -> AgentStep:
    values: dict[str, Any] = {
        "id": new_id(),
        "run_id": new_id(),
        "node": "risk_scorer",
        "model_profile": "fast",
        "model": None,
        "prompt_version": "risk_scorer@3",
        "input_redacted": {"context": "Cuộc gọi lạ từ 0912345678", "untrusted": False},
        "output": {"level": "high", "h1": "x" * 5, "nested": {"phone": "0912345678", "ok": [1, "20.000.000 đồng"]}},
        "latency_ms": 412,
        "tokens_in": 10,
        "tokens_out": 5,
        "cost_usd": Decimal("0.00125"),
        "fallback_used": True,
        "error": "timeout",
        "at": datetime(2026, 12, 1, 2, 15, 31, 123456, tzinfo=UTC),
    }
    values.update(changes)
    return AgentStep(**values)


def test_step_view_builds_a_valid_step_without_input_redacted() -> None:
    view = step_view(_step())
    assert _validator("agent_step").is_valid(view), view
    assert "input_redacted" not in view
    assert view["cost_usd"] == "0.001250"
    assert view["at"] == "2026-12-01T02:15:31.123456Z"
    assert view["output"] == {"level": "high", "nested": {"ok": [1, "20.000.000 đồng"]}}


def test_step_view_keeps_a_missing_output_as_null() -> None:
    view = step_view(_step(output=None))
    assert view["output"] is None and _validator("agent_step").is_valid(view)


def test_step_view_treats_a_naive_database_timestamp_as_utc() -> None:
    view = step_view(_step(at=datetime(2026, 12, 1, 2, 15, 31)))
    assert view["at"] == "2026-12-01T02:15:31.000000Z" and _validator("agent_step").is_valid(view)


def test_run_done_view_matches_its_schema() -> None:
    run = AgentRun(
        id=new_id(),
        graph="incident",
        status="done",
        thread_id="t",
        cost_usd=Decimal("0.00245"),
        is_drill=False,
        is_demo=True,
    )
    view = run_done_view(run, 7)
    assert _validator("run_done").is_valid(view), view
    assert view == {
        "run_id": str(run.id),
        "status": "done",
        "total_steps": 7,
        "cost_usd": "0.002450",
        "is_drill": False,
        "is_demo": True,
    }
