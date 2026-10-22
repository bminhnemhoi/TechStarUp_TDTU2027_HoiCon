"""Hợp đồng spec 031: `case_file.v1.json`, `case_file_action.v1.json` (FR-001)."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
NAMES = ["case_file", "case_file_action"]


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
