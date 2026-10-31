"""Spec 037 FR-003: sau khi người cao tuổi rút `guardian_alerts`, liên kết hành động đã gửi từ trước không còn cho
đọc dữ liệu sự cố (cùng 404 như liên kết không tồn tại); người giám hộ vẫn ghi được quyết định để đóng sự cố
(đường an toàn). Dữ liệu demo được miễn."""

from collections.abc import AsyncGenerator
from types import SimpleNamespace

import pytest
from case_support import seed_case
from consent_support import SHA, call, purge_family
from sqlalchemy import update

from hoicon.db.models import Consent, Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate
from hoicon.services.action_token_service import ActionTokenService

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    consent_gate.reset_cache()


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[SimpleNamespace]:
    w = await seed_case(state="awaiting_guardian", with_run=False, flagged=False, answers=())
    async with get_sessionmaker().begin() as session:  # sự cố THẬT: không demo
        await session.execute(update(Incident).where(Incident.id == w.incident).values(is_demo=False))
    yield w
    await purge_family(w.family)


async def token_for(w: SimpleNamespace) -> str:
    async with get_sessionmaker().begin() as session:
        _, raw = await ActionTokenService.create_token(session, incident_id=w.incident, member_id=w.guardian)
    return raw


async def consent(w: SimpleNamespace, granted: bool) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=w.family,
                member_id=w.protected,
                purpose="guardian_alerts",
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()


async def test_a_link_sent_while_consented_stops_showing_data_after_withdrawal(world: SimpleNamespace) -> None:
    raw = await token_for(world)
    await consent(world, True)
    shown = await call("GET", f"/v1/action/{raw}")
    assert shown.status_code == 200 and shown.json()["incident"]["id"] == str(world.incident)
    await consent(world, False)
    hidden = await call("GET", f"/v1/action/{raw}")
    unknown = await call("GET", "/v1/action/" + "x" * 43)
    assert hidden.status_code == unknown.status_code == 404
    assert hidden.json() == unknown.json()  # không phân biệt "đã rút" với "không có"
    assert str(world.incident) not in hidden.text


async def test_the_link_of_a_never_consented_real_incident_shows_nothing(world: SimpleNamespace) -> None:
    raw = await token_for(world)
    assert (await call("GET", f"/v1/action/{raw}")).status_code == 404


async def test_the_guardian_can_still_record_a_decision_after_withdrawal(world: SimpleNamespace) -> None:
    raw = await token_for(world)
    await consent(world, True)
    await consent(world, False)
    decided = await call("POST", f"/v1/action/{raw}/decision", json={"decision": "safe"})
    assert decided.status_code == 200 and decided.json()["incident_id"] == str(world.incident)  # đường an toàn còn mở


async def test_demo_links_are_exempt(world: SimpleNamespace) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(update(Incident).where(Incident.id == world.incident).values(is_demo=True))
    raw = await token_for(world)
    assert (await call("GET", f"/v1/action/{raw}")).status_code == 200
