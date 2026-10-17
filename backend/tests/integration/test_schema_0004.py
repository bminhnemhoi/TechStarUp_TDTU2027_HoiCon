"""Migration 0004 (spec 003, ADR-006): `threat_indicators` — danh sách đe dọa chỉ lưu HMAC, không lưu h1."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError

from hoicon.db.models import ThreatIndicator
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

FIXTURE_HMAC = "ab" * 32  # chuỗi giả, không phải HMAC của số nào
ROW: dict[str, Any] = {
    "kind": "phone",
    "value_hmac": FIXTURE_HMAC,
    "value_kid": 1,
    "source": "fixture",
    "confidence": 0.9,
    "list_version": "test-0004",
}


@pytest.fixture(autouse=True)
async def clean(require_db: None) -> AsyncGenerator[None]:
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == "test-0004"))


async def insert(**changes: Any) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(ThreatIndicator(**{**ROW, **changes}))


async def test_columns_match_the_data_model_and_hold_no_raw_number() -> None:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, character_maximum_length, is_nullable "
                    "from information_schema.columns where table_name = 'threat_indicators'"
                )
            )
        ).all()
    cols = {r.column_name: r for r in rows}
    assert set(cols) == {
        "id",
        "kind",
        "value_hmac",
        "value_kid",
        "last3",
        "source",
        "confidence",
        "tactic",
        "list_version",
        "is_demo",
        "first_seen",
        "last_seen",
        "expires_at",
        "bucket_enc",  # migration 0007 (spec 026): bucket 24 bit đã mã hóa
    }
    assert not [name for name in cols if "h1" in name or "phone" in name or "number" in name]
    assert (cols["value_hmac"].data_type, cols["value_hmac"].character_maximum_length) == ("character", 64)
    assert (cols["last3"].data_type, cols["last3"].character_maximum_length) == ("character", 3)
    assert cols["last3"].is_nullable == "YES" and cols["expires_at"].is_nullable == "YES"
    assert cols["value_kid"].data_type == "smallint"


async def test_the_tuple_kind_kid_hmac_is_unique() -> None:
    await insert()
    with pytest.raises(IntegrityError):
        await insert()
    await insert(value_kid=2)  # cùng HMAC nhưng pepper kid khác: được (xoay pepper)


async def test_unique_key_is_the_lookup_index() -> None:
    async with get_engine().connect() as conn:
        defs = list(await conn.scalars(text("select indexdef from pg_indexes where tablename = 'threat_indicators'")))
    assert any("UNIQUE" in d and "kind, value_kid, value_hmac" in d for d in defs)


async def test_kind_and_confidence_are_constrained() -> None:
    with pytest.raises(IntegrityError):
        await insert(kind="email")
    with pytest.raises(IntegrityError):
        await insert(confidence=1.5)
    with pytest.raises(IntegrityError):
        await insert(confidence=-0.1)
    with pytest.raises(IntegrityError):
        await insert(value_hmac="ab" * 31)  # char(64) tự đệm khoảng trắng ⇒ phải có CHECK 64 hex
    with pytest.raises(IntegrityError):
        await insert(value_hmac="zz" * 32)  # đủ 64 ký tự nhưng không phải hex
    with pytest.raises(IntegrityError):
        await insert(value_hmac="AB" * 32)  # hex chữ hoa: HMAC luôn lưu chữ thường
    await insert(confidence=0)
    await insert(value_kid=3, confidence=1, last3="002", tactic="impersonation_authority")


async def test_defaults() -> None:
    await insert()
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(ThreatIndicator).where(ThreatIndicator.list_version == "test-0004"))).one()
    assert row.is_demo is False and row.expires_at is None and row.first_seen is not None and row.last_seen is not None
