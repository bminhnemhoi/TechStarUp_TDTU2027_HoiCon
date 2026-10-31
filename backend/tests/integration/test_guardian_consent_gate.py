# ruff: noqa: F811
"""Spec 011 FR-006 (T021, D9): người cao tuổi rút `guardian_alerts` ⇒ web của người giám hộ không còn đọc được sự cố
của họ (danh sách rỗng, chi tiết/lượt chạy/luồng ⇒ cùng 404). Dữ liệu demo hư cấu được miễn."""

from datetime import timedelta
from typing import Any

import pytest
from consent_support import SHA, call
from test_guardian_incidents import BASE, add_run, bearer, worlds  # noqa: F401 (worlds là fixture)

from hoicon.db.models import Consent, Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    consent_gate.reset_cache()


async def record(w: dict[str, Any], granted: bool, purpose: str = "guardian_alerts") -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=w["family"],
                member_id=w["protected"],
                purpose=purpose,
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()


async def add_incident(w: dict[str, Any], state: str, opened_at: Any, *, is_demo: bool) -> Any:
    async with get_sessionmaker().begin() as session:
        incident = Incident(
            family_id=w["family"],
            member_id=w["protected"],
            state=state,
            level="high",
            rule_floor="high",
            is_demo=is_demo,
            opened_at=opened_at,
        )
        session.add(incident)
        await session.flush()
        w["incidents"].append(incident.id)
        return incident.id


async def real_incident(w: dict[str, Any]) -> tuple[Any, Any]:
    incident = await add_incident(w, "awaiting_guardian", BASE + timedelta(minutes=1), is_demo=False)
    return incident, await add_run(incident)


async def ids_in_list(w: dict[str, Any]) -> list[str]:
    resp = await call("GET", "/v1/guardian/incidents", token=bearer(w))
    assert resp.status_code == 200, resp.text
    return [i["id"] for i in resp.json()["incidents"]]


async def test_a_real_incident_is_hidden_until_the_elder_has_consented(worlds: Any) -> None:
    a, _ = worlds
    incident, run = await real_incident(a)
    assert await ids_in_list(a) == []
    for path in (f"/v1/guardian/incidents/{incident}", f"/v1/incidents/{incident}/run", f"/v1/runs/{run}/steps"):
        assert (await call("GET", path, token=bearer(a))).status_code == 404, path


async def test_granting_makes_it_visible_and_withdrawing_hides_it_again(worlds: Any) -> None:
    a, _ = worlds
    incident, run = await real_incident(a)
    await record(a, True)
    assert await ids_in_list(a) == [str(incident)]
    for path in (f"/v1/guardian/incidents/{incident}", f"/v1/incidents/{incident}/run", f"/v1/runs/{run}/steps"):
        assert (await call("GET", path, token=bearer(a))).status_code == 200, path
    await record(a, False)
    assert await ids_in_list(a) == []
    for path in (f"/v1/guardian/incidents/{incident}", f"/v1/incidents/{incident}/run", f"/v1/runs/{run}/steps"):
        assert (await call("GET", path, token=bearer(a))).status_code == 404, path
    assert (await call("GET", f"/v1/runs/{run}/stream", token=bearer(a))).status_code == 404


async def test_another_purpose_does_not_stand_in_for_guardian_alerts(worlds: Any) -> None:
    a, _ = worlds
    await real_incident(a)
    await record(a, True, "core_protection")
    assert await ids_in_list(a) == []


async def test_demo_incidents_are_exempt(worlds: Any) -> None:
    a, _ = worlds
    demo = await add_incident(a, "awaiting_guardian", BASE + timedelta(minutes=2), is_demo=True)
    assert await ids_in_list(a) == [str(demo)]
    assert (await call("GET", f"/v1/guardian/incidents/{demo}", token=bearer(a))).status_code == 200
