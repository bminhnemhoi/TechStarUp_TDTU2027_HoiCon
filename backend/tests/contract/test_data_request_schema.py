"""Spec 038 T002: hợp đồng `data_request.v1` (yêu cầu xóa từ app + biên nhận)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS / "data_request.v1.json").read_text(encoding="utf-8")), format_checker=FormatChecker()
)


def _docs(kind: str) -> list[dict]:
    return json.loads((SCHEMAS / "fixtures" / f"data_request.v1.{kind}.json").read_text(encoding="utf-8"))


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.mark.parametrize("doc", _docs("valid"), ids=lambda d: d["_name"])
def test_valid_fixtures_pass(doc: dict) -> None:
    assert list(VALIDATOR.iter_errors(_strip(doc))) == []


@pytest.mark.parametrize("doc", _docs("invalid"), ids=lambda d: d["_why"])
def test_invalid_fixtures_fail(doc: dict) -> None:
    assert not VALIDATOR.is_valid(_strip(doc)), doc["_why"]
