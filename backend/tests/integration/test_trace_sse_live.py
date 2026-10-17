"""Spec 025 (FR-005/FR-009): luồng SSE trên uvicorn THẬT (cổng ngẫu nhiên, task nền, client httpx/socket thô).

ASGITransport không dùng được cho luồng đang mở (nó gom hết thân phản hồi). Ở đây đo độ trễ SC-001, `: ping`, nối lại
bằng `Last-Event-ID` và kiểm 50 lần ngắt đột ngột không rò kết nối pool hay chỗ trong bộ đếm (SC-006). Số đo: máy dev,
localhost, không qua Caddy."""

import asyncio
import contextlib
import json
import statistics
import time
from collections.abc import AsyncIterator, Callable, Iterator
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx
import pytest
import uvicorn
from trace_support import another_incident, auth

from hoicon.api.main import app
from hoicon.db.models import AgentRun, AgentStep
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.services import trace_service

pytestmark = pytest.mark.integration


class QuietServer(uvicorn.Server):
    """uvicorn chạy như task nền trong test: không chiếm tín hiệu của pytest."""

    @contextlib.contextmanager
    def capture_signals(self) -> Iterator[None]:
        yield


@pytest.fixture
async def base_url() -> AsyncIterator[str]:
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="off")
    server = QuietServer(config)
    task = asyncio.create_task(server.serve())
    async with asyncio.timeout(10):
        while not server.started:  # noqa: ASYNC110 — cờ của uvicorn, không có sự kiện để chờ
            await asyncio.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    async with asyncio.timeout(10):
        await task


@pytest.fixture
def roomy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trace_service, "MAX_STREAMS_PER_MEMBER", 100)
    monkeypatch.setattr(trace_service, "MAX_STREAMS", 100)


async def new_running_run(world: dict[str, Any]) -> UUID:
    incident = await another_incident(world)
    async with get_sessionmaker().begin() as session:
        run = AgentRun(graph="incident", status="running", thread_id=str(incident), cost_usd=Decimal(0), is_demo=True)
        session.add(run)
    world["runs"].append(run.id)
    return run.id


async def add_step(run_id: UUID, node: str = "ingest") -> float:
    """Chèn một bước và commit; ⇒ thời điểm (monotonic) ngay sau commit."""
    async with get_sessionmaker().begin() as session:
        session.add(AgentStep(run_id=run_id, node=node, output={"n": 1}, latency_ms=1))
    return time.monotonic()


async def finish(run_id: UUID, status: str = "done") -> None:
    async with get_sessionmaker().begin() as session:
        run = await session.get(AgentRun, run_id)
        assert run is not None
        run.status = status


class Sse:
    """Đọc luồng httpx ⇒ khung đã ghép (dict) kèm thời điểm nhận."""

    def __init__(self, response: httpx.Response) -> None:
        self.frames: list[dict[str, Any]] = []
        self._lines = response.aiter_lines()

    async def next_frame(self, limit_s: float = 5.0) -> dict[str, Any]:
        fields: dict[str, str] = {}
        async with asyncio.timeout(limit_s):
            async for line in self._lines:
                if line == "":
                    if not fields:
                        continue
                    frame = {"at": time.monotonic(), **fields}
                    self.frames.append(frame)
                    return frame
                if line.startswith(":"):
                    fields["comment"] = line[1:].strip()
                    continue
                name, _, value = line.partition(": ")
                fields[name] = value
        raise AssertionError("luồng đóng trước khi có khung kế tiếp")

    async def until(self, predicate: Callable[[dict[str, Any]], bool], limit_s: float = 5.0) -> dict[str, Any]:
        async with asyncio.timeout(limit_s):
            while True:
                frame = await self.next_frame(limit_s)
                if predicate(frame):
                    return frame


def is_step(frame: dict[str, Any]) -> bool:
    return frame.get("event") == "step"


async def drained(limit_s: float = 4.0) -> bool:
    async with asyncio.timeout(limit_s + 1):
        while trace_service.open_streams() > 0:  # noqa: ASYNC110 — thăm dò bộ đếm trong bộ nhớ
            await asyncio.sleep(0.05)
    return True


# --- bước mới tới client, độ trễ (SC-001) ---------------------------------------------------------------------


async def test_new_steps_reach_the_client_and_measure_latency(trace_world: dict[str, Any], base_url: str) -> None:
    run_id = await new_running_run(trace_world)
    headers = {"Authorization": f"Bearer {auth(trace_world)}"}
    latencies: list[float] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60.0)) as client:  # noqa: SIM117 — hai ngữ cảnh độc lập về vòng đời
        async with client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["x-accel-buffering"] == "no" and "connection" not in response.headers
            sse = Sse(response)
            assert (await sse.next_frame())["retry"] == "3000"
            for i in range(30):
                await asyncio.sleep((i % 6) * 0.06)  # rải pha so với nhịp thăm dò 0,3 s
                committed = await add_step(run_id)
                frame = await sse.until(is_step)
                latencies.append(frame["at"] - committed)
                assert json.loads(frame["data"])["node"] == "ingest"
            await finish(run_id)
            done = await sse.until(lambda f: f.get("event") == "done")
            assert json.loads(done["data"])["total_steps"] == 30
    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(0.95 * len(latencies)) - 1]
    print(
        f"\nSC-001 n={len(latencies)} p50={p50 * 1000:.0f} ms p95={p95 * 1000:.0f} ms "
        f"max={max(latencies) * 1000:.0f} ms "
        "(uvicorn thật, localhost, POLL_S=0.3)"
    )
    assert p95 <= 1.0, "CI chỉ khẳng định ≤ 1 s; mục tiêu 0,5 s đo trên máy dev"


