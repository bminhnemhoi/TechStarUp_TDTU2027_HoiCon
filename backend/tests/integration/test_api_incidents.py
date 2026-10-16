"""Spec 021 (FR-007): `GET /v1/incidents/{id}`, `GET /v1/families/{id}/incidents` — chỉ trong gia đình của token."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, pair_device, purge_family
from drill_support import running_drill_for
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from test_api_events import harmless, make_event, post

from hoicon.db.ids import new_id
from hoicon.db.models import Family
from hoicon.db.session import get_sessionmaker
from hoicon.ops.pairing_code import create_pairing_code
from hoicon.services.incident_service import IncidentService

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
BASE = "https://hoicon.vn/schemas/"
REGISTRY = Registry().with_resources(
    (doc["$id"], Resource.from_contents(doc))
    for doc in (json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.v1.json"))
)


def errors(ref: str, doc: Any) -> list[str]:
    validator = Draft202012Validator({"$ref": BASE + ref}, registry=REGISTRY, format_checker=FormatChecker())
    return [e.message for e in validator.iter_errors(doc)]


@pytest.fixture
async def token(device_world: Any) -> str:
    return (await pair_device(device_world.code))["access_token"]


async def open_incident(token: str, **changes: Any) -> str:
    body = (await post(token, make_event(**changes))).json()
    assert body["incident_opened"] is True, body
    return body["incident_id"]


async def test_both_endpoints_require_a_device_token(device_world: Any) -> None:
    assert (await call("GET", f"/v1/incidents/{new_id()}")).status_code == 401
    assert (await call("GET", f"/v1/families/{device_world.family_id}/incidents")).status_code == 401
    assert (await call("GET", f"/v1/incidents/{new_id()}", token="nope")).status_code == 401


async def test_incident_detail_matches_the_contract(device_world: Any, token: str) -> None:
    incident_id = await open_incident(token)
    resp = await call("GET", f"/v1/incidents/{incident_id}", token=token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert errors("incident.v1.json", body) == []
    assert (body["id"], body["state"], body["level"], body["rule_floor"], body["version"]) == (
        incident_id,
        "detected",
        "high",
        "high",
        1,
    )
    assert body["family_id"] == str(device_world.family_id) and body["is_drill"] is False
    assert [(t["from_state"], t["to_state"], t["actor"]) for t in body["transitions"]] == [(None, "detected", "device")]


async def test_detail_follows_the_state_machine(device_world: Any, token: str) -> None:
    incident_id = UUID(await open_incident(token))
    async with get_sessionmaker().begin() as session:
        await IncidentService.transition(session, incident_id, "assessing", "agent", "test", expected_version=1)
        await IncidentService.transition(session, incident_id, "resolved_safe", "guardian", None, expected_version=2)
    body = (await call("GET", f"/v1/incidents/{incident_id}", token=token)).json()
    assert errors("incident.v1.json", body) == []
    assert (body["state"], body["version"], body["outcome"]) == ("resolved_safe", 3, "safe") and body["closed_at"]
    assert [t["to_state"] for t in body["transitions"]] == ["detected", "assessing", "resolved_safe"]


async def test_unknown_or_malformed_id(device_world: Any, token: str) -> None:
    assert (await call("GET", f"/v1/incidents/{new_id()}", token=token)).status_code == 404
    resp = await call("GET", "/v1/incidents/0900000001", token=token)
    assert resp.status_code == 422 and "0900000001" not in resp.text


async def test_another_familys_incident_looks_like_it_does_not_exist(device_world: Any, token: str) -> None:
    async with get_sessionmaker().begin() as session:
        other = Family(display_name=f"{device_world.display_name}-b", region="bac", is_demo=True)
        session.add(other)
        await session.flush()
        other_id = other.id
    try:
        other_token = (await pair_device(await create_pairing_code(get_sessionmaker(), other_id)))["access_token"]
        theirs = await open_incident(other_token)
        mine = await open_incident(token)
        assert (
            await call("GET", f"/v1/incidents/{theirs}", token=token)
        ).status_code == 404  # không phải 403: không lộ sự tồn tại
        assert (await call("GET", f"/v1/families/{other_id}/incidents", token=token)).status_code == 404
        listing = (await call("GET", f"/v1/families/{device_world.family_id}/incidents", token=token)).json()
        assert [i["id"] for i in listing["incidents"]] == [mine]
    finally:
        await purge_family(other_id)


async def test_family_list_is_newest_first_limited_and_matches_the_contract(device_world: Any, token: str) -> None:
    first = await open_incident(token)
    drill = str(await running_drill_for(token))  # spec 028 D2: bài `in_progress` hợp lệ thì cờ diễn tập mới được tin
    second = await open_incident(token, is_drill=True, drill_id=drill)  # diễn tập là sự cố riêng, gắn cờ is_drill
    resp = await call("GET", f"/v1/families/{device_world.family_id}/incidents", token=token)
    assert resp.status_code == 200
    body = resp.json()
    assert errors("incident.v1.json#/$defs/list", body) == []
    assert [i["id"] for i in body["incidents"]] == [second, first]
    assert [i["is_drill"] for i in body["incidents"]] == [True, False]
    assert all("transitions" not in i for i in body["incidents"])  # danh sách là bản tóm tắt
    limited = (await call("GET", f"/v1/families/{device_world.family_id}/incidents?limit=1", token=token)).json()
    assert [i["id"] for i in limited["incidents"]] == [second]


async def test_limit_is_bounded(device_world: Any, token: str) -> None:
    base = f"/v1/families/{device_world.family_id}/incidents"
    for bad in ("0", "101", "-1", "abc"):
        assert (await call("GET", f"{base}?limit={bad}", token=token)).status_code == 422, bad
    assert (await call("GET", f"{base}?limit=100", token=token)).status_code == 200


async def test_empty_family_has_an_empty_list(device_world: Any, token: str) -> None:
    await post(token, harmless())  # sự kiện vô hại không mở sự cố
    body = (await call("GET", f"/v1/families/{device_world.family_id}/incidents", token=token)).json()
    assert body == {"incidents": []} and errors("incident.v1.json#/$defs/list", body) == []


async def test_responses_never_carry_phone_data(device_world: Any, token: str) -> None:
    incident_id = await open_incident(token)
    text = (await call("GET", f"/v1/incidents/{incident_id}", token=token)).text
    text += (await call("GET", f"/v1/families/{device_world.family_id}/incidents", token=token)).text
    for leaked in ("caller", "h1", "hmac", "last3", "phone", "3f1c9a5e"):
        assert leaked not in text, leaked
