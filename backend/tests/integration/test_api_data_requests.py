"""Spec 038 FR-004 (T002): `POST /v1/data-requests` — người được bảo vệ xóa dữ liệu gia đình từ app.

Chỉ thiết bị `protected`; lũy đẳng; 3/ngày/thiết bị; được phép cả khi đã rút đồng ý (không qua `consent_gate`); tin báo
người giám hộ CHỈ khi còn `guardian_alerts` và xếp TRƯỚC `purge_family`. Mọi định danh hư cấu."""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, call, pair_device
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import select

from hoicon.agents.texts import AI_DISCLOSURE
from hoicon.api.routers import data_requests as data_requests_router
from hoicon.db.models import Consent, DataRequest, Job, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate, purge_service

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _receipt_validator() -> Draft202012Validator:
    docs = [json.loads(p.read_text("utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    return Draft202012Validator(
        {"$ref": "https://hoicon.vn/schemas/data_request.v1.json#/$defs/receipt"},
        registry=registry,
        format_checker=FormatChecker(),
    )


RECEIPT = _receipt_validator()
BODY = {"kind": "delete", "confirmed": True}


@dataclass
class World:
    family_id: UUID
    member_id: UUID
    token: str
    guardian_id: UUID


@pytest.fixture
async def world(device_world: Any) -> AsyncGenerator[World]:
    data_requests_router.reset_limits()
    paired = await pair_device(device_world.code)  # ghi core_protection + guardian_alerts
    me = (await call("GET", "/v1/devices/me", token=paired["access_token"])).json()["device"]
    family_id = UUID(me["family_id"])
    async with get_sessionmaker().begin() as session:
        guardian = Member(family_id=family_id, role="guardian", guardian_rank=1, alias="Con")
        session.add(guardian)
        await session.flush()
        guardian_id = guardian.id
    consent_gate.reset_cache()
    yield World(family_id, UUID(me["member_id"]), paired["access_token"], guardian_id)
    data_requests_router.reset_limits()
    consent_gate.reset_cache()


async def post(w: World, body: Any = BODY, token: str | None = None) -> Any:
    return await call("POST", "/v1/data-requests", token=token or w.token, json=body)


async def requests_of(w: World) -> list[DataRequest]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(DataRequest).where(DataRequest.family_id == w.family_id)))


async def jobs_of(kind: str, w: World) -> list[Job]:
    async with get_sessionmaker()() as session:
        rows = await session.scalars(select(Job).where(Job.kind == kind))
        return [j for j in rows if j.payload.get("family_id") == str(w.family_id)]


async def withdraw(w: World, purpose: str) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=w.family_id,
                member_id=w.member_id,
                purpose=purpose,
                granted=False,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.invalidate(w.member_id)


async def test_a_protected_device_records_a_delete_request_and_queues_the_purge(world: World) -> None:
    res = await post(world)
    assert res.status_code == 202, res.text
    body = res.json()
    assert list(RECEIPT.iter_errors(body)) == [] and body["status"] == "pending" and body["deadline_hours"] == 72
    (row,) = await requests_of(world)
    assert (row.kind, row.requested_via, row.status) == ("delete", "app", "pending") and str(row.id) == body[
        "request_id"
    ]
    (purge,) = await jobs_of("purge_family", world)
    assert purge.payload["request_id"] == body["request_id"]
    assert res.headers["cache-control"] == "no-store"


async def test_a_second_request_returns_the_pending_one_with_200(world: World) -> None:
    first = (await post(world)).json()
    again = await post(world)
    assert again.status_code == 200 and again.json()["request_id"] == first["request_id"]
    assert len(await requests_of(world)) == 1 and len(await jobs_of("purge_family", world)) == 1


async def test_at_most_three_requests_a_day_per_device(world: World) -> None:
    assert [(await post(world)).status_code for _ in range(3)] == [202, 200, 200]
    blocked = await post(world)
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) >= 1


