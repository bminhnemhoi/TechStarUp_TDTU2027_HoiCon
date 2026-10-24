"""Spec 033 T023 (plan D9): thiết bị `sim:` của lượt đã kết thúc > 24 giờ bị dọn trong `retention`; sự cố giữ nguyên."""

import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from consent_support import purge_family

from hoicon.db.models import Device, Family, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services import retention_service as rs

pytestmark = pytest.mark.integration

NOW = datetime(2027, 3, 1, 12, 0, tzinfo=UTC)
H = timedelta(hours=1)


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-033-sim-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        ids = {"family": family.id, "member": member.id}
    yield ids
    await purge_family(ids["family"])


async def add_device(world: dict[str, UUID], label: str | None, age: timedelta, *, closed_ago: timedelta | None = None,
                     open_incident: bool = False) -> tuple[UUID, UUID | None]:  # fmt: skip
    """Thiết bị tạo cách đây `age`; tùy chọn có một sự cố đã đóng cách đây `closed_ago` hoặc còn mở."""
    async with get_sessionmaker().begin() as session:
        device = Device(
            family_id=world["family"], member_id=world["member"], platform="web", label=label, app_version="sim-1",
            rules_version="sim-1", device_secret_hash=secrets.token_hex(32), created_at=NOW - age,
        )  # fmt: skip
        session.add(device)
        await session.flush()
        incident_id: UUID | None = None
        if closed_ago is not None or open_incident:
            values: dict[str, Any] = {
                "family_id": world["family"], "member_id": world["member"], "device_id": device.id,
                "state": "case_open" if open_incident else "resolved_safe", "level": "high", "rule_floor": "high",
                "is_demo": True, "outcome": None if open_incident else "safe",
                "closed_at": None if open_incident else NOW - (closed_ago or H),
            }  # fmt: skip
            incident = Incident(**values)
            session.add(incident)
            await session.flush()
            incident_id = incident.id
        return device.id, incident_id


async def alive(model: Any, key: UUID | None) -> bool:
    async with get_sessionmaker()() as session:
        return key is not None and await session.get(model, key) is not None


async def sweep(*, dry_run: bool = False) -> int:
    return await rs.purge_sim_devices(get_sessionmaker(), now=NOW, dry_run=dry_run)


async def test_a_sim_device_is_kept_at_23_hours_and_removed_at_25_hours_but_the_incident_stays(
    world: dict[str, UUID],
) -> None:
    young, young_incident = await add_device(world, "sim:fake_police_001", 40 * H, closed_ago=23 * H)
    old, old_incident = await add_device(world, "sim:fake_police_002", 40 * H, closed_ago=25 * H)
    assert await sweep() >= 1
    assert await alive(Device, young) and not await alive(Device, old)
    assert await alive(Incident, young_incident) and await alive(Incident, old_incident)  # hạn lưu sự cố giữ nguyên
    async with get_sessionmaker()() as session:
        kept = await session.get(Incident, old_incident)
        assert kept is not None and kept.device_id is None


def test_the_label_prefix_matches_the_one_the_sim_service_writes() -> None:
    from hoicon.services import sim_service

    assert rs.SIM_LABEL_PREFIX == sim_service.SIM_LABEL_PREFIX


async def test_a_device_without_the_sim_label_is_never_touched(world: dict[str, UUID]) -> None:
    real, _ = await add_device(world, None, 500 * H, closed_ago=400 * H)
    named, _ = await add_device(world, "may-cua-me", 500 * H)
    lookalike, _ = await add_device(world, "xsim:fake_001", 500 * H)
    await sweep()
    assert await alive(Device, real) and await alive(Device, named) and await alive(Device, lookalike)


async def test_a_sim_device_with_a_still_open_incident_is_kept(world: dict[str, UUID]) -> None:
    device, _ = await add_device(world, "sim:fake_police_003", 100 * H, open_incident=True)
    await sweep()
    assert await alive(Device, device)


async def test_a_sim_device_with_no_incident_follows_its_own_age(world: dict[str, UUID]) -> None:
    """Kịch bản hợp lệ không mở sự cố: tuổi thiết bị quyết định."""
    young, _ = await add_device(world, "sim:benign_official_005", 23 * H)
    old, _ = await add_device(world, "sim:benign_official_006", 25 * H)
    await sweep()
    assert await alive(Device, young) and not await alive(Device, old)


async def test_dry_run_counts_without_deleting_and_run_retention_reports_it(world: dict[str, UUID]) -> None:
    old, _ = await add_device(world, "sim:fake_police_004", 48 * H)
    assert await sweep(dry_run=True) >= 1
    assert await alive(Device, old)

    async def noop(_: str) -> None:
        return None

    report = await rs.run_retention(get_sessionmaker(), noop, now=NOW)
    assert report["sim_devices"] >= 1 and not await alive(Device, old)
