"""Truy vết tác tử cho người giám hộ (spec 025): bước đã che, lịch sử và luồng SSE.

Chỉ ĐỌC `agent_runs`/`agent_steps`. Hai lớp che độc lập (ADR-006): danh sách trắng cột trong `step_view` (không có
`input_redacted`) và `redact_json` cho `output`. `/steps` và SSE dùng chung `step_view`/`run_done_view` ⇒ cùng một bản.

Luồng SSE thăm dò DB mỗi `POLL_S` (đủ cho ≤ 20 luồng, không cần LISTEN/NOTIFY). Mỗi nhịp mượn một session NGẮN và đóng
nó TRƯỚC khi `yield`: client treo hay biến mất không giữ kết nối pool. Bộ đếm chỗ đếm trong bộ nhớ ⇒ đúng với một tiến
trình (ADR-002).
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from hoicon.db.models import AgentRun, AgentStep
from hoicon.domain.pii import redact_json

logger = logging.getLogger(__name__)

POLL_S = 0.3  # p95 trễ ≈ POLL_S + truy vấn (SC-001: ≤ 0,5 s)
PING_S = 15.0  # dưới hạn chờ đọc mặc định của proxy
MAX_STREAM_S = 600.0  # lượt `waiting` có thể kéo dài tới T3 (900 s): đóng định kỳ để nhả chỗ, client nối lại
DB_FAIL_LIMIT = 3
DB_TIMEOUT_S = 5.0  # một nhịp đọc DB (kể cả chờ pool) không được treo luồng quá lâu
PAGE = 100  # số bước tối đa mỗi nhịp
RETRY_MS = 3000
MAX_STREAMS = 20
MAX_STREAMS_PER_MEMBER = 3
MAX_GUEST_STREAMS = 8  # bể chung của mọi phiên khách gian (một gia đình demo)
MAX_STREAMS_PER_FAMILY = 4  # tối đa 2 người giám hộ/nhà ⇒ không để vài gia đình hợp lại chiếm hết 20 chỗ
BUSY_RETRY_AFTER_S = 5
TERMINAL = ("done", "failed")
HISTORY_LIMIT = 500

Cursor = tuple[datetime, UUID]


# --- dựng bản xuất ----------------------------------------------------------------------------------------------


def _utc_iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _cost(value: Decimal | None) -> str:
    return f"{Decimal(value or 0):.6f}"


def step_view(step: AgentStep) -> dict[str, Any]:
    """Một bước theo `agent_step.v1`: danh sách trắng cột (không có `input_redacted`), `output` đã qua `redact_json`."""
    output = redact_json(step.output) if step.output is not None else None
    return {
        "id": str(step.id),
        "run_id": str(step.run_id),
        "node": step.node,
        "model_profile": step.model_profile,
        "model": step.model,
        "prompt_version": step.prompt_version,
        "latency_ms": step.latency_ms,
        "tokens_in": step.tokens_in,
        "tokens_out": step.tokens_out,
        "cost_usd": _cost(step.cost_usd),
        "fallback_used": step.fallback_used,
        "error": step.error,
        "output": output,
        "at": _utc_iso(step.at),
    }


def run_done_view(run: AgentRun, total_steps: int) -> dict[str, Any]:
    """Payload `event: done` theo `run_done.v1`."""
    return {
        "run_id": str(run.id),
        "status": run.status,
        "total_steps": total_steps,
        "cost_usd": _cost(run.cost_usd),
        "is_drill": run.is_drill,
        "is_demo": run.is_demo,
    }


# --- đọc DB -------------------------------------------------------------------------------------------------------


async def list_steps(
    session: AsyncSession, run_id: UUID, after: Cursor | None = None, limit: int = HISTORY_LIMIT
) -> list[AgentStep]:
    """Bước của lượt theo thứ tự `(at, id)`, chỉ những bước SAU `after`. Khóa kép: hai bước cùng `at` không mất bước."""
    query = select(AgentStep).where(AgentStep.run_id == run_id)
    if after is not None:
        query = query.where(tuple_(AgentStep.at, AgentStep.id) > tuple_(*after))
    rows = await session.scalars(query.order_by(AgentStep.at, AgentStep.id).limit(limit))
    return list(rows)


async def _load_run(session: AsyncSession, run_id: UUID) -> AgentRun | None:
    return await session.scalar(select(AgentRun).where(AgentRun.id == run_id))


async def _find_step(session: AsyncSession, run_id: UUID, step_id: UUID) -> AgentStep | None:
    return await session.scalar(select(AgentStep).where(AgentStep.id == step_id, AgentStep.run_id == run_id))


async def _count_steps(session: AsyncSession, run_id: UUID) -> int:
    return int(await session.scalar(select(func.count()).select_from(AgentStep).where(AgentStep.run_id == run_id)) or 0)


# --- bộ đếm chỗ ---------------------------------------------------------------------------------------------------


class StreamLimitError(Exception):
    """Hết chỗ: 429 (người này mở quá nhiều) hoặc 503 (tiến trình đã đủ luồng); luôn có `Retry-After`."""

    def __init__(self, status_code: int, retry_after_s: int, scope: str = "global") -> None:
        super().__init__(f"stream limit ({status_code})")
        self.status_code = status_code
        self.retry_after_s = retry_after_s
        self.scope = scope  # "member" | "family" | "global"


_open_total = 0
_open_by_member: dict[UUID, int] = {}
_open_by_family: dict[UUID, int] = {}


def _decrement(counter: dict[UUID, int], key: UUID) -> None:
    left = counter.get(key, 1) - 1
    if left > 0:
        counter[key] = left
    else:
        counter.pop(key, None)


@dataclass
class StreamSlot:
    member_id: UUID
    family_id: UUID | None = None
    released: bool = field(default=False, repr=False)

    def release(self) -> None:
        global _open_total
        if self.released:
            return
        self.released = True
        _open_total -= 1
        _decrement(_open_by_member, self.member_id)
        if self.family_id is not None:
            _decrement(_open_by_family, self.family_id)


def slot_keys(member_id: UUID, family_id: UUID | None, *, jti: str | None, guest: bool) -> tuple[UUID, UUID | None]:
    """Khóa đếm luồng. Mọi khách gian dùng chung `member_id` của người giám hộ demo => mỗi PHIÊN khách (`jti`) có chỗ
    riêng (không chiếm hạn mức của người trình bày hay của khách khác), nhưng MỌI khách chung một bể nhỏ
    `MAX_GUEST_STREAMS` để không ai xin nhiều phiên rồi chiếm hết `MAX_STREAMS` của máy chủ (spec 050 T017 #5)."""
    if not guest or jti is None:
        return member_id, family_id
    return uuid5(member_id, jti), (uuid5(family_id, "booth-guests") if family_id is not None else None)


def acquire_slot(
    member_id: UUID, family_id: UUID | None = None, *, family_limit: int = MAX_STREAMS_PER_FAMILY
) -> StreamSlot:
    """Giữ một chỗ cho luồng mới (đồng bộ, không `await` ⇒ không đua giữa các coroutine)."""
    global _open_total
    if _open_by_member.get(member_id, 0) >= MAX_STREAMS_PER_MEMBER:
        raise StreamLimitError(429, BUSY_RETRY_AFTER_S, "member")
    if family_id is not None and _open_by_family.get(family_id, 0) >= family_limit:
        raise StreamLimitError(429, BUSY_RETRY_AFTER_S, "family")
    if _open_total >= MAX_STREAMS:
        raise StreamLimitError(503, BUSY_RETRY_AFTER_S)
    _open_total += 1
    _open_by_member[member_id] = _open_by_member.get(member_id, 0) + 1
    if family_id is not None:
        _open_by_family[family_id] = _open_by_family.get(family_id, 0) + 1
    return StreamSlot(member_id, family_id)


def open_streams() -> int:
    return _open_total


def _reset_slots() -> None:
    """Chỉ cho test."""
    global _open_total
    _open_total = 0
    _open_by_member.clear()
    _open_by_family.clear()


class TraceStreamResponse(StreamingResponse):
    """`StreamingResponse` bảo đảm dọn dẹp: Starlette 1.7 với ASGI ≥ 2.4 báo ngắt bằng `ClientDisconnect` khi ghi và
    KHÔNG tự đóng generator ⇒ tự `aclose()` rồi nhả chỗ trong `finally`."""

    def __init__(self, content: AsyncIterator[str], slot: StreamSlot, **kwargs: Any) -> None:
        super().__init__(content, **kwargs)
        self._slot = slot

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            try:
                await self.body_iterator.aclose()  # type: ignore[attr-defined]
            finally:
                self._slot.release()


# --- luồng SSE ----------------------------------------------------------------------------------------------------


_LINE_BREAKS = {"\u2028": "\\u2028", "\u2029": "\\u2029", "\x85": "\\u0085"}


def _json(value: object) -> str:
    """JSON một dòng. `json.dumps` đã escape `\n`/`\r`; thêm U+2028/2029/0085 để `splitlines()` không tách khung."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).translate(
        str.maketrans(_LINE_BREAKS)
    )


def step_frame(view: dict[str, Any]) -> str:
    return f"id: {view['id']}\nevent: step\ndata: {_json(view)}\n\n"


def _parse_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


async def stream_run(
    sessions: Callable[[], Any],
    run_id: UUID,
    last_event_id: str | None,
    is_disconnected: Callable[[], Any],
    still_allowed: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[str]:
    """Phát các khung SSE của một lượt cho tới khi lượt kết thúc (hoặc `MAX_STREAM_S`, lỗi DB, client ngắt).

    Mỗi nhịp: đọc TRẠNG THÁI trước rồi mới đọc BƯỚC (READ COMMITTED), nên `done` không đến trước bước cuối; session
    đóng trước khi `yield`. Không nuốt `CancelledError`/`GeneratorExit`.
    """
    clock = time.monotonic
    started = last_write = clock()
    resume_from = _parse_uuid(last_event_id)
    cursor: Cursor | None = None
    fails = sent = 0
    try:
        yield f"retry: {RETRY_MS}\n\n"
        while True:
            if await is_disconnected():
                return
            if still_allowed is not None and not await still_allowed():
                return  # người cao tuổi vừa rút đồng ý: luồng đang mở cũng dừng (spec 011 D9)
            run: AgentRun | None
            rows: list[AgentStep] = []
            total = 0
            try:
                async with asyncio.timeout(DB_TIMEOUT_S), sessions() as session:
                    run = await _load_run(session, run_id)
                    if run is None:
                        return  # lượt biến mất (gia đình bị xóa): kết thúc im lặng
                    if resume_from is not None:  # Last-Event-ID: bước không thuộc lượt ⇒ phát lại từ đầu
                        known = await _find_step(session, run_id, resume_from)
                        cursor = (known.at, known.id) if known is not None else None
                        resume_from = None
                    rows = await list_steps(session, run_id, cursor, PAGE)
                    finished = run.status in TERMINAL and len(rows) < PAGE
                    if finished:
                        total = await _count_steps(session, run_id)
                fails = 0
            except (SQLAlchemyError, OSError, TimeoutError, ValueError) as exc:
                fails += 1
                logger.warning("trace stream %s: lỗi đọc lần %d (%s)", run_id, fails, type(exc).__name__)
                if isinstance(exc, ValueError):  # dữ liệu bước hỏng, xác định: thử lại cũng gặp đúng lỗi này
                    yield 'event: error\ndata: {"retryable":false}\n\n'
                    return
                if fails >= DB_FAIL_LIMIT:
                    yield 'event: error\ndata: {"retryable":true}\n\n'
                    return
                run, finished = None, False
            for step in rows:
                try:
                    frame = step_frame(step_view(step))
                except Exception as exc:  # bước không dựng được: dừng rõ ràng thay vì chết im sau khi đã gửi header
                    logger.warning("trace stream %s: không dựng được một bước (%s)", run_id, type(exc).__name__)
                    yield 'event: error\ndata: {"retryable":false}\n\n'  # thử lại cũng gặp đúng bước này
                    return
                yield frame
                cursor = (step.at, step.id)
                last_write = clock()
                sent += 1
            if run is not None and finished:
                yield f"event: done\ndata: {_json(run_done_view(run, total))}\n\n"
                return
            now = clock()
            if now - started >= MAX_STREAM_S:
                return  # client nối lại bằng Last-Event-ID
            if now - last_write >= PING_S:
                yield ": ping\n\n"
                last_write = now
            if len(rows) < PAGE:
                await asyncio.sleep(POLL_S)
    finally:
        logger.debug("trace stream %s: đóng sau %d bước", run_id, sent)
