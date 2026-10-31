"""Hợp đồng spec 021: `events_batch.v1.json`, `events_result.v1.json`, `incident.v1.json` (FR-003, FR-009)."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
BASE = "https://hoicon.vn/schemas/"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.glob("*.v1.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validator(ref: str) -> Draft202012Validator:
    Draft202012Validator.check_schema(_load(SCHEMAS / ref.split("#")[0]))
    return Draft202012Validator({"$ref": BASE + ref}, registry=_registry(), format_checker=FormatChecker())


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why", "_as")}


def _incident_ref(doc: dict[str, Any]) -> str:
    return f"incident.v1.json#/$defs/{doc['_as']}"


def _errors(validator: Draft202012Validator, doc: dict[str, Any]) -> list[str]:
    return [e.message for e in validator.iter_errors(_strip(doc))]


def _fixture(name: str) -> list[dict[str, Any]]:
    return _load(SCHEMAS / "fixtures" / name)


@pytest.mark.parametrize("name", ["events_batch", "events_result"])
def test_valid_fixtures(name: str) -> None:
    validator = _validator(f"{name}.v1.json")
    for doc in _fixture(f"{name}.v1.valid.json"):
        assert _errors(validator, doc) == [], doc["_name"]


@pytest.mark.parametrize("name", ["events_batch", "events_result"])
def test_invalid_fixtures(name: str) -> None:
    validator = _validator(f"{name}.v1.json")
    for doc in _fixture(f"{name}.v1.invalid.json"):
        assert _errors(validator, doc), doc["_why"]


def test_incident_valid_fixtures() -> None:
    for doc in _fixture("incident.v1.valid.json"):
        assert _errors(_validator(_incident_ref(doc)), doc) == [], doc["_name"]


def test_incident_invalid_fixtures() -> None:
    for doc in _fixture("incident.v1.invalid.json"):
        assert _errors(_validator(_incident_ref(doc)), doc), doc["_why"]


def test_incident_root_is_the_detail_document() -> None:
    root = _validator("incident.v1.json")
    detail = next(d for d in _fixture("incident.v1.valid.json") if d["_as"] == "detail")
    assert _errors(root, detail) == []
    assert _errors(root, next(d for d in _fixture("incident.v1.valid.json") if d["_as"] == "list"))


def test_batch_is_capped_at_50_events() -> None:
    validator = _validator("events_batch.v1.json")
    event = _fixture("risk_event.v1.valid.json")[0]
    assert validator.is_valid({"events": [event] * 50})
    assert not validator.is_valid({"events": [event] * 51})
    assert not validator.is_valid({"events": []})


def test_no_schema_can_carry_a_raw_phone_number() -> None:
    """FR-009: chỉ có h1 (hex 64) + last3; không trường tự do nào cho số điện thoại/tên thật."""
    batch = _load(SCHEMAS / "events_batch.v1.json")
    risk = _load(SCHEMAS / "risk_event.v1.json")
    assert batch["additionalProperties"] is False and risk["additionalProperties"] is False
    assert risk["properties"]["caller"]["additionalProperties"] is False
    assert set(risk["properties"]["caller"]["properties"]) == {"h1", "last3", "in_contacts", "trusted", "flagged"}
    for name in ("events_result", "incident"):
        names = _property_names(_load(SCHEMAS / f"{name}.v1.json"))
        assert names.isdisjoint({"phone", "h1", "last3", "caller", "e164", "caller_hmac"}), name


def _property_names(node: Any) -> set[str]:
    """Mọi tên thuộc tính khai báo (đệ quy), bỏ qua chữ mô tả."""
    found: set[str] = set()
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            found |= set(props)
        for value in node.values():
            found |= _property_names(value)
    elif isinstance(node, list):
        for value in node:
            found |= _property_names(value)
    return found