async def test_it_needs_a_device_token_and_only_a_protected_member_may_ask(world: World) -> None:
    assert (await call("POST", "/v1/data-requests", json=BODY)).status_code == 401
    assert (await post(world, token="khong-phai-jwt")).status_code == 401
    from hoicon.api.auth import issue_access_token

    async with get_sessionmaker()() as session:
        guardian = await session.get(Member, world.guardian_id)
        assert guardian is not None
    device_of_guardian = issue_access_token(world.guardian_id, world.family_id, UUID(int=1))
    assert (await post(world, token=device_of_guardian)).status_code == 401  # thiết bị không tồn tại
    assert await requests_of(world) == []


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"kind": "delete"},
        {"kind": "delete", "confirmed": False},
        {"kind": "export", "confirmed": True},
        {**BODY, "reason": "văn bản tự do"},
    ],
)
async def test_a_bad_body_is_422_and_records_nothing(world: World, body: dict[str, Any]) -> None:
    assert (await post(world, body)).status_code == 422
    assert await requests_of(world) == []


async def test_the_guardian_is_told_before_the_purge_while_guardian_alerts_is_on(world: World) -> None:
    await post(world)
    (notice,) = await jobs_of("notify_guardian", world)
    (purge,) = await jobs_of("purge_family", world)
    p = notice.payload
    assert p["text"].startswith(AI_DISCLOSURE) and p["guardian_rank"] == 1
    assert p["protected_member_id"] == str(world.member_id)  # đồng ý được kiểm lại LÚC GỬI (037 FR-002)
    assert p["job_key"] and p["template"] == "data_delete_notice" and p["is_demo"] is True
    assert notice.run_at < purge.run_at  # tin đi ngay lúc yêu cầu, purge sau khoảng chờ
    assert "72 giờ" in p["text"] and "hoảng" not in p["text"].lower()
    assert "Hủy" in p["text"] and " ngày " in p["text"]  # ghi giờ xóa và cách hủy (FR-006)


async def test_after_withdrawing_guardian_alerts_the_request_is_allowed_but_nobody_is_told(world: World) -> None:
    await withdraw(world, "guardian_alerts")
    res = await post(world)
    assert res.status_code == 202
    assert await jobs_of("notify_guardian", world) == []
    assert len(await jobs_of("purge_family", world)) == 1


async def test_it_works_after_withdrawing_core_protection_too(world: World) -> None:
    await withdraw(world, "core_protection")
    assert (await post(world)).status_code == 202  # quyền xóa không phụ thuộc đồng ý


async def test_after_the_purge_the_old_token_is_refused(world: World) -> None:
    assert (await post(world)).status_code == 202

    async def no_thread(_: str) -> None:
        return None

    await purge_service.purge_family(get_sessionmaker(), no_thread, world.family_id)
    assert (await call("GET", "/v1/devices/me", token=world.token)).status_code == 401
    assert (await post(world)).status_code == 401


async def test_two_simultaneous_requests_make_one_request_one_purge_and_one_notice(world: World) -> None:
    """Rà soát lượt 10 Medium #1: bấm đúp/thử lại chập chờn không được sinh hai yêu cầu, hai purge, hai tin."""
    import asyncio

    results = await asyncio.gather(*[post(world) for _ in range(3)])
    assert sorted(r.status_code for r in results) == [200, 200, 202]
    assert len({r.json()["request_id"] for r in results}) == 1
    assert len(await requests_of(world)) == 1
    assert len(await jobs_of("purge_family", world)) == 1 and len(await jobs_of("notify_guardian", world)) == 1


# --- T007 (FR-006): khoảng chờ 24 giờ có thể hủy ---------------------------------------------------


async def delete(w: World, request_id: Any, token: str | None = None) -> Any:
    return await call("DELETE", f"/v1/data-requests/{request_id}", token=token or w.token)


async def set_request(request_id: Any, **values: Any) -> None:
    from sqlalchemy import update

    async with get_sessionmaker().begin() as session:
        await session.execute(update(DataRequest).where(DataRequest.id == UUID(str(request_id))).values(**values))


async def test_the_receipt_carries_execute_after_24_hours_ahead_and_the_purge_waits_for_it(world: World) -> None:
    from datetime import datetime, timedelta

    body = (await post(world)).json()
    assert list(RECEIPT.iter_errors(body)) == []
    asked, due = datetime.fromisoformat(body["requested_at"]), datetime.fromisoformat(body["execute_after"])
    assert timedelta(hours=23, minutes=59) < due - asked < timedelta(hours=24, minutes=1)
    (row,) = await requests_of(world)
    assert row.execute_after == due
    (purge,) = await jobs_of("purge_family", world)
    assert abs((purge.run_at - due).total_seconds()) < 5  # job purge chạy đúng lúc hết khoảng chờ
    (notice,) = await jobs_of("notify_guardian", world)
    assert (purge.run_at - notice.run_at) > timedelta(hours=23)  # tin báo đi ngay, không chờ


