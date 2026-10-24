"""Spec 031 FR-007 (SC-002, SC-004): `GET/POST /v1/guardian/incidents/{id}/case-file`."""

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from case_support import FAKE_HMAC, purge_case, seed_case
from consent_support import call
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import func, select

from hoicon.api.auth import issue_guardian_access_token
from hoicon.config import get_settings
from hoicon.db.models import CaseFile, Incident, IncidentTransition, Job
from hoicon.db.session import get_sessionmaker
from hoicon.services import case_file_service

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Sec-Fetch-Site": "same-origin"}
RAW_VALUES = ("0900000123", FAKE_HMAC, "vn.hoicon.demobank", "+84900000123")


def _validator(name: str) -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = json.loads((SCHEMAS / f"{name}.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


CASE_FILE = _validator("case_file")


@pytest.fixture
async def world(require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[SimpleNamespace]:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()
    mine = await seed_case(with_run=False)
    other = await seed_case(with_run=False)
    async with get_sessionmaker().begin() as session:
        for w in (mine, other):
            content = await case_file_service.build_content(session, w.incident)
            session.add(CaseFile(incident_id=w.incident, family_id=w.family, content=content, is_demo=True))
    mine.token = issue_guardian_access_token(mine.guardian, mine.family)
    other.token = issue_guardian_access_token(other.guardian, other.family)
    yield SimpleNamespace(mine=mine, other=other)
    for w in (mine, other):
        await purge_case(w)
    get_settings.cache_clear()


def url(w: SimpleNamespace) -> str:
    return f"/v1/guardian/incidents/{w.incident}/case-file"


async def act(w: SimpleNamespace, action: str, token: str | None = None, **headers: str) -> Any:
    return await call("POST", url(w), token=token or w.token, json={"action": action}, headers={**ORIGIN, **headers})


async def state_of(w: SimpleNamespace) -> tuple[str, str]:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, w.incident, populate_existing=True)
        case = await session.scalar(select(CaseFile.status).where(CaseFile.incident_id == w.incident))
    return incident.state, case


async def test_get_returns_the_draft_in_the_contract_and_without_raw_values(world: SimpleNamespace) -> None:
    res = await call("GET", url(world.mine), token=world.mine.token)
    assert res.status_code == 200, res.text
    CASE_FILE.validate(res.json())
    assert res.json()["status"] == "draft" and res.headers["cache-control"] == "no-store"
    for raw in RAW_VALUES:
        assert raw not in res.text, raw


async def test_guidance_is_always_sent_and_has_no_steps_while_unapproved(world: SimpleNamespace) -> None:
    res = await call("GET", url(world.mine), token=world.mine.token)
    body = res.json()
    CASE_FILE.validate(body)
    assert body["guidance"]["approved"] is False and body["guidance"]["steps"] == []
    assert len(body["guidance"]["fallback_vi"]) >= 10
    assert not re.search(r"\d{4,}", json.dumps(body["guidance"], ensure_ascii=False))  # không số đường dây chưa kiểm


async def test_an_approved_guidance_file_shows_every_step_in_order_and_validates(
    world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    file = tmp_path / "guidance.yaml"
    file.write_text(
        "approved: true\nfallback_vi: Anh/chị liên hệ công an nơi cư trú.\nsteps:\n"
        "  - {id: contact_bank, text_vi: Gọi tổng đài ghi sau thẻ của ngân hàng., source_ref: null}\n"
        "  - {id: contact_police, text_vi: Mang hồ sơ tới công an phường hoặc xã., source_ref: Nguồn thử}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(case_file_service, "GUIDANCE_FILE", file)
    case_file_service.load_guidance.cache_clear()
    try:
        body = (await call("GET", url(world.mine), token=world.mine.token)).json()
        CASE_FILE.validate(body)
        assert body["guidance"]["approved"] is True
        assert [s["id"] for s in body["guidance"]["steps"]] == ["contact_bank", "contact_police"]
        posted = await act(world.mine, "approve")  # POST cũng trả `guidance`
        assert posted.status_code == 200 and posted.json()["guidance"]["approved"] is True
    finally:
        case_file_service.load_guidance.cache_clear()


async def test_another_family_and_unknown_ids_are_404(world: SimpleNamespace) -> None:
    assert (await call("GET", url(world.other), token=world.mine.token)).status_code == 404
    assert (await act(world.other, "approve", token=world.mine.token)).status_code == 404
    res = await call("GET", f"/v1/guardian/incidents/{uuid4()}/case-file", token=world.mine.token)
    assert res.status_code == 404
    assert (await call("GET", url(world.mine))).status_code == 401


async def test_wrong_origin_is_forbidden_and_unknown_fields_are_422(world: SimpleNamespace) -> None:
    evil = {"Origin": "https://evil.example"}
    res = await call("POST", url(world.mine), token=world.mine.token, json={"action": "approve"}, headers=evil)
    assert res.status_code == 403
    bad = {"action": "approve", "caller_phone": "0900000123"}  # ô tự điền không bao giờ được gửi
    assert (await call("POST", url(world.mine), token=world.mine.token, json=bad, headers=ORIGIN)).status_code == 422
    assert (await act(world.mine, "xoa_het")).status_code == 422
    assert await state_of(world.mine) == ("case_open", "draft")


@pytest.mark.parametrize(
    ("steps", "expected_incident", "expected_case"),
    [
        (["approve"], "case_open", "approved"),
        (["approve", "mark_sent"], "closed", "sent"),
        (["approve", "discard"], "closed", "discarded"),
        (["discard"], "closed", "discarded"),
    ],
)
async def test_valid_paths(
    world: SimpleNamespace, steps: list[str], expected_incident: str, expected_case: str
) -> None:
    for action in steps:
        res = await act(world.mine, action)
        assert res.status_code == 200, (action, res.text)
        CASE_FILE.validate(res.json())
    assert await state_of(world.mine) == (expected_incident, expected_case)
    async with get_sessionmaker()() as session:
        reasons = list(
            await session.scalars(
                select(IncidentTransition.reason).where(
                    IncidentTransition.incident_id == world.mine.incident, IncidentTransition.to_state == "closed"
                )
            )
        )
        key = f"{world.mine.incident}:case_action"
        resumes = await session.scalar(select(func.count()).select_from(Job).where(Job.idempotency_key.startswith(key)))
    if expected_incident == "closed":
        assert reasons and reasons[0] in ("case_sent", "case_discarded")
    assert resumes == sum(1 for a in steps if a in ("approve", "discard"))


@pytest.mark.parametrize(
    ("setup", "action"),
    [
        ([], "mark_sent"),  # còn bản nháp ⇒ chưa thể đánh dấu đã nộp
        (["approve"], "approve"),
        (["discard"], "approve"),
        (["discard"], "discard"),
        (["discard"], "mark_sent"),
        (["approve", "mark_sent"], "approve"),
        (["approve", "mark_sent"], "discard"),
        (["approve", "mark_sent"], "mark_sent"),
    ],
)
async def test_every_invalid_pair_is_a_409_and_changes_nothing(
    world: SimpleNamespace, setup: list[str], action: str
) -> None:
    for step in setup:
        assert (await act(world.mine, step)).status_code == 200
    before = await state_of(world.mine)
    assert (await act(world.mine, action)).status_code == 409
    assert await state_of(world.mine) == before


async def test_actions_never_touch_the_other_family(world: SimpleNamespace) -> None:
    await act(world.mine, "discard")
    assert await state_of(world.other) == ("case_open", "draft")


async def test_a_real_family_without_guardian_alerts_consent_gets_404_until_it_consents(
    world: SimpleNamespace,
) -> None:
    """Hồ sơ thuộc mục đích `guardian_alerts`: chưa/không còn đồng ý ⇒ 404 (hồ sơ demo hư cấu được miễn)."""
    from case_support import FAKE_HMAC as _  # noqa: F401
    from consent_support import SHA, purge_family
    from sqlalchemy import update

    from hoicon.db.models import Consent
    from hoicon.services import consent_gate

    real = await seed_case(with_run=False)
    try:
        async with get_sessionmaker().begin() as session:
            content = await case_file_service.build_content(session, real.incident)
            session.add(CaseFile(incident_id=real.incident, family_id=real.family, content=content, is_demo=False))
            await session.execute(update(Incident).where(Incident.id == real.incident).values(is_demo=False))
        token = issue_guardian_access_token(real.guardian, real.family)
        consent_gate.reset_cache()
        assert (await call("GET", url(real), token=token)).status_code == 404
        assert (await act(real, "approve", token=token)).status_code == 404
        async with get_sessionmaker().begin() as session:
            session.add(
                Consent(
                    family_id=real.family,
                    member_id=real.protected,
                    purpose="guardian_alerts",
                    granted=True,
                    consent_version="v1.0",
                    text_sha256=SHA,
                    channel="app",
                )
            )
        consent_gate.reset_cache()
        assert (await call("GET", url(real), token=token)).status_code == 200
    finally:
        consent_gate.reset_cache()
        await purge_family(real.family)


async def test_case_file_visibility_follows_the_incident_is_demo_flag_not_the_row_copy(
    world: SimpleNamespace,
) -> None:
    """011 T024 #7: nguồn sự thật cho "demo được miễn" là `incident.is_demo` (như mọi route khác), không phải bản
    sao ở dòng hồ sơ. Sự cố THẬT mà hồ sơ gắn nhãn demo nhầm không lọt qua cổng đồng ý; sự cố demo luôn đọc được."""
    from case_support import FAKE_HMAC as _  # noqa: F401
    from consent_support import purge_family
    from sqlalchemy import update

    from hoicon.services import consent_gate

    real = await seed_case(with_run=False)
    try:
        async with get_sessionmaker().begin() as session:
            content = await case_file_service.build_content(session, real.incident)
            session.add(CaseFile(incident_id=real.incident, family_id=real.family, content=content, is_demo=True))
            await session.execute(update(Incident).where(Incident.id == real.incident).values(is_demo=False))
        token = issue_guardian_access_token(real.guardian, real.family)
        consent_gate.reset_cache()
        # sự cố thật + hồ sơ nhãn demo nhầm + chưa đồng ý ⇒ 404
        assert (await call("GET", url(real), token=token)).status_code == 404
        async with get_sessionmaker().begin() as session:
            await session.execute(update(Incident).where(Incident.id == real.incident).values(is_demo=True))
            await session.execute(update(CaseFile).where(CaseFile.incident_id == real.incident).values(is_demo=False))
        # sự cố demo + hồ sơ nhãn thật ⇒ vẫn đọc được
        assert (await call("GET", url(real), token=token)).status_code == 200
    finally:
        consent_gate.reset_cache()
        await purge_family(real.family)