async def test_ping_is_sent_when_nothing_happens(
    trace_world: dict[str, Any], base_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(trace_service, "PING_S", 0.4)
    run_id = await new_running_run(trace_world)
    async with (
        httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60.0)) as client,
        client.stream(
            "GET", f"/v1/runs/{run_id}/stream", headers={"Authorization": f"Bearer {auth(trace_world)}"}
        ) as response,
    ):
        sse = Sse(response)
        await sse.next_frame()
        started = time.monotonic()
        ping = await sse.next_frame()
        assert ping.get("comment") == "ping" and "event" not in ping
        assert 0.35 <= ping["at"] - started < 1.5
        assert (await sse.next_frame())["comment"] == "ping"  # và tiếp tục đều đặn


# --- nối lại -------------------------------------------------------------------------------------------------------


async def test_reconnecting_with_last_event_id_does_not_repeat_steps(
    trace_world: dict[str, Any], base_url: str
) -> None:
    run_id = await new_running_run(trace_world)
    headers = {"Authorization": f"Bearer {auth(trace_world)}"}
    for node in ("ingest", "fast_alert", "risk_scorer"):
        await add_step(run_id, node)
    async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60.0)) as client:
        async with client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as response:
            sse = Sse(response)
            first = [await sse.until(is_step) for _ in range(3)]
        assert [json.loads(f["data"])["node"] for f in first] == ["ingest", "fast_alert", "risk_scorer"]
        for node in ("intervention", "resolve"):
            await add_step(run_id, node)
        await finish(run_id)
        async with client.stream(
            "GET", f"/v1/runs/{run_id}/stream", headers={**headers, "Last-Event-ID": first[-1]["id"]}
        ) as response:
            sse = Sse(response)
            await sse.until(lambda f: f.get("event") == "done")
    again = [json.loads(f["data"])["node"] for f in sse.frames if is_step(f)]
    assert again == ["intervention", "resolve"]
    assert {f["id"] for f in sse.frames if is_step(f)}.isdisjoint(f["id"] for f in first)


# --- ngắt đột ngột (SC-006) -----------------------------------------------------------------------------------


async def test_fifty_abrupt_disconnects_leak_neither_pool_connections_nor_slots(
    trace_world: dict[str, Any], base_url: str, roomy: None
) -> None:
    run_id = await new_running_run(trace_world)
    host, port = base_url.removeprefix("http://").split(":")
    request = (
        f"GET /v1/runs/{run_id}/stream HTTP/1.1\r\nHost: {host}\r\nAuthorization: Bearer {auth(trace_world)}\r\n"
        "Accept: text/event-stream\r\n\r\n"
    ).encode()
    pool = get_engine().pool
    baseline = pool.checkedout()
    assert trace_service.open_streams() == 0
    peak = 0
    for _ in range(50):
        reader, writer = await asyncio.open_connection(host, int(port))
        writer.write(request)
        await writer.drain()
        async with asyncio.timeout(5):
            await reader.readuntil(b"retry: 3000\n\n")  # luồng đã thật sự bắt đầu
        writer.transport.abort()  # RST, không FIN lịch sự
        peak = max(peak, pool.checkedout())
    assert await drained(), "bộ đếm chỗ phải về 0 sau khi mọi client biến mất"
    await asyncio.sleep(0.5)  # nhịp thăm dò cuối cùng (nếu có) đã trả kết nối
    assert pool.checkedout() == baseline, "không kết nối pool nào bị giữ"
    assert peak <= baseline + 5 + 10, "kể cả 50 luồng sống, pool không bị rút cạn"
    # sau đó API vẫn phục vụ bình thường
    async with httpx.AsyncClient(base_url=base_url) as client:
        res = await client.get(f"/v1/runs/{run_id}/steps", headers={"Authorization": f"Bearer {auth(trace_world)}"})
    assert res.status_code == 200


async def test_stream_opened_over_the_limit_is_refused_before_it_starts(
    trace_world: dict[str, Any], base_url: str
) -> None:
    run_id = await new_running_run(trace_world)
    headers = {"Authorization": f"Bearer {auth(trace_world)}"}
    async with httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(60.0)) as client:
        opened = []
        for _ in range(trace_service.MAX_STREAMS_PER_MEMBER):
            cm = client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers)
            response = await cm.__aenter__()
            assert response.status_code == 200
            opened.append(cm)
        async with client.stream("GET", f"/v1/runs/{run_id}/stream", headers=headers) as fourth:
            assert fourth.status_code == 429 and fourth.headers["retry-after"]
        for cm in opened:
            await cm.__aexit__(None, None, None)
    assert await drained()