async def test_cancelling_inside_the_waiting_period_keeps_everything_and_drops_the_purge_job(world: World) -> None:
    created = (await post(world)).json()
    res = await delete(world, created["request_id"])
    assert res.status_code == 200, res.text
    body = res.json()
    assert list(RECEIPT.iter_errors(body)) == [] and body["status"] == "cancelled"
    assert body["request_id"] == created["request_id"]
    assert await jobs_of("purge_family", world) == []  # job purge bị bỏ
    (row,) = await requests_of(world)
    assert row.status == "cancelled" and row.completed_at is None

    async def no_thread(_: str) -> None:
        return None

    # dù job nào đó vẫn chạy được purge_family, yêu cầu đã hủy thì KHÔNG xóa gì
    report = await purge_service.purge_family(get_sessionmaker(), no_thread, world.family_id, request_id=row.id)
    assert report == {"cancelled": 1}
    assert (await call("GET", "/v1/devices/me", token=world.token)).status_code == 200  # thiết bị còn sống
    assert (await requests_of(world))[0].status == "cancelled"


async def test_cancel_is_idempotent_and_a_new_request_can_follow(world: World) -> None:
    first = (await post(world)).json()
    assert (await delete(world, first["request_id"])).status_code == 200
    again = await delete(world, first["request_id"])
    assert again.status_code == 200 and again.json()["status"] == "cancelled"
    second = await post(world)
    assert second.status_code == 202 and second.json()["request_id"] != first["request_id"]  # yêu cầu mới sau khi hủy


async def test_cancel_is_refused_after_the_waiting_period_and_after_done(world: World) -> None:
    from datetime import UTC, datetime, timedelta

    created = (await post(world)).json()
    await set_request(created["request_id"], execute_after=datetime.now(UTC) - timedelta(seconds=1))
    assert (await delete(world, created["request_id"])).status_code == 409  # quá giờ: không hủy được nữa
    assert (await requests_of(world))[0].status == "pending"
    await set_request(created["request_id"], status="done", completed_at=datetime.now(UTC))
    assert (await delete(world, created["request_id"])).status_code == 409


async def test_cancel_needs_a_device_and_only_touches_the_own_familys_request(world: World) -> None:
    from hoicon.db.models import Family

    created = (await post(world)).json()
    assert (await call("DELETE", f"/v1/data-requests/{created['request_id']}")).status_code == 401
    assert (await delete(world, created["request_id"], token="khong-phai-jwt")).status_code == 401
    async with get_sessionmaker().begin() as session:
        other = Family(display_name="test-038-other", region="nam", is_demo=True)
        session.add(other)
        await session.flush()
        other_id = other.id
    try:
        theirs, _ = await purge_service.request_delete_detailed(get_sessionmaker(), other_id, "app")
        denied = await delete(world, theirs.id)
        unknown = await delete(world, UUID(int=7))
        assert denied.status_code == 404 and unknown.status_code == 404 and denied.json() == unknown.json()
        async with get_sessionmaker()() as session:
            assert (await session.get(DataRequest, theirs.id)).status == "pending"  # type: ignore[union-attr]
        assert (await delete(world, "khong-phai-uuid")).status_code == 422
    finally:
        from consent_support import purge_family

        await purge_family(other_id)


async def test_the_purge_runs_once_the_waiting_period_is_over(world: World) -> None:
    from datetime import UTC, datetime, timedelta

    created = (await post(world)).json()
    await set_request(created["request_id"], execute_after=datetime.now(UTC) - timedelta(seconds=1))

    async def no_thread(_: str) -> None:
        return None

    report = await purge_service.purge_family(
        get_sessionmaker(), no_thread, world.family_id, request_id=UUID(created["request_id"])
    )
    assert report["devices_revoked"] >= 1
    assert (await requests_of(world))[0].status == "done"
