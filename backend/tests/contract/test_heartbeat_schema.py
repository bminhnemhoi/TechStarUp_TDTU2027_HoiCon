"""Hợp đồng spec 029: `heartbeat.v1.json` (thân `POST /v1/heartbeat`) và `pilot_report.v1.json` (đầu ra
`ops pilot report`). Fixture valid của heartbeat phải khớp thân Android dựng (`PairingApiClient.sendHeartbeat`)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    resources = []
    for path in SCHEMAS.glob("*.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    schema = _load(SCHEMAS / f"{name}.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=Registry().with_resources(resources), format_checker=FormatChecker())


def _fixtures(name: str, kind: str):
    return _load(SCHEMAS / "fixtures" / f"{name}.v1.{kind}.json")


@pytest.mark.parametrize("name", ["heartbeat", "pilot_report"])
def test_the_valid_fixture_passes(name: str) -> None:
    assert not list(_validator(name).iter_errors(_fixtures(name, "valid")))


@pytest.mark.parametrize("name", ["heartbeat", "pilot_report"])
def test_every_invalid_fixture_is_rejected(name: str) -> None:
    cases = _fixtures(name, "invalid")
    assert len(cases) >= 4
    for case in cases:
        doc = {k: v for k, v in case.items() if k != "_name"}
        assert list(_validator(name).iter_errors(doc)), f"phải bị từ chối: {case['_name']}"


def test_the_heartbeat_fixture_has_exactly_the_keys_android_sends() -> None:
    """Android gửi app_version, rules_version, permission_state (+ threat_list_version nếu có) và không gì khác."""
    schema = _load(SCHEMAS / "heartbeat.v1.json")
    assert set(schema["properties"]) == {"app_version", "rules_version", "threat_list_version", "permission_state"}
    assert schema["additionalProperties"] is False
    assert set(_fixtures("heartbeat", "valid")) == set(schema["properties"])


def test_the_pilot_report_cannot_carry_member_names_or_secrets() -> None:
    schema = _load(SCHEMAS / "pilot_report.v1.json")
    family = schema["properties"]["families"]["items"]
    device = family["properties"]["devices"]["items"]
    assert family["additionalProperties"] is False and device["additionalProperties"] is False
    assert device["properties"]["device"]["pattern"] == "^[0-9a-f]{8}$"  # chỉ 8 ký tự đầu của id
