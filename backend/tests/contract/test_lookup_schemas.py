"""Hợp đồng spec 026: `lookup_request.v1.json`, `lookup_result.v1.json`, `threat_list.v1.json`."""

import base64
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"
AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon."


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


def _fixtures(name: str, kind: str) -> list[dict]:
    return _load(SCHEMAS / "fixtures" / f"{name}.v1.{kind}.json")


NAMES = ["lookup_request", "lookup_result", "threat_list"]
VALIDATORS = {n: _validator(f"{n}.v1.json") for n in NAMES}


@pytest.mark.parametrize("name", NAMES)
def test_valid_fixtures_pass(name: str) -> None:
    docs = _fixtures(name, "valid")
    assert docs, "mỗi schema phải có ít nhất một fixture hợp lệ"
    for doc in docs:
        assert [e.message for e in VALIDATORS[name].iter_errors(_strip(doc))] == [], doc["_name"]


@pytest.mark.parametrize("name", NAMES)
def test_invalid_fixtures_fail(name: str) -> None:
    docs = _fixtures(name, "invalid")
    assert len(docs) >= 5
    for doc in docs:
        assert not VALIDATORS[name].is_valid(_strip(doc)), doc["_why"]


def test_every_valid_result_opens_with_the_ai_disclosure() -> None:
    for doc in _fixtures("lookup_result", "valid"):
        assert doc["disclaimer"].startswith(AI_DISCLOSURE), doc["_name"]


def test_result_without_the_disclosure_is_rejected() -> None:
    doc = _strip(_fixtures("lookup_result", "valid")[0])
    doc["disclaimer"] = "Kết quả chỉ để tham khảo."
    assert not VALIDATORS["lookup_result"].is_valid(doc)


@pytest.mark.parametrize("field", ["h1", "subject_hmac", "url", "number", "phone"])
def test_result_never_allows_identifying_fields(field: str) -> None:
    doc = _strip(_fixtures("lookup_result", "valid")[0])
    doc[field] = "x"
    assert not VALIDATORS["lookup_result"].is_valid(doc)


@pytest.mark.parametrize("field", ["number", "phone", "e164", "msisdn"])
def test_phone_request_rejects_raw_number_fields(field: str) -> None:
    doc = _strip(_fixtures("lookup_request", "valid")[0])
    doc[field] = "0900000123"
    assert not VALIDATORS["lookup_request"].is_valid(doc)


def test_request_kind_account_is_reserved() -> None:
    doc = {"kind": "account", "via": "typed", "h1": "a" * 64, "last3": "123"}
    assert not VALIDATORS["lookup_request"].is_valid(doc)


def test_threat_list_buckets_decode_to_a_multiple_of_three_bytes() -> None:
    for doc in _fixtures("threat_list", "valid"):
        raw = base64.b64decode(doc["buckets_b64"], validate=True)
        assert len(raw) == 3 * doc["count"], doc["_name"]


def test_threat_list_has_no_identifying_fields() -> None:
    properties = _load(SCHEMAS / "threat_list.v1.json")["properties"]
    assert not {"h1", "hmac", "last3", "subject_hmac", "value_hmac"} & set(properties)


def test_consent_record_accepts_the_lookups_purpose() -> None:
    schema = _load(SCHEMAS / "consent_record.v1.json")
    purposes = schema["properties"]["items"]["items"]["properties"]["purpose"]["enum"]
    assert "lookups" in purposes
    assert len(purposes) == len(set(purposes))
