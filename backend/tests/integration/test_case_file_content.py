"""Spec 031 FR-004: `build_content` tất định, đúng `case_file.v1#/$defs/content`, không PII."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from case_support import FAKE_HMAC, FAKE_LAST3, purge_case, seed_case
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from hoicon.db.session import get_sessionmaker
from hoicon.services.case_file_service import build_content

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _validator() -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = {"$ref": "https://hoicon.vn/schemas/case_file.v1.json#/$defs/content"}
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


CONTENT = _validator()
SECRETS = ["0900000123", FAKE_HMAC, "vn.hoicon.demobank", "+84900000123"]


@pytest.fixture
async def case(require_db: None) -> AsyncGenerator[SimpleNamespace]:
    world = await seed_case()
    yield world
    await purge_case(world)


async def content_of(world: SimpleNamespace, **kwargs: Any) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        return await build_content(session, world.incident, **kwargs)


async def test_content_is_valid_and_has_the_known_facts(case: SimpleNamespace) -> None:
    content = await content_of(case)
    CONTENT.validate(content)
    assert content["elder_alias"] == "Mẹ" and content["level"] == "critical" and content["app_category"] == "bank"
    assert content["caller_last3"] == FAKE_LAST3
    assert content["guardian_decision"] == "scam"
    assert content["ai_label"].startswith("Đây là trợ lý AI HỏiCon")
    assert [a["answer"] for a in content["elder_answers"]] == ["Có", "Có"]
    assert content["verifications"] == [
        {"kind": "phone", "verdict": "dangerous", "source": "Danh sách cảnh báo HỏiCon", "list_version": "2026-12-19"}
    ]
    assert len(content["timeline"]) == 4 and content["timeline"][-1]["text"].startswith(
        "Người giám hộ chọn: nghi lừa đảo"
    )
    assert any("danh sách số bị báo" in r for r in content["reasons"])
    assert content["rule"].startswith("Đang nghe số lạ")
    assert {f["key"] for f in content["local_fields"]} >= {"caller_phone", "amount"}


async def test_content_never_carries_the_secrets_of_the_incident(case: SimpleNamespace) -> None:
    blob = json.dumps(await content_of(case), ensure_ascii=False)
    for secret in SECRETS:
        assert secret not in blob, secret


async def test_content_is_deterministic(case: SimpleNamespace) -> None:
    assert await content_of(case) == await content_of(case)


async def test_a_given_summary_replaces_the_template(case: SimpleNamespace) -> None:
    content = await content_of(case, summary="Một đoạn tóm tắt sạch.")
    assert content["summary"] == "Một đoạn tóm tắt sạch."
    CONTENT.validate(content)


async def test_without_verifications_the_list_is_empty_and_a_floor_reason_is_given(require_db: None) -> None:
    world = await seed_case(flagged=False, answers=())
    try:
        content = await content_of(world)
        CONTENT.validate(content)
        assert content["verifications"] == [] and content["elder_answers"] == []
        assert content["reasons"] == ["Mức rủi ro do luật trên điện thoại xác định"]
    finally:
        await purge_case(world)


async def test_a_sideload_case_without_a_call_has_no_last3(require_db: None) -> None:
    world = await seed_case(app_category="sideloaded", rule_id="R2", caller_last3=None, flagged=False, answers=())
    try:
        content = await content_of(world)
        CONTENT.validate(content)
        assert content["caller_last3"] is None and content["app_category"] == "sideloaded"
        assert any("CH Play" in r for r in content["reasons"])
    finally:
        await purge_case(world)


async def test_a_decision_from_the_web_or_jwt_is_emergency_pause(require_db: None) -> None:
    world = await seed_case(reason="guardian_jwt")
    try:
        assert (await content_of(world))["guardian_decision"] == "emergency_pause"
    finally:
        await purge_case(world)


async def test_unknown_incident_is_an_error(require_db: None) -> None:
    from uuid import uuid4

    async with get_sessionmaker()() as session:
        with pytest.raises(LookupError):
            await build_content(session, uuid4())


def test_report_guidance_is_pending_approval_and_has_no_phone_numbers() -> None:
    import re

    import yaml

    doc = yaml.safe_load((SCHEMAS.parents[1] / "data" / "case_file" / "report_guidance.vi.yaml").read_text("utf-8"))
    assert doc["approved"] is False and doc["fallback_vi"]
    assert not re.search(r"\d{3,}", json.dumps(doc, ensure_ascii=False))
