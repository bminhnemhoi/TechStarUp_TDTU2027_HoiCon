"""Hợp đồng spec 027: `guardian_session.v1.json`, `incident_list.v1.json` và phần mở rộng của `incident.v1.json`."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
FIXTURES = SCHEMAS / "fixtures"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources = []
    for path in SCHEMAS.glob("*.v1.json"):
        doc = _load(path)
        resources.append((doc["$id"], Resource.from_contents(doc)))
    return Registry().with_resources(resources)


def _validator(name: str, fragment: str = "") -> Draft202012Validator:
    schema = _load(SCHEMAS / f"{name}.v1.json")
    Draft202012Validator.check_schema(schema)
    if fragment:
        schema = {"$ref": f"{schema['$id']}#/$defs/{fragment}"}
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why", "_as")}


def _fixtures(name: str, kind: str) -> list[dict[str, Any]]:
    return _load(FIXTURES / f"{name}.v1.{kind}.json")


def _for(name: str, doc: dict[str, Any]) -> Draft202012Validator:
    return _validator(name, doc["_as"]) if "_as" in doc else _validator(name)


@pytest.mark.parametrize("name", ["guardian_session", "incident_list"])
def test_valid_fixtures_pass(name: str) -> None:
    docs = _fixtures(name, "valid")
    assert docs, "mỗi schema phải có ít nhất một fixture hợp lệ"
    for doc in docs:
        assert [e.message for e in _for(name, doc).iter_errors(_strip(doc))] == [], doc["_name"]


@pytest.mark.parametrize("name", ["guardian_session", "incident_list"])
def test_invalid_fixtures_fail(name: str) -> None:
    docs = _fixtures(name, "invalid")
    assert len(docs) >= 5
    for doc in docs:
        assert not _for(name, doc).is_valid(_strip(doc)), doc["_why"]


def test_session_invalid_fixtures_cover_the_required_cases() -> None:
    reasons = " ".join(doc["_why"] for doc in _fixtures("guardian_session", "invalid"))
    for needle in ("ký tự lạ", "lộ token phiên", "lộ số điện thoại"):
        assert needle in reasons
    assert any("next_cursor" in doc["_why"] and "dài" in doc["_why"] for doc in _fixtures("incident_list", "invalid"))


def test_session_response_never_carries_a_token_phone_or_zalo_id() -> None:
    props = _load(SCHEMAS / "guardian_session.v1.json")["$defs"]["response"]["properties"]
    assert not {"token", "access_token", "phone", "zalo_id", "chat_id", "email"} & set(props)


def test_previous_incident_fixtures_still_pass() -> None:
    """Thêm `elder_alias`/`has_run`/`run_id` là tùy chọn: fixture cũ của spec 021 không bị đổi kết quả."""
    for doc in _load(FIXTURES / "incident.v1.valid.json"):
        assert _validator("incident", doc["_as"]).is_valid(_strip(doc)), doc["_name"]
    for doc in _load(FIXTURES / "incident.v1.invalid.json"):
        assert not _validator("incident", doc["_as"]).is_valid(_strip(doc)), doc["_why"]


def test_incident_summary_accepts_the_guardian_fields_and_rejects_bad_types() -> None:
    validator = _validator("incident", "summary")
    base = _strip(_fixtures("incident_list", "valid")[0]["incidents"][0])
    assert validator.is_valid(base)
    assert validator.is_valid({**base, "elder_alias": None, "run_id": "01928f3a-7b2c-7d4e-8f10-2a3b4c5d6eb1"})
    assert not validator.is_valid({**base, "elder_alias": "x" * 65})
    assert not validator.is_valid({**base, "run_id": "khong-phai-uuid"})
