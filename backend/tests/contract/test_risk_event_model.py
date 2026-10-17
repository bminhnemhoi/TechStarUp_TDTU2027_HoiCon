"""Pydantic RiskEvent khớp hợp đồng docs/schemas/risk_event.v1.json (CLAUDE.md luật 10)."""

import json
import typing
from pathlib import Path

import pytest
from pydantic import ValidationError

from hoicon.domain.events import App, AppCategory, EventType, RiskEvent, RuleId
from hoicon.domain.risk import RiskLevel

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def schema() -> dict:
    return json.loads((SCHEMAS / "risk_event.v1.json").read_text(encoding="utf-8"))


def test_enums_match_schema() -> None:
    props = schema()["properties"]
    assert list(typing.get_args(EventType)) == props["type"]["enum"]
    assert list(typing.get_args(RuleId)) == props["rule_id"]["enum"]
    assert [level.value for level in RiskLevel] == props["rule_floor"]["enum"]
    assert list(typing.get_args(AppCategory)) == props["app"]["properties"]["category"]["enum"]
    assert set(App.model_fields) <= set(props["app"]["properties"])


def test_valid_fixtures_parse() -> None:
    for raw in json.loads((SCHEMAS / "fixtures" / "risk_event.v1.valid.json").read_text(encoding="utf-8")):
        event = RiskEvent.model_validate(raw)
        assert event.rule_floor in RiskLevel


def test_raw_phone_number_is_rejected() -> None:
    raw = json.loads((SCHEMAS / "fixtures" / "risk_event.v1.valid.json").read_text(encoding="utf-8"))[0]
    raw["caller"]["h1"] = "0900000001"
    with pytest.raises(ValidationError):
        RiskEvent.model_validate(raw)
