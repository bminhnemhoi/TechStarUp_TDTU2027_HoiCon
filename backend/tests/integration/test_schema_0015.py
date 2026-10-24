"""Migration 0015 (spec 038 T007): `data_requests.execute_after` + trạng thái `cancelled`."""

import pytest
from sqlalchemy import text

from hoicon.db.models import DataRequest
from hoicon.db.session import get_engine

pytestmark = pytest.mark.integration


async def test_execute_after_is_a_non_null_timestamp_defaulting_to_now(require_db: None) -> None:
    async with get_engine().connect() as conn:
        row = (
            await conn.execute(
                text(
                    "select data_type, is_nullable, column_default from information_schema.columns "
                    "where table_name = 'data_requests' and column_name = 'execute_after'"
                )
            )
        ).one()
    assert (row.data_type, row.is_nullable) == ("timestamp with time zone", "NO") and "now()" in row.column_default


async def test_status_check_allows_cancelled_and_still_rejects_unknown_values(require_db: None) -> None:
    async with get_engine().connect() as conn:
        definition = (
            await conn.execute(
                text("select pg_get_constraintdef(oid) from pg_constraint where conname = 'ck_data_requests_status'")
            )
        ).scalar_one()
    assert "cancelled" in definition and "pending" in definition and "done" in definition
    assert "execute_after" in DataRequest.__table__.c
