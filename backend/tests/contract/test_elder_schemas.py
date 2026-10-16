"""Hợp đồng spec 024: `elder_question.v1.json`, `elder_answer.v1.json`."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "docs" / "schemas"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _checker() -> FormatChecker:
    fc = FormatChecker()

    @fc.checks("date-time")
    def _is_dt(val: object) -> bool:
        if not isinstance(val, str):
            return True
        import datetime

        try:
            datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
            return True
        except Exception:
            return False

    return fc


def _validator(name: str) -> Draft202012Validator:
    schema = _load(SCHEMAS / name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=_checker())


def _strip(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("_name", "_why")}


@pytest.fixture(scope="module")
def question_validator() -> Draft202012Validator:
    return _validator("elder_question.v1.json")


@pytest.fixture(scope="module")
def answer_validator() -> Draft202012Validator:
    return _validator("elder_answer.v1.json")


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/elder_question.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_elder_question_fixtures(question_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in question_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/elder_question.v1.invalid.json"), ids=lambda d: d["_name"])
def test_invalid_elder_question_fixtures(question_validator: Draft202012Validator, doc: dict) -> None:
    assert not question_validator.is_valid(_strip(doc))


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/elder_answer.v1.valid.json"), ids=lambda d: d["_name"])
def test_valid_elder_answer_fixtures(answer_validator: Draft202012Validator, doc: dict) -> None:
    assert [e.message for e in answer_validator.iter_errors(_strip(doc))] == []


@pytest.mark.parametrize("doc", _load(SCHEMAS / "fixtures/elder_answer.v1.invalid.json"), ids=lambda d: d["_name"])
def test_invalid_elder_answer_fixtures(answer_validator: Draft202012Validator, doc: dict) -> None:
    assert not answer_validator.is_valid(_strip(doc))


def test_note_flags_match_domain_and_api() -> None:
    """Cờ E8 ở hợp đồng = cờ API nhận = cờ `NOTE_KEYWORDS` mà `clean_resume`/LLM dùng (ADR-009)."""
    from hoicon.api.routers.elder import NoteFlags
    from hoicon.domain.pii import NOTE_KEYWORDS

    schema = _load(SCHEMAS / "elder_answer.v1.json")["properties"]["note_flags"]["properties"]
    assert set(schema) == set(NoteFlags.model_fields) == set(NOTE_KEYWORDS)


def test_every_elder_question_discloses_ai() -> None:
    """Luật 6: mọi câu E8 (thật và diễn tập) mở đầu bằng câu công khai AI; diễn tập có nhãn ngay sau đó (luật 8)."""
    from hoicon.agents import texts

    question_ids = _load(SCHEMAS / "elder_question.v1.json")["properties"]["question_id"]["enum"]
    assert set(question_ids) == set(texts.QUESTIONS)
    for qid in question_ids:
        assert texts.question_for_elder(qid, False).startswith(texts.AI_DISCLOSURE)
        assert texts.question_for_elder(qid, True).startswith(f"{texts.AI_DISCLOSURE} {texts.DRILL_LABEL}")
