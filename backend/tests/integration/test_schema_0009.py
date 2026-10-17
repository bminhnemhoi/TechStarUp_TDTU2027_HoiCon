"""Migration 0009 (spec 034): data_requests, tombstone families/members, chỉ mục cho job hạn lưu."""

import secrets
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import DataRequest, Family, Member
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration


@pytest.fixture
async def family(require_db: None) -> AsyncGenerator[UUID]:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name=f"test-0009-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(fam)
        await session.flush()
        family_id = fam.id
    yield family_id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from data_requests where family_id = :f"), {"f": family_id})
        await session.execute(text("delete from families where id = :f"), {"f": family_id})


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


def request(family_id: UUID, **changes: Any) -> DataRequest:
    base: dict[str, Any] = {"id": new_id(), "family_id": family_id, "requested_via": "ops"}
    return DataRequest(**{**base, **changes})


async def test_columns_and_defaults(family: UUID) -> None:
    cols = await columns("data_requests")
    assert set(cols) == {
        "id",
        "family_id",
        "kind",
        "requested_via",
        "status",
        "error_code",
        "requested_at",
        "completed_at",
    }
    assert cols["error_code"].is_nullable == "YES" and cols["completed_at"].is_nullable == "YES"
    async with get_sessionmaker().begin() as session:
        session.add(request(family))
    async with get_sessionmaker()() as session:
        row = (await session.execute(select(DataRequest).where(DataRequest.family_id == family))).scalar_one()
    assert (row.kind, row.status, row.requested_via) == ("delete", "pending", "ops")
    assert row.requested_at is not None and row.completed_at is None and row.error_code is None


async def test_no_column_can_hold_free_text() -> None:
    cols = await columns("data_requests")
    assert not any(bad in name for name in cols for bad in ("note", "text", "reason", "comment", "message"))
    assert {n for n, c in cols.items() if c.data_type in ("character varying", "text")} == {
        "kind",
        "requested_via",
        "status",
        "error_code",
    }


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "export"},
        {"requested_via": "email"},
        {"status": "running"},
        {"status": "done"},  # đã xong mà chưa có completed_at
    ],
    ids=lambda b: next(iter(b)) + "=" + str(next(iter(b.values()))),
)
async def test_check_constraints(family: UUID, bad: dict[str, Any]) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(request(family, **bad))


async def test_completed_at_without_done_is_refused(family: UUID) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(request(family, status="pending", completed_at=text("now()")))


@pytest.mark.parametrize("via", ["ops", "app", "web"])
@pytest.mark.parametrize("status", ["pending", "failed"])
async def test_documented_values_are_accepted(family: UUID, via: str, status: str) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(request(family, requested_via=via, status=status, error_code="x" if status == "failed" else None))


async def test_done_needs_a_completion_time(family: UUID) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(request(family, status="done", completed_at=text("now()")))


async def test_a_family_with_a_request_cannot_be_deleted(family: UUID) -> None:
    """RESTRICT: vết pháp lý còn lại; gia đình bị ẩn danh chứ không bị xóa."""
    async with get_sessionmaker().begin() as session:
        session.add(request(family))
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            await session.execute(text("delete from families where id = :f"), {"f": family})


async def test_a_request_needs_a_real_family(require_db: None) -> None:
    with pytest.raises(IntegrityError):
        async with get_sessionmaker().begin() as session:
            session.add(request(new_id()))


async def test_tombstone_columns_exist_and_are_nullable(family: UUID) -> None:
    for table in ("families", "members"):
        col = (await columns(table))["deleted_at"]
        assert col.is_nullable == "YES" and col.data_type == "timestamp with time zone"
    async with get_sessionmaker()() as session:
        assert (await session.get(Family, family)).deleted_at is None  # type: ignore[union-attr]
    async with get_sessionmaker().begin() as session:
        member = Member(family_id=family, role="protected")
        session.add(member)
        await session.flush()
        assert member.deleted_at is None


@pytest.mark.parametrize(
    ("name", "table", "definition"),
    [
        ("ix_agent_steps_at", "agent_steps", "(at)"),
        ("ix_jobs_done_at", "jobs", "(done_at)"),
        ("ix_risk_events_received", "risk_events", "(received_at)"),
        ("ix_data_requests_family", "data_requests", "(family_id)"),
    ],
)
async def test_retention_indexes_exist(require_db: None, name: str, table: str, definition: str) -> None:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text("select indexdef from pg_indexes where indexname = :n and tablename = :t"), {"n": name, "t": table}
            )
        ).all()
    assert len(rows) == 1 and definition in rows[0].indexdef
