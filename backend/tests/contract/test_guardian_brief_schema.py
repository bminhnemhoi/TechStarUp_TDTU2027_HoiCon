"""Hợp đồng `guardian_brief.v2.json` (ADR-012, spec 024 FR-011): enum mã điểm là nguồn sự thật cho `BriefPoint`."""

import json
import typing
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from hoicon.agents.incident_graph import Action, BriefPoint, GuardianBrief

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
SCHEMA = json.loads((SCHEMAS / "guardian_brief.v2.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)


def _fixture(kind: str) -> list[dict[str, Any]]:
    return json.loads((SCHEMAS / "fixtures" / f"guardian_brief.v2.{kind}.json").read_text(encoding="utf-8"))


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


def test_schema_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_valid_fixtures_pass() -> None:
    docs = _fixture("valid")
    assert docs
    for doc in docs:
        assert not list(VALIDATOR.iter_errors(_strip(doc))), doc["_name"]


def test_invalid_fixtures_fail() -> None:
    docs = _fixture("invalid")
    assert len(docs) >= 5
    for doc in docs:
        assert list(VALIDATOR.iter_errors(_strip(doc))), doc["_name"]


def test_point_enum_equals_pydantic_literal() -> None:
    assert set(SCHEMA["properties"]["points"]["items"]["enum"]) == set(typing.get_args(BriefPoint))
    assert len(typing.get_args(BriefPoint)) == 11


def test_action_enum_equals_pydantic_literal() -> None:
    assert set(SCHEMA["properties"]["action"]["enum"]) == set(typing.get_args(Action))


def test_model_json_schema_is_closed() -> None:
    assert GuardianBrief.model_json_schema()["additionalProperties"] is False


def test_pydantic_agrees_with_the_fixtures() -> None:
    for doc in _fixture("valid"):
        GuardianBrief.model_validate(_strip(doc))
    for doc in _fixture("invalid"):
        with pytest.raises(ValueError):
            GuardianBrief.model_validate(_strip(doc))
