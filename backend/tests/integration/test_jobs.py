"""Hàng đợi job Postgres: chống trùng theo khóa, SKIP LOCKED không giao trùng, thử lại có giãn cách."""

import asyncio

import pytest
from sqlalchemy import func, select, update

from hoicon.db.ids import new_id
from hoicon.db.models import Job
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import MAX_ATTEMPTS, cancel_prefix, claim_due, complete, enqueue

pytestmark = pytest.mark.integration


async def mine(prefix: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(Job).where(Job.idempotency_key.startswith(prefix))))


async def test_enqueue_is_idempotent_and_claims_never_overlap(threads: list[str]) -> None:
    prefix = str(new_id())
    threads.append(prefix)
    sessions = get_sessionmaker()
    for i in range(3):
        await enqueue(sessions, "test", {"i": i}, key=f"{prefix}:job:{i}")
    await enqueue(sessions, "test", {"i": 0}, key=f"{prefix}:job:0")  # trùng khóa ⇒ bỏ qua
    assert len(await mine(prefix)) == 3

    a, b = await asyncio.gather(claim_due(sessions, "w1", 50), claim_due(sessions, "w2", 50))
    ours_a = {j.id for j in a if j.idempotency_key.startswith(prefix)}
    ours_b = {j.id for j in b if j.idempotency_key.startswith(prefix)}
    assert not ours_a & ours_b and len(ours_a | ours_b) == 3
    # Nhả khóa job không thuộc test này (DB dev có thể còn job cũ đến hạn).
    foreign = [j.id for j in [*a, *b] if not (j.idempotency_key or "").startswith(prefix)]
    async with sessions.begin() as session:
        await session.execute(update(Job).where(Job.id.in_(foreign)).values(locked_at=None, locked_by=None))


async def test_failed_job_backs_off_then_gives_up(threads: list[str]) -> None:
    prefix = str(new_id())
    threads.append(prefix)
    sessions = get_sessionmaker()
    await enqueue(sessions, "test", {}, key=f"{prefix}:job")
    job = next(j for j in await claim_due(sessions, "w", 50) if j.idempotency_key == f"{prefix}:job")
    await complete(sessions, job, error="Boom")
    (row,) = await mine(prefix)
    assert row.done_at is None and row.error == "Boom" and row.locked_by is None and row.run_at > job.run_at

    # Lần lấy thứ MAX_ATTEMPTS (đưa job về đến hạn thay vì chờ giãn cách) lại lỗi ⇒ dừng thử lại, giữ lỗi để chẩn đoán.
    async with sessions.begin() as session:
        await session.execute(update(Job).where(Job.id == job.id).values(attempts=MAX_ATTEMPTS - 1, run_at=func.now()))
    job = next(j for j in await claim_due(sessions, "w", 50) if j.idempotency_key == f"{prefix}:job")
    assert job.attempts == MAX_ATTEMPTS
    await complete(sessions, job, error="Boom")
    (row,) = await mine(prefix)
    assert row.done_at is not None and row.error == "Boom"


async def test_stale_worker_cannot_complete_a_reclaimed_job(threads: list[str]) -> None:
    prefix = str(new_id())
    threads.append(prefix)
    sessions = get_sessionmaker()
    await enqueue(sessions, "test", {}, key=f"{prefix}:job")
    stale = next(j for j in await claim_due(sessions, "old", 50) if j.idempotency_key == f"{prefix}:job")
    async with sessions.begin() as session:  # khóa của worker cũ hết hạn, worker mới lấy lại
        await session.execute(update(Job).where(Job.id == stale.id).values(locked_by="new"))
    await complete(sessions, stale)
    (row,) = await mine(prefix)
    assert row.done_at is None and row.locked_by == "new"


async def test_cancel_prefix_only_removes_pending(threads: list[str]) -> None:
    prefix = str(new_id())
    threads.append(prefix)
    sessions = get_sessionmaker()
    await enqueue(sessions, "test", {}, key=f"{prefix}:timer:a")
    await enqueue(sessions, "test", {}, key=f"{prefix}:timer:b")
    done = next(j for j in await claim_due(sessions, "w", 50) if j.idempotency_key == f"{prefix}:timer:a")
    await complete(sessions, done)
    assert await cancel_prefix(sessions, f"{prefix}:timer:") == 1
    assert [j.idempotency_key for j in await mine(prefix)] == [f"{prefix}:timer:a"]


async def test_run_once_tells_the_handler_which_attempt_it_is_without_touching_stored_payload(
    threads: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.jobs import queue
    from hoicon.jobs.queue import ATTEMPT_KEY, run_once

    prefix = str(new_id())
    threads.append(prefix)
    sessions = get_sessionmaker()
    kind = f"attempt-probe-{prefix}"
    await enqueue(sessions, kind, {"x": 1}, key=f"{prefix}:probe")
    real_claim = queue.claim_due

    async def only_mine(sessions_: object, worker_id: str, limit: int = 10) -> list[Job]:
        """DB dev có thể còn job của test khác: chỉ nhận job của mình, nhả khóa phần còn lại (không để `no_handler`)."""
        jobs = await real_claim(sessions_, worker_id, 50)  # type: ignore[arg-type]
        foreign = [j.id for j in jobs if j.kind != kind]
        async with sessions.begin() as session:
            await session.execute(update(Job).where(Job.id.in_(foreign)).values(locked_at=None, locked_by=None))
        return [j for j in jobs if j.kind == kind]

    monkeypatch.setattr(queue, "claim_due", only_mine)
    seen: list[dict] = []

    async def fail_once(payload: dict) -> None:
        seen.append(payload)
        raise RuntimeError("thử lại")

    await run_once(sessions, {kind: fail_once}, "w-probe")
    assert seen == [{"x": 1, ATTEMPT_KEY: 1}]
    (job,) = await mine(prefix)
    assert job.payload == {"x": 1} and job.attempts == 1 and job.error == "RuntimeError"
