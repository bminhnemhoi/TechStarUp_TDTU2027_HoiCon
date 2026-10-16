"""Spec 029 FR-002/FR-003 (T003/T004): `POST /v1/heartbeat`.

Thân đúng ⇒ 200 và `devices` đổi; gửi lặp trong khung ⇒ 1 dòng; trường lạ ⇒ 422 (không lặp lại giá trị); thiết bị bị
thu hồi ⇒ 401; chưa/rút đồng ý ⇒ 403 `consent_withdrawn`; lần thứ 9 trong giờ ⇒ 429; DB không lưu gì ngoài hợp đồng."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, item, pair_device
from sqlalchemy import func, select, text, update

from hoicon.api.routers import devices as devices_router
from hoicon.db.models import Device, DeviceHeartbeat
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate, heartbeat_service
from hoicon.services import retention_service as rs

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "fixtures" / "heartbeat.v1.valid.json"
CORE_ON = {"call_screening_role": True, "usage_access": True, "notifications": False}


def body(**changes: Any) -> dict[str, Any]:
    base = {"app_version": "0.3.0", "rules_version": "r1", "permission_state": CORE_ON}
    return {**base, **changes}


@pytest.fixture
async def paired(device_world: Any) -> AsyncGenerator[dict[str, Any]]:
    devices_router.reset_limits()
    consent_gate.reset_cache()
    result = await pair_device(device_world.code)
    me = (await call("GET", "/v1/devices/me", token=result["access_token"])).json()["device"]
    yield {"token": result["access_token"], "device_id": UUID(me["device_id"]), "member_id": UUID(me["member_id"])}
    devices_router.reset_limits()
    consent_gate.reset_cache()


async def heartbeats(device_id: UUID) -> list[DeviceHeartbeat]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(DeviceHeartbeat).where(DeviceHeartbeat.device_id == device_id)))


async def test_a_valid_body_returns_200_and_updates_the_device(paired: dict[str, Any]) -> None:
    async with get_sessionmaker().begin() as session:  # đẩy mốc cũ về quá khứ để thấy nó đổi
        await session.execute(
            update(Device)
            .where(Device.id == paired["device_id"])
            .values(last_heartbeat_at=datetime(2026, 1, 1, tzinfo=UTC))
        )
    sent = body(app_version="0.3.1", rules_version="r2", threat_list_version="0123456789abcdef")
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=sent)
    assert resp.status_code == 200 and resp.json() == {"status": "ok"}
    async with get_sessionmaker()() as session:
        device = await session.get(Device, paired["device_id"])
    assert (device.app_version, device.rules_version, device.threat_list_version) == ("0.3.1", "r2", "0123456789abcdef")
    assert device.permission_state == CORE_ON
    assert device.last_heartbeat_at > datetime.now(UTC) - timedelta(minutes=1)
    (row,) = await heartbeats(paired["device_id"])
    assert row.slot == heartbeat_service.slot_of(datetime.now(UTC)) and row.protected is True


async def test_the_contract_fixture_is_accepted_as_is(paired: dict[str, Any]) -> None:
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=json.loads(FIXTURE.read_text("utf-8")))
    assert resp.status_code == 200
    (row,) = await heartbeats(paired["device_id"])
    assert row.protected is True  # fixture: pin không giới hạn tắt nhưng cả hai quyền lõi bật


async def test_protected_needs_every_core_permission(paired: dict[str, Any]) -> None:
    sent = body(permission_state={"call_screening_role": True, "usage_access": False})
    assert (await call("POST", "/v1/heartbeat", token=paired["token"], json=sent)).status_code == 200
    (row,) = await heartbeats(paired["device_id"])
    assert row.protected is False


async def test_a_repeat_in_the_same_slot_keeps_one_row_but_refreshes_the_device(paired: dict[str, Any]) -> None:
    first = await call("POST", "/v1/heartbeat", token=paired["token"], json=body())
    second = await call("POST", "/v1/heartbeat", token=paired["token"], json=body(app_version="0.3.9"))
    assert first.status_code == second.status_code == 200
    assert len(await heartbeats(paired["device_id"])) == 1
    async with get_sessionmaker()() as session:
        assert (await session.get(Device, paired["device_id"])).app_version == "0.3.9"


async def test_the_slot_is_a_quarter_hour_mark_in_utc() -> None:
    assert heartbeat_service.slot_of(datetime(2026, 12, 1, 3, 29, 59, tzinfo=UTC)) == datetime(
        2026, 12, 1, 3, 15, tzinfo=UTC
    )
    assert heartbeat_service.slot_of(datetime(2026, 12, 1, 3, 30, tzinfo=UTC)) == datetime(
        2026, 12, 1, 3, 30, tzinfo=UTC
    )


@pytest.mark.parametrize(
    "extra",
    [{"label": "may cua ba"}, {"phone": "0900000111"}, {"note": "ghi-chu-rieng-tu"}],
)
async def test_an_unknown_field_is_422_and_the_value_is_not_echoed(
    paired: dict[str, Any], extra: dict[str, Any]
) -> None:
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json={**body(), **extra})
    assert resp.status_code == 422
    for value in extra.values():
        assert value not in resp.text
    assert await heartbeats(paired["device_id"]) == []


@pytest.mark.parametrize(
    "changes",
    [
        {"permission_state": {"usage_access": "yes"}},
        {"permission_state": {"Usage Access": True}},
        {"permission_state": {f"p{i}".replace("1", "a").replace("2", "b"): True for i in range(30)}},
        {"app_version": "0900000123456"},
        {"threat_list_version": "v1"},
        {"app_version": None},
    ],
)
async def test_a_body_outside_the_contract_is_422(paired: dict[str, Any], changes: dict[str, Any]) -> None:
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=body(**changes))
    assert resp.status_code == 422
    assert await heartbeats(paired["device_id"]) == []


async def test_no_token_or_a_revoked_device_is_401(paired: dict[str, Any]) -> None:
    assert (await call("POST", "/v1/heartbeat", json=body())).status_code == 401
    async with get_sessionmaker().begin() as session:
        await session.execute(update(Device).where(Device.id == paired["device_id"]).values(revoked_at=func.now()))
    assert (await call("POST", "/v1/heartbeat", token=paired["token"], json=body())).status_code == 401
    assert await heartbeats(paired["device_id"]) == []


async def test_withdrawing_core_protection_is_403_and_nothing_is_written(paired: dict[str, Any]) -> None:
    withdrawn = await call(
        "POST", "/v1/consents", token=paired["token"], json={"items": [item("core_protection", granted=False)]}
    )
    assert withdrawn.status_code == 200
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=body())
    assert resp.status_code == 403 and resp.json() == {"detail": "consent_withdrawn"}
    assert await heartbeats(paired["device_id"]) == []
    again = await call("POST", "/v1/consents", token=paired["token"], json={"items": [item("core_protection")]})
    assert again.status_code == 200
    assert (await call("POST", "/v1/heartbeat", token=paired["token"], json=body())).status_code == 200


async def test_a_device_that_never_consented_is_403(device_world: Any) -> None:
    devices_router.reset_limits()
    consent_gate.reset_cache()
    result = await pair_device(device_world.code, consent=False)
    resp = await call("POST", "/v1/heartbeat", token=result["access_token"], json=body())
    assert resp.status_code == 403 and resp.json() == {"detail": "consent_withdrawn"}


async def test_the_ninth_heartbeat_in_an_hour_is_429(paired: dict[str, Any]) -> None:
    for _ in range(8):
        assert (await call("POST", "/v1/heartbeat", token=paired["token"], json=body())).status_code == 200
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=body())
    assert resp.status_code == 429 and int(resp.headers["Retry-After"]) >= 1
    assert devices_router._limit.retry_after(paired["device_id"], now=10**9) is None  # cửa sổ trượt mở lại sau 1 giờ


async def test_the_database_keeps_nothing_outside_the_contract(paired: dict[str, Any]) -> None:
    resp = await call("POST", "/v1/heartbeat", token=paired["token"], json=body())
    assert resp.status_code == 200
    async with get_sessionmaker()() as session:
        device = await session.get(Device, paired["device_id"])
        dumped = json.dumps(
            {
                "permission_state": device.permission_state,
                "versions": [device.app_version, device.rules_version, device.threat_list_version],
            }
        )
        cols = (
            (
                await session.execute(
                    text("select column_name from information_schema.columns where table_name = 'device_heartbeats'")
                )
            )
            .scalars()
            .all()
        )
    assert set(json.loads(dumped)["permission_state"]) <= {"call_screening_role", "usage_access", "notifications"}
    assert set(cols) == {"device_id", "slot", "protected"}  # không IP, không tên máy, không văn bản
    (row,) = await heartbeats(paired["device_id"])
    assert set(vars(row)) - {"_sa_instance_state"} == {"device_id", "slot", "protected"}


async def test_retention_deletes_heartbeats_older_than_90_days(paired: dict[str, Any]) -> None:
    now = datetime(2027, 3, 1, 3, 0, tzinfo=UTC)  # đúng mốc 15 phút
    assert rs.RETENTION["device_heartbeats"] == timedelta(days=90)  # FR-002: giữ 90 ngày
    cutoff = now - rs.RETENTION["device_heartbeats"]
    old, young = cutoff - timedelta(minutes=15), cutoff
    async with get_sessionmaker().begin() as session:
        session.add_all(
            [
                DeviceHeartbeat(device_id=paired["device_id"], slot=old, protected=True),
                DeviceHeartbeat(device_id=paired["device_id"], slot=young, protected=True),
            ]
        )
    dry = await rs.purge_device_heartbeats(get_sessionmaker(), now=now, dry_run=True)
    assert dry >= 1 and len(await heartbeats(paired["device_id"])) == 2
    assert await rs.purge_device_heartbeats(get_sessionmaker(), now=now) >= 1
    assert [h.slot for h in await heartbeats(paired["device_id"])] == [young]
    assert await rs.purge_device_heartbeats(get_sessionmaker(), now=now) == 0  # lũy đẳng


async def test_the_service_itself_refuses_a_revoked_device(paired: dict[str, Any]) -> None:
    """Rào cuối nếu thu hồi xảy ra giữa lúc xác thực và lúc ghi: không đổi `devices`, không ghi khung."""
    async with get_sessionmaker().begin() as session:
        await session.execute(update(Device).where(Device.id == paired["device_id"]).values(revoked_at=func.now()))
    async with get_sessionmaker().begin() as session:
        alive = await heartbeat_service.record(
            session,
            paired["device_id"],
            app_version="9.9.9",
            rules_version="r9",
            threat_list_version=None,
            permission_state=CORE_ON,
            now=datetime.now(UTC),
        )
    assert alive is False and await heartbeats(paired["device_id"]) == []
    async with get_sessionmaker()() as session:
        assert (await session.get(Device, paired["device_id"])).app_version == "0.2.0"
