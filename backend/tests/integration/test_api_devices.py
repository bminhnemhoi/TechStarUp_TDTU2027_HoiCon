"""Spec 020 (FR-004, T010): `GET /v1/devices/me` — thông tin thiết bị + trạng thái đồng ý hiện tại."""

import json
from pathlib import Path
from typing import Any

import pytest
from consent_support import call, item, pair_device
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, update

from hoicon.db.models import Device
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def validate(doc: Any) -> list[str]:
    schema = json.loads((SCHEMAS / "device_me.v1.json").read_text(encoding="utf-8"))
    return [e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(doc)]


async def test_requires_a_device_token(device_world: Any) -> None:
    assert (await call("GET", "/v1/devices/me")).status_code == 401
    assert (await call("GET", "/v1/devices/me", token="nope")).status_code == 401


async def test_fresh_device_has_no_consents_and_matches_the_contract(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False, device_label="Máy của mẹ")
    resp = await call("GET", "/v1/devices/me", token=paired["access_token"])
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert validate(data) == []
    assert data["consents"] == []
    device = data["device"]
    assert device["device_id"] == paired["device_id"] and device["family_name"] == device_world.display_name
    assert (device["platform"], device["label"], device["app_version"]) == ("android", "Máy của mẹ", "0.2.0")
    assert device["rules_version"] == "r1" and device["threat_list_version"] is None


async def test_response_never_leaks_secrets(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)
    text = (await call("GET", "/v1/devices/me", token=paired["access_token"])).text
    for leaked in (paired["refresh_token"], paired["access_token"], "device_secret_hash", "fcm_token"):
        assert leaked not in text


async def test_consents_show_only_the_latest_row_per_purpose(device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    await call("POST", "/v1/consents", token=token, json={"items": [item("voice_input", True), item("drills", True)]})
    await call(
        "POST", "/v1/consents", token=token, json={"items": [item("voice_input", False, consent_version="v1.1")]}
    )
    data = (await call("GET", "/v1/devices/me", token=token)).json()
    assert validate(data) == []
    state = {c["purpose"]: c for c in data["consents"]}
    assert set(state) == {"voice_input", "drills"}
    assert state["voice_input"]["granted"] is False and state["voice_input"]["consent_version"] == "v1.1"
    assert state["drills"]["granted"] is True


async def test_another_familys_consents_are_not_visible(device_world: Any) -> None:
    from consent_support import purge_family

    from hoicon.db.models import Family

    token = (await pair_device(device_world.code, consent=False))["access_token"]
    await call("POST", "/v1/consents", token=token, json={"items": [item("drills", True)]})
    async with get_sessionmaker().begin() as session:
        other = Family(display_name=f"{device_world.display_name}-b", region="bac", is_demo=True)
        session.add(other)
        await session.flush()
        other_id = other.id
    try:
        other_code = await _code_for(other_id)
        other_token = (await pair_device(other_code, consent=False))["access_token"]
        data = (await call("GET", "/v1/devices/me", token=other_token)).json()
        assert data["consents"] == [] and data["device"]["family_id"] == str(other_id)
    finally:
        await purge_family(other_id)


async def _code_for(family_id: Any) -> str:
    from hoicon.ops.pairing_code import create_pairing_code

    return await create_pairing_code(get_sessionmaker(), family_id)


async def test_revoked_device_loses_access_immediately(device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    assert (await call("GET", "/v1/devices/me", token=token)).status_code == 200
    async with get_sessionmaker().begin() as session:
        await session.execute(
            update(Device).where(Device.family_id == device_world.family_id).values(revoked_at=func.now())
        )
    assert (await call("GET", "/v1/devices/me", token=token)).status_code == 401
