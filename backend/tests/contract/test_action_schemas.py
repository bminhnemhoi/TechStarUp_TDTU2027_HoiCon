"""Hợp đồng spec 023: `incident_decision.v1.json`, `action_view.v1.json`."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.fixture(scope="module")
def decision_validator() -> Draft202012Validator:
    return _validator("incident_decision.v1.json")


@pytest.fixture(scope="module")
def action_view_validator() -> Draft202012Validator:
    return _validator("action_view.v1.json")


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/incident_decision.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_incident_decision_fixtures(decision_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in decision_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/incident_decision.v1.invalid.json"), ids=lambda d: d["_name"])
def test_invalid_incident_decision_fixtures(decision_validator: Draft202012Validator, doc: dict) -> None:
    assert not decision_validator.is_valid(_strip(doc))


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/action_view.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_action_view_fixtures(action_view_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in action_view_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/action_view.v1.invalid.json"), ids=lambda d: d["_name"])
def test_invalid_action_view_fixtures(action_view_validator: Draft202012Validator, doc: dict) -> None:
    assert not action_view_validator.is_valid(_strip(doc))
