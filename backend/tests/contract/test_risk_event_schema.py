"""Hợp đồng sự kiện máy → máy chủ (docs/schemas/risk_event.v1.json). Fixture dùng chung với test Kotlin."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _load(name: str):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = _load("risk_event.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.parametrize("event", _load("fixtures/risk_event.v1.valid.json"), ids=lambda e: e["type"])
def test_valid_fixtures(validator: Draft202012Validator, event: dict) -> None:
    errors = [e.message for e in validator.iter_errors(event)]
    assert errors == []


@pytest.mark.parametrize("case", _load("fixtures/risk_event.v1.invalid.json"), ids=lambda c: c["_why"])
def test_invalid_fixtures(validator: Draft202012Validator, case: dict) -> None:
    event = {k: v for k, v in case.items() if k != "_why"}
    assert not validator.is_valid(event), case["_why"]


def test_schema_has_no_raw_phone_field() -> None:
    """Sự kiện chỉ mang h1 + last3 (ADR-006) — không có trường số điện thoại thô."""
    caller = _load("risk_event.v1.json")["properties"]["caller"]["properties"]
    assert set(caller) <= {"h1", "last3", "in_contacts", "trusted", "flagged"}
