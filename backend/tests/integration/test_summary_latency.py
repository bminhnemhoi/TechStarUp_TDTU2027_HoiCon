"""Spec 024 T024 (SC-001): độ trễ từ lúc nhận sự kiện tới lúc tin tóm tắt (`detail`) gọi client Zalo.

Đo qua đồ thị THẬT (`IncidentRuntime`) trên Postgres thật, LLM giả trả tức thì (tương đương replay) và client Zalo MOCK
có dấu thời gian: đây là số đo "máy dev, Zalo mock", KHÔNG phải độ trễ thật với LLM/Zalo thật. Không gồm nhịp thăm dò
của worker (≤ 0.5 s) vì job được xử lý trực tiếp; nhịp đó cộng thêm tối đa 0.5 s mỗi tin."""

import dataclasses
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import select
from test_graph_verification import Client, deps, event

from hoicon.agents.runtime import IncidentRuntime
from hoicon.channels.guardian import send_to_guardian
from hoicon.channels.zalo import MockZaloClient
from hoicon.db.models import Job

pytestmark = pytest.mark.integration

RUNS = 20
SC_001_P95_S = 15.0


@dataclass
class StampedMock(MockZaloClient):
    stamps: list[float] = field(default_factory=list)

    async def send_message(self, chat_id: str, text: str) -> Any:
        sent = await super().send_message(chat_id, text)
        self.stamps.append(time.monotonic())
        return sent


async def notify_payloads(sessions: Any, incident: str) -> dict[str, dict[str, Any]]:
    async with sessions() as session:
        rows = await session.scalars(
            select(Job).where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{incident}:msg:"))
        )
        return {j.payload["template"]: j.payload for j in rows}


async def test_summary_latency_from_the_event_to_the_zalo_call_stays_under_sc_001(
    zalo_world: Any, threads: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    world = zalo_world
    await world.add_guardian(1)
    client = StampedMock()
    settings = world.settings.model_copy(update={"zalo_monthly_quota": 10_000})
    channel = dataclasses.replace(world.deps, client=client, settings=settings)
    latencies: list[float] = []
    async with IncidentRuntime.open(deps(Client(level="high"))) as runtime:
        for _ in range(RUNS):
            incident = world.new_incident()
            threads.append(incident)
            received = time.monotonic()  # lúc máy chủ nhận lô sự kiện
            await runtime.start(
                event(), incident_id=incident, elder_alias="Mẹ", is_demo=True, family_id=str(world.family.id)
            )
            payloads = await notify_payloads(channel.sessions, incident)
            assert "detail" in payloads, "đồ thị phải xếp tin tóm tắt"
            before = len(client.stamps)
            assert await send_to_guardian(channel, payloads["detail"]) == "sent"
            assert len(client.stamps) == before + 1
            latencies.append(client.stamps[-1] - received)
            await runtime.graph.checkpointer.adelete_thread(incident)
    ordered = sorted(latencies)
    p50, p95 = statistics.median(ordered), ordered[int(0.95 * (RUNS - 1) + 0.999)]
    with capsys.disabled():
        print(
            f"\nSC-001 summary_latency (máy dev, Zalo mock, LLM giả): n={RUNS} "
            f"p50={p50:.3f}s p95={p95:.3f}s max={ordered[-1]:.3f}s"
        )
    assert len(latencies) == RUNS and all(x > 0 for x in latencies)
    assert p95 <= SC_001_P95_S
