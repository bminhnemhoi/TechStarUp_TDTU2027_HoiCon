"""Hợp đồng cập nhật webhook Zalo (docs/schemas/zalo_update.v1.json). Fixture dùng chung với mock và test webhook."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _load(name: str):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = _load("zalo_update.v1.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


@pytest.mark.parametrize("update", _load("fixtures/zalo_update.v1.valid.json"), ids=lambda u: u["_name"])
def test_valid_fixtures(validator: Draft202012Validator, update: dict) -> None:
    payload = {k: v for k, v in update.items() if k != "_name"}
    assert [e.message for e in validator.iter_errors(payload)] == []


@pytest.mark.parametrize("case", _load("fixtures/zalo_update.v1.invalid.json"), ids=lambda c: c["_why"])
def test_invalid_fixtures(validator: Draft202012Validator, case: dict) -> None:
    payload = {k: v for k, v in case.items() if k != "_why"}
    assert not validator.is_valid(payload), case["_why"]


def test_dedupe_key_is_message_id() -> None:
    """Zalo không gửi update_id (docs/spikes/P1-S3-zalo.md §1): khóa chống trùng là message.message_id."""
    text_rule = _load("zalo_update.v1.json")["$defs"]["text_message"]
    assert "message_id" in text_rule["required"]


def test_fixtures_are_fictional_and_unpaired_with_real_ids() -> None:
    """Định danh trong fixture phải là hư cấu (tiền tố `fixture`), không phải ID/tên thật (CLAUDE.md luật 2)."""
    for update in _load("fixtures/zalo_update.v1.valid.json"):
        message = update["result"].get("message")
        if message:
            assert message["from"]["id"].startswith("fixture")
            assert message["chat"]["id"].startswith("fixture")
            assert message["from"].get("display_name", "Người giám hộ mẫu").startswith("Người giám hộ mẫu")
