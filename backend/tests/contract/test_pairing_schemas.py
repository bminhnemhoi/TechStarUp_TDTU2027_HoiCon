"""Hợp đồng spec 020: `pair_request.v1.json`, `pair_response.v1.json`, `consent_record.v1.json`."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.fixture(scope="module")
def pair_request_validator() -> Draft202012Validator:
    return _validator("pair_request.v1.json")


@pytest.fixture(scope="module")
def pair_response_validator() -> Draft202012Validator:
    return _validator("pair_response.v1.json")


@pytest.fixture(scope="module")
def consent_validator() -> Draft202012Validator:
    return _validator("consent_record.v1.json")


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/pair_request.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_pair_request_fixtures(pair_request_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in pair_request_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/pair_request.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_pair_request_fixtures(pair_request_validator: Draft202012Validator, doc: dict) -> None:
    assert not pair_request_validator.is_valid(_strip(doc)), doc["_why"]


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/pair_response.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_pair_response_fixtures(pair_response_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in pair_response_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/pair_response.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_pair_response_fixtures(pair_response_validator: Draft202012Validator, doc: dict) -> None:
    assert not pair_response_validator.is_valid(_strip(doc)), doc["_why"]


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/consent_record.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_consent_fixtures(consent_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in consent_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/consent_record.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_consent_fixtures(consent_validator: Draft202012Validator, doc: dict) -> None:
    assert not consent_validator.is_valid(_strip(doc)), doc["_why"]
