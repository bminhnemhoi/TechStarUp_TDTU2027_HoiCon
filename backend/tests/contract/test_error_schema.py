"""Hợp đồng spec 037 FR-001/FR-002: `error.v1.json` (mã lỗi cố định mà app/web dựa vào).

Fixture hợp lệ/không hợp lệ; mã `consent_withdrawn` của `routers/events.py`, `routers/devices.py` thuộc `$defs.code`;
câu 422 của `routers/consents.py` hợp lệ. Thân phản hồi thật: `tests/integration/test_error_body_contract.py`."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from hoicon.api.routers import consents, devices, events

DOCS = Path(__file__).resolve().parents[3] / "docs"
SCHEMAS = DOCS / "schemas"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


SCHEMA = _load(SCHEMAS / "error.v1.json")


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA, format_checker=FormatChecker())


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/error.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_fixtures(validator: Draft202012Validator, doc: dict[str, Any]) -> None:
    assert [e.message for e in validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/error.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_fixtures(validator: Draft202012Validator, doc: dict[str, Any]) -> None:
    assert not validator.is_valid(_strip(doc)), doc["_why"]


@pytest.mark.parametrize("code", [events.CONSENT_WITHDRAWN, devices.CONSENT_WITHDRAWN], ids=["events", "devices"])
def test_the_code_sent_by_the_server_is_in_the_error_enum(code: str) -> None:
    assert code in SCHEMA["$defs"]["code"]["enum"]


def test_the_422_sentence_of_consents_is_a_valid_body(validator: Draft202012Validator) -> None:
    assert validator.is_valid({"detail": consents.UNKNOWN_TEXT})
