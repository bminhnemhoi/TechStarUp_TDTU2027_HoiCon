"""Spec 050 FR-005b / SC-004: `ops booth reset` xóa mọi lượt mô phỏng của gia đình demo và KHÔNG đụng gì khác."""

import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from consent_support import purge_family
from sqlalchemy import func, select

from hoicon.db.models import AgentRun, Device, Family, Incident, Job, Member
from hoicon.db.session import get_sessionmaker
from hoicon.ops import booth

pytestmark = pytest.mark.integration


async def make_family(*, demo: bool, sim_incidents: int, closed: int = 0, plain_incidents: int = 0) -> dict[str, Any]:
    """Gia đình có `sim_incidents` lượt mô phỏng (thiết bị `sim:`, `closed` lượt đã đóng)
    và `plain_incidents` sự cố thường."""
    sim_ids: list[UUID] = []
    plain_ids: list[UUID] = []
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-050-{secrets.token_hex(3)}", region="nam", is_demo=demo)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add(member)
        await session.flush()

        async def add(label: str | None, state: str) -> UUID:
            device = Device(
                family_id=family.id,
                member_id=member.id,
                label=label,
                app_version="t",
                rules_version="t",
                device_secret_hash=secrets.token_hex(32),
            )
            session.add(device)
            await session.flush()
            incident = Incident(
                family_id=family.id,
                member_id=member.id,
                device_id=device.id,
                state=state,
                level="high",
                rule_floor="high",
                is_demo=True,
                closed_at=datetime.now(UTC) if state == "resolved_safe" else None,
            )
            session.add(incident)
            await session.flush()
            session.add(
                AgentRun(
                    incident_id=incident.id, graph="incident", status="done", thread_id=str(incident.id), is_demo=True
                )
            )
            session.add(
                Job(kind="notify_guardian", payload={"sim": True}, idempotency_key=f"{incident.id}:msg:fast_alert")
            )
            return incident.id

        for n in range(sim_incidents):
            sim_ids.append(await add(f"sim:scenario_{n}", "resolved_safe" if n < closed else "detected"))
        for _ in range(plain_incidents):
            plain_ids.append(await add(None, "detected"))
    return {"family": family.id, "sim": sim_ids, "plain": plain_ids}


@pytest.fixture
async def families(require_db: None) -> AsyncGenerator[list[dict[str, Any]]]:
    made: list[dict[str, Any]] = []
    yield made
    for world in made:
        async with get_sessionmaker().begin() as session:
            for incident in [*world["sim"], *world["plain"]]:
                await session.execute(AgentRun.__table__.delete().where(AgentRun.thread_id == str(incident)))
        await purge_family(world["family"])


async def count(model: Any, *where: Any) -> int:
    async with get_sessionmaker()() as session:
        return int(await session.scalar(select(func.count()).select_from(model).where(*where)) or 0)


async def test_reset_removes_demo_sim_runs_and_leaves_everything_else(families: list[dict[str, Any]]) -> None:
    demo = await make_family(demo=True, sim_incidents=3, closed=1, plain_incidents=2)
    real = await make_family(demo=False, sim_incidents=2)  # nhãn `sim:` nhưng KHÔNG phải gia đình demo
    families.extend([demo, real])
    done = await booth.reset_sim(get_sessionmaker())
    assert done["incidents"] >= 3 and done["devices"] >= 3
    assert await count(Incident, Incident.id.in_(demo["sim"])) == 0
    assert await count(AgentRun, AgentRun.thread_id.in_([str(i) for i in demo["sim"]])) == 0
    assert await count(Job, *[Job.idempotency_key.startswith(f"{i}:") for i in demo["sim"]][:1]) == 0
    assert await count(Device, Device.family_id == demo["family"], Device.label.startswith("sim:")) == 0
    # không đụng: sự cố demo thường và mọi thứ của gia đình thật
    assert await count(Incident, Incident.id.in_(demo["plain"])) == 2
    assert await count(Incident, Incident.id.in_(real["sim"])) == 2
    assert await count(Family, Family.id.in_([demo["family"], real["family"]])) == 2


async def test_a_real_incident_on_a_device_with_a_sim_label_is_kept_with_its_device(
    families: list[dict[str, Any]],
) -> None:
    """Nhãn thiết bị là chuỗi tự do: sự cố không phải mô phỏng (`is_demo` false) và thiết bị của nó được giữ."""
    demo = await make_family(demo=True, sim_incidents=1)
    families.append(demo)
    async with get_sessionmaker().begin() as session:
        await session.execute(Incident.__table__.update().where(Incident.id.in_(demo["sim"])).values(is_demo=False))
    await booth.reset_sim(get_sessionmaker())
    assert await count(Incident, Incident.id.in_(demo["sim"])) == 1
    assert await count(Device, Device.family_id == demo["family"], Device.label.startswith("sim:")) == 1


async def test_reset_twice_removes_nothing_the_second_time_of_this_family(families: list[dict[str, Any]]) -> None:
    demo = await make_family(demo=True, sim_incidents=2)
    families.append(demo)
    await booth.reset_sim(get_sessionmaker())
    again = await booth.reset_sim(get_sessionmaker())
    assert await count(Incident, Incident.id.in_(demo["sim"])) == 0
    assert again["incidents"] == 0 and again["devices"] == 0


async def test_reset_of_twenty_runs_takes_well_under_thirty_seconds(families: list[dict[str, Any]]) -> None:
    demo = await make_family(demo=True, sim_incidents=20, closed=5)
    families.append(demo)
    done = await booth.reset_sim(get_sessionmaker())
    assert done["incidents"] >= 20
    assert done["seconds"] < 30
    print(f"BOOTH-RESET 20 lượt: {done}")


def test_the_command_refuses_to_run_without_the_explicit_flag() -> None:
    with pytest.raises(SystemExit):
        booth.build_parser().parse_args(["reset"])
    assert booth.build_parser().parse_args(["reset", "--confirm-demo"]).command == "reset"
