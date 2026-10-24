"""Spec 024 T023 (FR-005): câu trả lời E8 làm nâng mức ⇒ ghi ngược `incidents.level` (chỉ nâng, không hạ — luật 5).

Dùng lại dựng sẵn của `test_graph_verification` (gia đình/sự cố hư cấu, LLM giả)."""

import pytest
from test_graph_verification import Client, World, incident_row, running, start, steps, world  # noqa: F401

pytestmark = pytest.mark.integration


async def test_elder_answer_that_raises_the_level_is_written_back_to_the_incident(world: World) -> None:  # noqa: F811
    async with running(world, Client(ask="q_asked_transfer")) as (runtime, thread):
        status = await start(runtime, world, thread)
        assert status.waiting_for == "ask_elder"
        assert (await incident_row(world.incident)).level == "high"
        status = await runtime.resume(
            thread, {"answer": "yes"}, expect="ask_elder"
        )  # "đang bị bảo chuyển tiền" ⇒ critical
        assert status.level == "critical"
    row = await incident_row(world.incident)
    assert (row.level, row.rule_floor) == ("critical", "high")  # mức sàn không đổi, chỉ mức hiện hành nâng
    assert await steps(str(world.incident), "risk_scorer")  # vẫn có vết ở trace


async def test_elder_answer_that_does_not_raise_keeps_the_incident_level(world: World) -> None:  # noqa: F811
    async with running(world, Client(ask="q_asked_transfer")) as (runtime, thread):
        await start(runtime, world, thread)
        version = (await incident_row(world.incident)).version
        await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
    row = await incident_row(world.incident)
    assert (row.level, row.version) == ("high", version)  # không nâng ⇒ không đổi gì, không tăng version


async def test_elder_answer_never_lowers_the_incident_level(world: World) -> None:  # noqa: F811
    async with running(world, Client(level="low", ask="q_asked_transfer")) as (runtime, thread):
        await start(runtime, world, thread)
        await runtime.resume(thread, {"answer": "unsure"}, expect="ask_elder")
    assert (await incident_row(world.incident)).level == "high"  # LLM nói low cũng không hạ dưới mức hiện có
