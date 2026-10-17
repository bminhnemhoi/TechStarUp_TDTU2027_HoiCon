"""Generator SSE `stream_run`, bộ đếm chỗ và `TraceStreamResponse` (spec 025, FR-004/FR-005).

Không chạm DB: các hàm đọc của `trace_service` được thay bằng bản đọc từ `World` trong bộ nhớ, `sessions` là bản giả chỉ
đếm số session đang mở. Hằng số thời gian được thu nhỏ.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import TracebackType
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.exc import OperationalError
from starlette.requests import ClientDisconnect

from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep
from hoicon.services import trace_service
from hoicon.services.trace_service import (
    StreamLimitError,
    StreamSlot,
    TraceStreamResponse,
    acquire_slot,
    run_done_view,
    step_view,
    stream_run,
)

T0 = datetime(2026, 12, 1, 2, 0, 0, tzinfo=UTC)


class FakeSessions:
    """Thay `async_sessionmaker`: đếm session đang mở / đã mở."""

    def __init__(self) -> None:
        self.open = 0
        self.opened = 0

    def __call__(self) -> "FakeSessions":
        return self

    async def __aenter__(self) -> object:
        self.open += 1
        self.opened += 1
        return object()

    async def __aexit__(self, *exc: type[BaseException] | BaseException | TracebackType | None) -> None:
        self.open -= 1


class World:
    """Trạng thái DB giả: một lượt + các bước của nó."""

    def __init__(self, status: str = "running") -> None:
        self.run = AgentRun(
            id=new_id(),
            graph="incident",
            status=status,
            thread_id="t",
            cost_usd=Decimal("0.5"),
            is_drill=False,
            is_demo=False,
        )
        self.steps: list[AgentStep] = []
        self.loads = 0
        self.fail_loads: list[bool] = []  # kịch bản lỗi theo từng lần đọc trạng thái
        self.after_status_read: Callable[[], None] | None = None

    def add(self, node: str = "ingest", *, seconds: float | None = None) -> AgentStep:
        at = T0 + timedelta(seconds=len(self.steps) if seconds is None else seconds)
        step = AgentStep(
            id=new_id(), run_id=self.run.id, node=node, output={"n": len(self.steps)}, cost_usd=Decimal(0), at=at,
            latency_ms=1, tokens_in=0, tokens_out=0, fallback_used=False,
        )  # fmt: skip
        self.steps.append(step)
        return step

    async def load_run(self, _session: object, run_id: UUID) -> AgentRun | None:
        assert run_id == self.run.id
        self.loads += 1
        if self.fail_loads and self.fail_loads.pop(0):
            raise OperationalError("select", {}, Exception("db down"))
        snapshot = AgentRun(
            id=self.run.id, graph="incident", status=self.run.status, thread_id="t", cost_usd=self.run.cost_usd,
            is_drill=self.run.is_drill, is_demo=self.run.is_demo,
        )  # fmt: skip
        if self.after_status_read is not None:
            hook, self.after_status_read = self.after_status_read, None
            hook()
        return snapshot

    async def list_steps(
        self, _session: object, _run_id: UUID, after: tuple[datetime, UUID] | None = None, limit: int = 500
    ) -> list[AgentStep]:
        ordered = sorted(self.steps, key=lambda s: (s.at, s.id))
        return [s for s in ordered if after is None or (s.at, s.id) > after][:limit]

    async def find_step(self, _session: object, _run_id: UUID, step_id: UUID) -> AgentStep | None:
        return next((s for s in self.steps if s.id == step_id), None)

    async def count_steps(self, _session: object, _run_id: UUID) -> int:
        return len(self.steps)


@pytest.fixture
def fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trace_service, "POLL_S", 0.01)
    monkeypatch.setattr(trace_service, "PING_S", 0.05)
    monkeypatch.setattr(trace_service, "MAX_STREAM_S", 5.0)


def wire(monkeypatch: pytest.MonkeyPatch, world: World) -> FakeSessions:
    monkeypatch.setattr(trace_service, "_load_run", world.load_run)
    monkeypatch.setattr(trace_service, "list_steps", world.list_steps)
    monkeypatch.setattr(trace_service, "_find_step", world.find_step)
    monkeypatch.setattr(trace_service, "_count_steps", world.count_steps)
    return FakeSessions()


async def never() -> bool:
    return False


async def collect(gen: AsyncIterator[str], *, limit: float = 3.0) -> list[str]:
    frames: list[str] = []
    async with asyncio.timeout(limit):
        async for frame in gen:
            frames.append(frame)
    return frames


def step_ids(frames: list[str]) -> list[str]:
    return [line.removeprefix("id: ") for f in frames for line in f.splitlines() if line.startswith("id: ")]


def events(frames: list[str]) -> list[str]:
    return [line.removeprefix("event: ") for f in frames for line in f.splitlines() if line.startswith("event: ")]


def data_of(frame: str) -> dict[str, Any]:
    line = next(line for line in frame.splitlines() if line.startswith("data: "))
    return json.loads(line.removeprefix("data: "))


# --- khung & kết thúc -------------------------------------------------------------------------------------------


async def test_first_frame_is_the_retry_hint(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert frames[0] == "retry: 3000\n\n"


async def test_done_comes_once_after_the_last_step(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    added = [world.add("ingest"), world.add("risk_scorer"), world.add("resolve")]
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert events(frames) == ["step", "step", "step", "done"]
    assert step_ids(frames) == [str(s.id) for s in added]
    assert data_of(frames[-1]) == run_done_view(world.run, 3)
    assert data_of(frames[1]) == step_view(added[0])
    assert all(f.endswith("\n\n") for f in frames)


async def test_step_data_is_a_single_line_of_json(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    world.add("ingest")
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    step_frame = frames[1]
    assert step_frame.count("\n") == 4  # id, event, data, dòng trống (kết thúc khung)
    assert "\r" not in step_frame


async def test_a_failed_run_also_ends_with_done(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("failed")
    world.add("ingest")
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert data_of(frames[-1])["status"] == "failed" and events(frames).count("done") == 1


async def test_done_never_overtakes_the_last_step(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    """Trạng thái đọc TRƯỚC, bước đọc SAU: bước commit ngay sau câu đọc trạng thái vẫn ra trước `done`."""
    world = World("running")
    world.add("ingest")

    def finish_between_status_and_steps() -> None:
        world.add("resolve")
        world.run.status = "done"

    world.after_status_read = finish_between_status_and_steps
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert events(frames) == ["step", "step", "done"]
    assert data_of(frames[-1])["total_steps"] == 2


async def test_waiting_run_is_not_closed(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("waiting")
    world.add("await_guardian")
    sessions = wire(monkeypatch, world)
    gen = stream_run(sessions, world.run.id, None, never)
    frames: list[str] = []
    async with asyncio.timeout(3):
        async for frame in gen:
            frames.append(frame)
            if len(frames) >= 4:  # retry, step, rồi ít nhất hai khung `: ping`
                break
    await gen.aclose()
    assert "done" not in events(frames) and ": ping\n\n" in frames


async def test_stream_closes_after_max_stream_seconds_without_done(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    monkeypatch.setattr(trace_service, "MAX_STREAM_S", 0.15)
    world = World("waiting")
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert "done" not in events(frames) and "error" not in events(frames)


async def test_ping_is_sent_after_ping_interval_of_silence(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    monkeypatch.setattr(trace_service, "PING_S", 0.1)
    world = World("running")
    gen = stream_run(wire(monkeypatch, world), world.run.id, None, never)
    loop = asyncio.get_running_loop()
    first = await anext(gen)  # retry
    started = loop.time()
    async with asyncio.timeout(2):
        second = await anext(gen)
    await gen.aclose()
    assert first == "retry: 3000\n\n" and second == ": ping\n\n"
    assert 0.09 <= loop.time() - started < 0.5


# --- nối lại ------------------------------------------------------------------------------------------------------


async def test_unknown_last_event_id_replays_from_the_start(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    added = [world.add("ingest"), world.add("resolve")]
    sessions = wire(monkeypatch, world)
    for foreign in (str(new_id()), "không-phải-uuid", "", "x" * 500):
        frames = await collect(stream_run(sessions, world.run.id, foreign, never))
        assert step_ids(frames) == [str(s.id) for s in added], foreign


async def test_known_last_event_id_skips_what_the_client_has(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    added = [world.add("ingest"), world.add("risk_scorer"), world.add("resolve")]
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, str(added[1].id), never))
    assert step_ids(frames) == [str(added[2].id)] and events(frames)[-1] == "done"


async def test_steps_with_the_same_timestamp_are_not_lost(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    monkeypatch.setattr(trace_service, "PAGE", 1)  # mỗi nhịp một bước ⇒ con trỏ phải là (at, id), không chỉ `at`
    world = World("done")
    added = [world.add(seconds=0), world.add(seconds=0), world.add(seconds=0), world.add(seconds=1)]
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert sorted(step_ids(frames)) == sorted(str(s.id) for s in added) and len(step_ids(frames)) == 4


async def test_a_step_added_while_streaming_is_delivered(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("running")
    world.add("ingest")
    gen = stream_run(wire(monkeypatch, world), world.run.id, None, never)
    got: list[str] = []
    async with asyncio.timeout(3):
        async for frame in gen:
            got.append(frame)
            if len(got) == 2:  # đã nhận retry + bước đầu: chèn thêm bước rồi chốt lượt
                late = world.add("resolve")
                world.run.status = "done"
    assert step_ids(got) == [str(world.steps[0].id), str(late.id)] and events(got)[-1] == "done"


# --- lỗi DB & ngắt kết nối ----------------------------------------------------------------------------------------


async def test_three_consecutive_db_failures_send_error_then_close(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("running")
    world.fail_loads = [True, True, True, False]
    sessions = wire(monkeypatch, world)
    frames = await collect(stream_run(sessions, world.run.id, None, never))
    assert frames[-1] == 'event: error\ndata: {"retryable":true}\n\n'
    assert world.loads == 3 and sessions.open == 0


async def test_a_recovering_database_resets_the_failure_count(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    world.fail_loads = [True, True, False, True, True, False]
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    assert "error" not in events(frames) and events(frames)[-1] == "done"


async def test_db_failure_log_has_only_the_exception_class(
    monkeypatch: pytest.MonkeyPatch, fast: None, caplog: pytest.LogCaptureFixture
) -> None:
    world = World("running")
    world.fail_loads = [True, True, True]
    with caplog.at_level("DEBUG"):
        await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "OperationalError" in text and "db down" not in text


async def test_disconnect_ends_the_stream_within_a_poll(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("waiting")
    gone = False

    async def disconnected() -> bool:
        return gone

    gen = stream_run(wire(monkeypatch, world), world.run.id, None, disconnected)
    await anext(gen)
    gone = True
    async with asyncio.timeout(1):
        rest = [frame async for frame in gen]
    assert "done" not in events(rest)


async def test_aclose_midway_leaves_no_session_open(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("waiting")
    world.add("ingest")
    sessions = wire(monkeypatch, world)
    gen = stream_run(sessions, world.run.id, None, never)
    await anext(gen)
    await anext(gen)  # đang đứng ở `yield` của khung bước
    assert sessions.open == 0, "không được giữ session qua yield"
    await gen.aclose()
    assert sessions.open == 0 and sessions.opened >= 1


async def test_cancellation_is_not_swallowed(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("waiting")
    sessions = wire(monkeypatch, world)

    async def consume() -> None:
        async for _ in stream_run(sessions, world.run.id, None, never):
            pass

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert sessions.open == 0


async def test_a_vanished_run_ends_the_stream_quietly(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("running")

    async def gone(_session: object, _run_id: UUID) -> None:
        return None

    sessions = wire(monkeypatch, world)
    monkeypatch.setattr(trace_service, "_load_run", gone)
    frames = await collect(stream_run(sessions, world.run.id, None, never))
    assert events(frames) == []


# --- bộ đếm chỗ & response --------------------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_slots() -> None:
    trace_service._reset_slots()


def test_per_member_limit_then_global_limit() -> None:
    member = new_id()
    slots = [acquire_slot(member) for _ in range(trace_service.MAX_STREAMS_PER_MEMBER)]
    with pytest.raises(StreamLimitError) as per_member:
        acquire_slot(member)
    assert per_member.value.status_code == 429 and per_member.value.retry_after_s > 0
    for slot in slots:
        slot.release()
    others = [acquire_slot(new_id()) for _ in range(trace_service.MAX_STREAMS)]
    with pytest.raises(StreamLimitError) as overall:
        acquire_slot(new_id())
    assert overall.value.status_code == 503 and overall.value.retry_after_s == 5
    for slot in others:
        slot.release()
    assert trace_service.open_streams() == 0


def test_release_is_idempotent() -> None:
    member = new_id()
    slot = acquire_slot(member)
    slot.release()
    slot.release()
    assert trace_service.open_streams() == 0
    assert [acquire_slot(member) for _ in range(trace_service.MAX_STREAMS_PER_MEMBER)]


async def _run_response(
    response: TraceStreamResponse, send: Callable[[dict[str, Any]], Any], asgi_version: str = "2.4"
) -> None:
    async def receive() -> dict[str, Any]:
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}

    scope = {"type": "http", "asgi": {"spec_version": asgi_version}}
    await response(scope, receive, send)


async def test_response_closes_generator_and_frees_slot_when_the_client_vanishes() -> None:
    closed = asyncio.Event()

    async def body() -> AsyncIterator[str]:
        try:
            while True:
                yield ": ping\n\n"
                await asyncio.sleep(0)
        finally:
            closed.set()

    slot = acquire_slot(new_id())

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.body":
            raise OSError("client đã ngắt")  # Starlette 1.7 + ASGI ≥ 2.4: báo ngắt bằng lỗi khi ghi

    response = TraceStreamResponse(body(), slot, media_type="text/event-stream")
    with pytest.raises(ClientDisconnect):
        await _run_response(response, send)
    assert closed.is_set(), "generator phải được aclose() chắc chắn"
    assert trace_service.open_streams() == 0


async def test_response_frees_slot_when_the_stream_ends_normally() -> None:
    async def body() -> AsyncIterator[str]:
        yield "retry: 3000\n\n"

    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await _run_response(TraceStreamResponse(body(), acquire_slot(new_id())), send)
    assert trace_service.open_streams() == 0 and sent[0]["status"] == 200


async def test_response_frees_slot_on_the_older_asgi_path_too() -> None:
    async def body() -> AsyncIterator[str]:
        yield "retry: 3000\n\n"
        await asyncio.sleep(3600)

    async def send(message: dict[str, Any]) -> None:
        return None

    response = TraceStreamResponse(body(), acquire_slot(new_id()))

    async def receive() -> dict[str, Any]:
        await asyncio.sleep(0.05)
        return {"type": "http.disconnect"}

    async with asyncio.timeout(3):
        await response({"type": "http", "asgi": {"spec_version": "2.3"}}, receive, send)
    assert trace_service.open_streams() == 0


def test_stream_slot_type_is_exported() -> None:
    assert isinstance(acquire_slot(new_id()), StreamSlot)


# --- sau review độc lập lượt 1 (spec 025) -------------------------------------------------------------------------


def test_family_limit_caps_what_two_guardians_can_hold_together() -> None:
    family = new_id()
    held = [acquire_slot(new_id(), family) for _ in range(trace_service.MAX_STREAMS_PER_FAMILY)]
    with pytest.raises(StreamLimitError) as info:
        acquire_slot(new_id(), family)  # một người giám hộ KHÁC của cùng gia đình
    assert info.value.status_code == 429
    acquire_slot(new_id(), new_id()).release()  # gia đình khác vẫn còn chỗ
    for slot in held:
        slot.release()
    assert trace_service.open_streams() == 0
    assert acquire_slot(new_id(), family)  # nhả chỗ thì mở lại được


async def test_line_separator_characters_cannot_split_an_sse_frame(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    world.add("ingest").output = {"s": "a event: done b\x85c\r\nid: x"}
    frames = await collect(stream_run(wire(monkeypatch, world), world.run.id, None, never))
    step = frames[1]
    for sep in (" ", " ", "\x85", "\r"):
        assert sep not in step
    assert len(step.split("\n")) == 5  # id, event, data, "", "" ⇒ đúng một khung
    assert data_of(step)["output"]["s"].startswith("a")


async def test_an_unrenderable_step_ends_the_stream_with_error(monkeypatch: pytest.MonkeyPatch, fast: None) -> None:
    world = World("done")
    world.add("ingest")
    sessions = wire(monkeypatch, world)

    def boom(_step: object) -> dict[str, object]:
        raise ValueError("không dựng được")

    monkeypatch.setattr(trace_service, "step_view", boom)
    frames = await collect(stream_run(sessions, world.run.id, None, never))
    assert frames[-1] == 'event: error\ndata: {"retryable":false}\n\n' and "done" not in events(frames)
    assert sessions.open == 0


async def test_a_value_error_while_loading_rows_ends_the_stream_without_inviting_a_retry(
    monkeypatch: pytest.MonkeyPatch, fast: None
) -> None:
    world = World("running")
    sessions = wire(monkeypatch, world)

    async def broken(*_args: object, **_kwargs: object) -> list[AgentStep]:
        raise ValueError("Exceeds the limit (4300 digits) for integer string conversion")

    monkeypatch.setattr(trace_service, "list_steps", broken)
    frames = await collect(stream_run(sessions, world.run.id, None, never))
    assert (
        frames[-1] == 'event: error\ndata: {"retryable":false}\n\n' and sessions.open == 0
    )  # dữ liệu hỏng: thử lại vô ích


def test_limit_errors_say_which_limit_was_hit() -> None:
    member, family = new_id(), new_id()
    held = [acquire_slot(member, family) for _ in range(trace_service.MAX_STREAMS_PER_MEMBER)]
    with pytest.raises(StreamLimitError) as by_member:
        acquire_slot(member, family)
    other = acquire_slot(new_id(), family)  # chỗ thứ 4 của gia đình
    with pytest.raises(StreamLimitError) as by_family:
        acquire_slot(new_id(), family)
    assert (by_member.value.scope, by_family.value.scope) == ("member", "family")
    for slot in [*held, other]:
        slot.release()
