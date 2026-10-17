"""Hợp đồng spec 003: `threat_seed.v1.json` (tệp nạp danh sách đe dọa) và `bench_report.v1.json` (kết quả bench)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"
SEED = ROOT / "data" / "threat_seed.demo.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.fixture(scope="module")
def seed_validator() -> Draft202012Validator:
    return _validator("threat_seed.v1.json")


@pytest.fixture(scope="module")
def bench_validator() -> Draft202012Validator:
    return _validator("bench_report.v1.json")


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/threat_seed.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_seed_fixtures(seed_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in seed_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/threat_seed.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_seed_fixtures(seed_validator: Draft202012Validator, doc: dict) -> None:
    assert not seed_validator.is_valid(_strip(doc)), doc["_why"]


def test_demo_seed_file_matches_the_contract(seed_validator: Draft202012Validator) -> None:
    assert [e.message for e in seed_validator.iter_errors(_load(SEED))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/bench_report.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_bench_fixtures(bench_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in bench_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/bench_report.v1.invalid.json"), ids=lambda d: d["_why"])
def test_invalid_bench_fixtures(bench_validator: Draft202012Validator, doc: dict) -> None:
    assert not bench_validator.is_valid(_strip(doc)), doc["_why"]
