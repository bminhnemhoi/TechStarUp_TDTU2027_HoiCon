"""Hàng đợi job trong Postgres (ADR-004, ARCHITECTURE §4): bộ hẹn giờ T1/T2/T3 và việc có tác dụng phụ.

- `enqueue` có `key` ⇒ chạy lại node (sau interrupt hay kill -9) không tạo job trùng. Mốc chạy do Postgres tính
  (`now() + delay`) để so cùng một đồng hồ với `claim_due` (giờ container có thể lệch giờ máy chạy app).
- `claim_due` dùng `FOR UPDATE SKIP LOCKED`: nhiều worker không lấy trùng một job; job bị khóa quá `STALE_LOCK` (worker
  chết giữa chừng) được lấy lại.
- Handler phải idempotent: một job có thể chạy lại nếu worker chết sau khi làm xong nhưng trước khi `complete`.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.db.ids import new_id
from hoicon.db.models import Job

logger = logging.getLogger(__name__)

STALE_LOCK = timedelta(minutes=5)
MAX_ATTEMPTS = 5
# Handler biết đây là lần thử thứ mấy (để quyết định "hết số lần thử ⇒ cần dự phòng" thay vì raise nữa): `run_once` thêm
# khóa này vào BẢN SAO payload; payload lưu trong DB không đổi.
ATTEMPT_KEY = "_attempt"

Handler = Callable[[dict[str, Any]], Awaitable[None]]


async def enqueue(
    sessions: async_sessionmaker | AsyncSession,
    kind: str,
    payload: dict[str, Any],
    *,
    delay_s: float = 0.0,
    key: str | None = None,
) -> None:
    run_at = func.now() + timedelta(seconds=delay_s)
    stmt = insert(Job).values(id=new_id(), kind=kind, payload=payload, run_at=run_at, idempotency_key=key)
    if isinstance(sessions, AsyncSession):
        await sessions.execute(stmt.on_conflict_do_nothing(index_elements=[Job.idempotency_key]))
    else:
        async with sessions.begin() as session:
            await session.execute(stmt.on_conflict_do_nothing(index_elements=[Job.idempotency_key]))


async def cancel_prefix(sessions: async_sessionmaker, key_prefix: str) -> int:
    """Hủy các job CHƯA chạy có khóa bắt đầu bằng `key_prefix` (vd. mọi bộ hẹn giờ của một sự cố đã đóng)."""
    async with sessions.begin() as session:
        result = await session.execute(
            delete(Job).where(Job.idempotency_key.startswith(key_prefix, autoescape=True), Job.done_at.is_(None))
        )
    return result.rowcount


async def claim_due(sessions: async_sessionmaker, worker_id: str, limit: int = 10) -> list[Job]:
    now = func.now()
    due = (
        select(Job.id)
        .where(
            Job.done_at.is_(None),
            Job.run_at <= now,
            or_(Job.locked_at.is_(None), Job.locked_at < now - STALE_LOCK),
        )
        .order_by(Job.run_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    async with sessions.begin() as session:
        result = await session.execute(
            update(Job)
            .where(Job.id.in_(due))
            .values(locked_at=now, locked_by=worker_id, attempts=Job.attempts + 1)
            .returning(Job)
        )
        return list(result.scalars())


async def complete(sessions: async_sessionmaker, job: Job, error: str | None = None) -> None:
    """Xong ⇒ `done_at`. Lỗi ⇒ thử lại sau 2^attempts giây, tới `MAX_ATTEMPTS` thì dừng và giữ lỗi."""
    values: dict[str, Any] = {"locked_at": None, "locked_by": None, "error": error}
    if error is None or job.attempts >= MAX_ATTEMPTS:
        values["done_at"] = func.now()
    else:
        values["run_at"] = func.now() + timedelta(seconds=2**job.attempts)
    async with sessions.begin() as session:
        await session.execute(
            update(Job).where(and_(Job.id == job.id, Job.locked_by == job.locked_by)).values(**values)
        )


async def run_once(sessions: async_sessionmaker, handlers: dict[str, Handler], worker_id: str) -> int:
    """Lấy và chạy một lượt job đến hạn; trả số job đã xử lý."""
    jobs = await claim_due(sessions, worker_id)
    for job in jobs:
        handler = handlers.get(job.kind)
        if handler is None:
            await complete(sessions, job, error=f"no_handler:{job.kind}")
            continue
        try:
            await handler({**job.payload, ATTEMPT_KEY: job.attempts})
        except Exception as exc:  # job lỗi không được làm chết worker; giữ tên lớp lỗi để chẩn đoán
            logger.exception("job %s (%s) failed", job.id, job.kind)
            await complete(sessions, job, error=type(exc).__name__)
        else:
            await complete(sessions, job)
    return len(jobs)
