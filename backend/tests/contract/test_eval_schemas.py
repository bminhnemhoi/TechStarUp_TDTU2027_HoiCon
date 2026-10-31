"""Hợp đồng eval (spec 030): `eval_cassette.v1.json` và `eval_report.v1.json` + fixture dùng chung với `hoicon.eval`."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"
CASSETTES = ROOT / "backend" / "eval" / "cassettes" / "smoke"
SUITE = ROOT / "backend" / "eval" / "suites" / "smoke.v1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.fixture(scope="module")
def cassette_validator() -> Draft202012Validator:
    return _validator("eval_cassette.v1.json")


@pytest.fixture(scope="module")
def report_validator() -> Draft202012Validator:
    return _validator("eval_report.v1.json")


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/eval_cassette.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_cassette_fixtures(cassette_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in cassette_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/eval_cassette.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_cassette_fixtures(cassette_validator: Draft202012Validator, doc: dict) -> None:
    assert not cassette_validator.is_valid(_strip(doc)), doc["_why"]


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/eval_report.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_report_fixtures(report_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in report_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/eval_report.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_report_fixtures(report_validator: Draft202012Validator, doc: dict) -> None:
    assert not report_validator.is_valid(_strip(doc)), doc["_why"]


def test_every_smoke_cassette_is_valid_and_named_after_its_case(cassette_validator: Draft202012Validator) -> None:
    files = sorted(CASSETTES.glob("*.json")) if CASSETTES.is_dir() else []
    if not files:
        pytest.skip("chưa có cassette smoke (T010)")
    for path in files:
        doc = _load(path)
        assert [e.message for e in cassette_validator.iter_errors(doc)] == [], path.name
        assert doc["case_id"] == path.stem, path.name


def test_smoke_suite_and_cassettes_match() -> None:
    if not SUITE.is_file() or not CASSETTES.is_dir():
        pytest.skip("chưa có suite/cassette smoke (T005, T010)")
    suite_ids = set(_load(SUITE)["cases"])
    assert suite_ids == {p.stem for p in CASSETTES.glob("*.json")}
