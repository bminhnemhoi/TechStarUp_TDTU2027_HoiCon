"""Hợp đồng spec 033: `sim_run_request`, `sim_run`, `sim_scenarios`, `graph_topology` (FR-001)."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
NAMES = ["sim_run_request", "sim_run", "sim_scenarios", "graph_topology"]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.glob("*.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / f"{name}.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


def _fixtures(name: str, kind: str) -> list[dict[str, Any]]:
    return _load(SCHEMAS / "fixtures" / f"{name}.v1.{kind}.json")


@pytest.mark.parametrize("name", NAMES)
def test_valid_fixtures_pass(name: str) -> None:
    validator = _validator(name)
    docs = _fixtures(name, "valid")
    assert docs
    for doc in docs:
        assert not list(validator.iter_errors(_strip(doc))), (name, doc["_name"])


@pytest.mark.parametrize("name", NAMES)
def test_invalid_fixtures_fail(name: str) -> None:
    validator = _validator(name)
    docs = _fixtures(name, "invalid")
    assert docs
    for doc in docs:
        assert list(validator.iter_errors(_strip(doc))), (name, doc["_why"])


def test_every_guardian_message_must_open_with_the_ai_disclosure() -> None:
    validator = _validator("sim_run")
    doc = _strip(_fixtures("sim_run", "valid")[-1])
    doc["guardian_messages"] = [{"at": "2026-12-01T02:15:30Z", "template": "detail", "text": "Anh/chị gọi Mẹ nhé."}]
    assert list(validator.iter_errors(doc))
