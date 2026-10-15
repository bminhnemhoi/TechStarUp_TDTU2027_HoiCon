"""`spike demo --family`: tìm gia đình dev và in độ trễ tin gửi (nguồn số đo SC-001 khi có token)."""

from typing import Any

import pytest

from hoicon.agents import texts
from hoicon.agents.spike import family_id_by_name, report_messages
from hoicon.channels.guardian import send_to_guardian
from hoicon.jobs.queue import enqueue

pytestmark = pytest.mark.integration


async def test_family_is_found_by_name_and_unknown_name_explains_how_to_create_it(zalo_world: Any) -> None:
    world = zalo_world
    assert await family_id_by_name(world.deps.sessions, world.family.display_name) == str(world.family.id)
    with pytest.raises(SystemExit, match="pairing_code --family"):
        await family_id_by_name(world.deps.sessions, "khong-co-gia-dinh-nay-xyz")


async def test_report_prints_status_and_latency_per_message(
    zalo_world: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    world = zalo_world
    await world.add_guardian(1)
    incident = world.new_incident()
    payload = {
        "incident_id": incident,
        "family_id": str(world.family.id),
        "template": "fast_alert",
        "text": texts.guardian_fast_alert("Mẹ", "002", "bank", False),
        "guardian_rank": 1,
        "is_drill": False,
        "is_demo": True,
    }
    await enqueue(world.deps.sessions, "notify_guardian", payload, key=f"{incident}:msg:fast_alert")
    await send_to_guardian(world.deps, payload)
    await report_messages(world.deps.sessions, incident)
    out = capsys.readouterr().out
    assert "tin gửi người giám hộ (1)" in out and "fast_alert" in out and "sent" in out and " ms" in out
    assert "chat-of" not in out and world.zalo_ids[1][1] not in out  # không in định danh
