"""Spec 020 US2 (FR-005, SC-002): `POST /v1/consents` ghi thêm vào sổ đồng ý bất biến."""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from consent_support import call, item, pair_device
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import DBAPIError

from hoicon.api import auth
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Device
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


async def rows(family_id: Any) -> list[Consent]:
    async with get_sessionmaker()() as session:
        query = select(Consent).where(Consent.family_id == family_id).order_by(Consent.recorded_at, Consent.id)
        return list(await session.scalars(query))


async def test_without_a_token_is_401_and_nothing_is_written(device_world: Any) -> None:
    resp = await call("POST", "/v1/consents", json={"items": [item()]})
    assert resp.status_code == 401 and resp.headers["WWW-Authenticate"] == "Bearer"
    assert await rows(device_world.family_id) == []


@pytest.mark.parametrize("token", ["garbage", "a.b.c", ""])
async def test_bad_tokens_are_401(device_world: Any, token: str) -> None:
    assert (await call("POST", "/v1/consents", token=token, json={"items": [item()]})).status_code == 401


async def test_expired_and_foreign_tokens_are_401(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)
    claims = auth.decode_access_token(paired["access_token"])
    expired = auth.issue_access_token(
        claims.device_id, claims.family_id, claims.member_id, now=datetime.now(UTC) - timedelta(days=31)
    )
    assert (await call("POST", "/v1/consents", token=expired, json={"items": [item()]})).status_code == 401
    other_family = auth.issue_access_token(claims.device_id, new_id(), claims.member_id)  # chữ ký đúng, gia đình sai
    assert (await call("POST", "/v1/consents", token=other_family, json={"items": [item()]})).status_code == 401
    assert await rows(device_world.family_id) == []


async def test_revoked_device_is_401(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)
    async with get_sessionmaker().begin() as session:
        await session.execute(
            update(Device).where(Device.family_id == device_world.family_id).values(revoked_at=func.now())
        )
    assert (
        await call("POST", "/v1/consents", token=paired["access_token"], json={"items": [item()]})
    ).status_code == 401


async def test_valid_batch_is_recorded_with_server_side_family_member_and_time(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)
    batch = json.loads((SCHEMAS / "fixtures" / "consent_record.v1.valid.json").read_text(encoding="utf-8"))[0]
    resp = await call("POST", "/v1/consents", token=paired["access_token"], json={"items": batch["items"]})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "recorded" and data["count"] == 2 and data["recorded_at"]
    saved = await rows(device_world.family_id)
    assert {c.purpose for c in saved} == {"core_protection", "call_screening"}
    assert {str(c.family_id) for c in saved} == {paired["family_id"]}
    assert {str(c.member_id) for c in saved} == {paired["member_id"]}
    assert all(c.granted and c.channel == "app" and c.recorded_at is not None for c in saved)
    assert len({c.recorded_at for c in saved}) == 1  # cả lô cùng một giao dịch


async def test_withdrawal_appends_a_new_row_and_never_touches_the_old_one(device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    assert (
        await call("POST", "/v1/consents", token=token, json={"items": [item("voice_input", True)]})
    ).status_code == 200
    assert (
        await call("POST", "/v1/consents", token=token, json={"items": [item("voice_input", False)]})
    ).status_code == 200
    saved = await rows(device_world.family_id)
    assert [c.granted for c in saved] == [True, False]


async def test_the_ledger_is_immutable_even_for_the_application_connection(device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    await call("POST", "/v1/consents", token=token, json={"items": [item()]})
    for statement in ("update consents set granted = false", "delete from consents"):
        with pytest.raises(DBAPIError, match="append-only"):
            async with get_sessionmaker().begin() as session:
                await session.execute(text(f"{statement} where family_id = :f"), {"f": device_world.family_id})
    assert [c.granted for c in await rows(device_world.family_id)] == [True]


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
async def test_there_is_no_http_way_to_change_or_remove_a_consent(device_world: Any, method: str) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    resp = await call(method, "/v1/consents", token=token, json={"items": [item()]})
    assert resp.status_code == 405


@pytest.mark.parametrize(
    "doc",
    json.loads((SCHEMAS / "fixtures" / "consent_record.v1.invalid.json").read_text(encoding="utf-8")),
    ids=lambda d: d["_why"],
)
async def test_invalid_contract_fixtures_are_422_and_write_nothing(doc: dict[str, Any], device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    resp = await call("POST", "/v1/consents", token=token, json={k: v for k, v in doc.items() if k != "_why"})
    assert resp.status_code == 422
    assert await rows(device_world.family_id) == []


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"items": [item(channel="zalo")]}, id="thiết bị không được tự nhận kênh khác app"),
        pytest.param({"items": [item(channel="sms")]}, id="kênh lạ"),
        pytest.param({"items": [item(), item()]}, id="trùng purpose trong một lô"),
        pytest.param({"items": [item(), item("call_screening", extra="x")]}, id="trường thừa"),
        pytest.param({"items": [item(consent_version="v" * 17)]}, id="phiên bản quá dài"),
        pytest.param({"items": [item(text_sha256="AB" * 32)]}, id="hex chữ hoa"),
        pytest.param({"items": [item(text_sha256=("ab" * 32) + "\n")]}, id="hex kèm xuống dòng"),
        pytest.param({"items": [item(granted="yes")]}, id="granted không phải bool"),
        pytest.param({"items": [item(), item("call_screening")] * 17}, id="quá 32 mục"),
        pytest.param({"items": [item()], "extra": 1}, id="trường thừa ở gốc"),
        pytest.param([item()], id="không phải object"),
    ],
)
async def test_bad_batches_are_422_and_atomic(device_world: Any, payload: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    resp = await call("POST", "/v1/consents", token=token, json=payload)
    assert resp.status_code == 422
    assert await rows(device_world.family_id) == []


async def test_a_batch_with_one_bad_item_writes_none(device_world: Any) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    resp = await call("POST", "/v1/consents", token=token, json={"items": [item("core_protection"), item("sell_data")]})
    assert resp.status_code == 422
    assert await rows(device_world.family_id) == []


async def test_missing_signing_key_is_503(device_world: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "")
    get_settings.cache_clear()
    assert (await call("POST", "/v1/consents", token=token, json={"items": [item()]})).status_code == 503


async def test_hashes_are_not_echoed_into_logs(device_world: Any, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    token = (await pair_device(device_world.code, consent=False))["access_token"]
    await call("POST", "/v1/consents", token=token, json={"items": [item()]})
    assert token not in caplog.text
