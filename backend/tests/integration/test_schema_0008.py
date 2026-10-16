"""Migration 0008 (spec 028): bảng `drills`."""

import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from consent_support import purge_family
from sqlalchemy import select, text
from sqlalchemy.exc import DataError, IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import Drill, Family, Member
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

START = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0008-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        ids = {"family": family.id, "member": member.id}
    yield ids
    await purge_family(ids["family"])


def drill(ids: dict[str, UUID], **changes: Any) -> Drill:
    base: dict[str, Any] = {
        "id": new_id(),
        "family_id": ids["family"],
        "member_id": ids["member"],
        "scheduled_by": "ops",
        "script_id": "drill_bank_card_locked",
        "window_start": START,
        "window_end": START + timedelta(minutes=30),
    }
    return Drill(**{**base, **changes})


async def columns(table: str) -> dict[str, Any]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, is_nullable from information_schema.columns where table_name = :t"
                ),
                {"t": table},
            )
        ).all()
    return {r.column_name: r for r in rows}


async def test_columns_and_defaults(world: dict[str, UUID]) -> None:
    cols = await columns("drills")
    assert set(cols) == {
        "id",
        "family_id",
        "member_id",
        "scheduled_by",
        "script_id",
        "window_start",
        "window_end",
        "status",
        "score",
        "answers",
        "offered_at",
        "started_at",
        "completed_at",
        "debriefed_at",
        "is_demo",
        "created_at",
    }
    for nullable in ("score", "answers", "offered_at", "started_at", "completed_at", "debriefed_at"):
        assert cols[nullable].is_nullable == "YES", nullable
    async with get_sessionmaker().begin() as session:
        session.add(drill(world))
    async with get_sessionmaker()() as session:
        row = (await session.execute(select(Drill).where(Drill.family_id == world["family"]))).scalar_one()
    assert row.status == "scheduled"
    assert row.is_demo is False
    assert row.created_at is not None
    assert row.score is None and row.answers is None


async def test_no_column_can_hold_free_text() -> None:
    """SC-006: chỉ mã lựa chọn. Cột văn bản duy nhất nhận chữ do máy ghi là `answers` (jsonb mảng); không có `note`."""
    cols = await columns("drills")
    for name in cols:
        assert not any(bad in name for bad in ("note", "text", "comment", "message", "audio", "phone", "h1")), name
    # Cột chuỗi: chỉ các cột do máy chủ đặt (không có chỗ máy nhét chữ tự do).
    strings = {n for n, c in cols.items() if c.data_type in ("character varying", "text")}
    assert strings == {"scheduled_by", "script_id", "status"}


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "running"},
        {"status": "PASSED"},
        {"window_end": START},  # bằng window_start
        {"window_end": START - timedelta(minutes=30)},  # đảo ngược
        {"window_end": START + timedelta(minutes=29, seconds=59)},  # ngắn hơn 30 phút
        {"window_end": START + timedelta(hours=4, seconds=1)},  # dài hơn 4 giờ
        {"status": "passed"},  # đã chấm mà không có điểm
        {"status": "failed"},
        {"score": 3},  # có điểm mà chưa chấm (status scheduled)
        {"status": "passed", "score": 6},
        {"status": "failed", "score": -1},
        {"answers": {"step": 0, "choice_id": "a"}},  # jsonb không phải mảng
        {"answers": "bác thấy lạ"},
    ],
    ids=lambda b: next(iter(b)) + "=" + str(next(iter(b.values()))),
)
async def test_check_constraints(world: dict[str, UUID], bad: dict[str, Any]) -> None:
    with pytest.raises((IntegrityError, DataError)):
        async with get_sessionmaker().begin() as session:
            session.add(drill(world, **bad))


@pytest.mark.parametrize("status", ["scheduled", "offered", "in_progress", "aborted", "declined", "expired"])
async def test_every_ungraded_status_is_accepted_without_a_score(world: dict[str, UUID], status: str) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(drill(world, status=status))


@pytest.mark.parametrize("status", ["passed", "failed"])
async def test_graded_status_needs_a_score(world: dict[str, UUID], status: str) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(drill(world, status=status, score=0, answers=[{"step": 0, "choice_id": "a"}]))


@pytest.mark.parametrize("minutes", [30, 90, 240])
async def test_window_bounds_are_inclusive(world: dict[str, UUID], minutes: int) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(drill(world, window_end=START + timedelta(minutes=minutes)))


async def test_the_family_index_exists() -> None:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(text("select indexdef from pg_indexes where indexname = 'ix_drills_family_window'"))
        ).all()
    assert len(rows) == 1
    assert "(family_id, window_start)" in rows[0].indexdef


async def test_deleting_the_family_cascades_to_drills() -> None:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-0008-cascade-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        ids = {"family": family.id, "member": member.id}
        session.add(drill(ids))
        session.add(drill(ids, window_start=START + timedelta(days=1), window_end=START + timedelta(days=1, hours=1)))
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": ids["family"]})
    async with get_sessionmaker()() as session:
        left = (
            await session.execute(text("select count(*) from drills where family_id = :f"), {"f": ids["family"]})
        ).scalar_one()
    assert left == 0


async def test_deleting_the_member_cascades_to_drills(world: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(drill(world))
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from members where id = :m"), {"m": world["member"]})
    async with get_sessionmaker()() as session:
        left = (
            await session.execute(text("select count(*) from drills where family_id = :f"), {"f": world["family"]})
        ).scalar_one()
    assert left == 0


async def test_a_drill_needs_a_real_family_and_member(world: dict[str, UUID]) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(drill(world, family_id=new_id()))
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(drill(world, member_id=new_id()))
