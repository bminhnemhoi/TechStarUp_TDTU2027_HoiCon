"""Hợp đồng spec 020: `device_me.v1.json` (GET /v1/devices/me) và giới hạn lô của `consent_record.v1.json`."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = _load(SCHEMAS / "device_me.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/device_me.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_fixtures(validator: Draft202012Validator, doc: dict[str, Any]) -> None:
    assert [e.message for e in validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/device_me.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_fixtures(validator: Draft202012Validator, doc: dict[str, Any]) -> None:
    assert not validator.is_valid(_strip(doc)), doc["_why"]


def test_consent_batch_is_capped_at_32_items() -> None:
    validator = Draft202012Validator(_load(SCHEMAS / "consent_record.v1.json"))
    item = _load(SCHEMAS / "fixtures/consent_record.v1.valid.json")[0]["items"][0]
    assert validator.is_valid({"items": [item] * 32})
    assert not validator.is_valid({"items": [item] * 33})
