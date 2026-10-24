"""Hợp đồng spec 037 FR-001/FR-002: `error.v1.json` (mã lỗi cố định mà app/web dựa vào).

Chạy được ở đây: fixture hợp lệ/không hợp lệ; enum `purpose` == mục đích trong manifest đồng ý; mã `consent_withdrawn`
của `routers/events.py` và `routers/devices.py` thuộc enum `error`. KHÔNG kiểm được thân phản hồi thật khớp lược đồ:
thân thật là `{"detail": "consent_withdrawn"}` (Android đọc dạng này), lược đồ mô tả `{"error": ..., "purpose": ...}`.
Lệch hợp đồng: xem `tests/integration/test_error_body_contract.py` (xfail có chủ đích) và evidence 037 T013."""

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from hoicon.api.routers import devices, events

DOCS = Path(__file__).resolve().parents[3] / "docs"
SCHEMAS = DOCS / "schemas"
MANIFEST = DOCS / "legal" / "consent" / "manifest.json"


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


def test_purpose_enum_equals_the_purposes_of_the_consent_manifest() -> None:
    manifest_purposes = [entry["purpose"] for entry in _load(MANIFEST)["purposes"]]
    assert SCHEMA["properties"]["purpose"]["enum"] == manifest_purposes  # cùng giá trị, cùng thứ tự


@pytest.mark.parametrize("code", [events.CONSENT_WITHDRAWN, devices.CONSENT_WITHDRAWN], ids=["events", "devices"])
def test_the_code_sent_by_the_server_is_in_the_error_enum(code: str) -> None:
    assert code in SCHEMA["properties"]["error"]["enum"]
