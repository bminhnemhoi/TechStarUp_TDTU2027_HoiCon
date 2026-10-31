"""Migration 0003 (spec 002, ADR-010 D2): families, members, pairing_codes, messages_out và các ràng buộc của chúng."""

from collections.abc import AsyncGenerator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from hoicon.db.ids import new_id
from hoicon.db.models import Family, Member, MessageOut, PairingCode
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

ZALO = {"zalo_bot_id": "fixture-bot", "zalo_user_hmac": "ab" * 32, "zalo_hmac_kid": 1, "zalo_chat_enc": "1.AAAA"}


@pytest.fixture
async def family(require_db: None) -> AsyncGenerator[Family]:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name="Gia đình mẫu", region="nam", is_demo=True)
        session.add(fam)
    yield fam
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Family).where(Family.id == fam.id))


async def insert(obj: Any) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(obj)


def guardian(family: Family, rank: int | None, **extra: Any) -> Member:
    return Member(family_id=family.id, role="guardian", guardian_rank=rank, **extra)


async def test_tables_and_key_indexes_exist(require_db: None) -> None:
    async with get_engine().connect() as conn:
        tables = set(
            await conn.scalars(
                text("select tablename from pg_tables where schemaname = 'public' and tablename = any(:t)").bindparams(
                    t=["families", "members", "pairing_codes", "messages_out"]
                )
            )
        )
        indexes = set(await conn.scalars(text("select indexname from pg_indexes where tablename = 'messages_out'")))
    assert tables == {"families", "members", "pairing_codes", "messages_out"}
    assert "ix_messages_out_quota" in indexes


async def test_guardian_rank_is_unique_per_family_and_limited_to_1_2(family: Family) -> None:
    await insert(guardian(family, 1))
    await insert(guardian(family, 2))
    with pytest.raises(IntegrityError):
        await insert(guardian(family, 1))
    with pytest.raises(IntegrityError):
        await insert(guardian(family, 3))
    with pytest.raises(IntegrityError):
        await insert(guardian(family, None))  # người giám hộ phải có hạng
    with pytest.raises(IntegrityError):
        await insert(Member(family_id=family.id, role="protected", guardian_rank=1))  # người được bảo vệ không có hạng
    await insert(Member(family_id=family.id, role="protected"))
    await insert(Member(family_id=family.id, role="protected"))  # nhiều người được bảo vệ cùng gia đình: được


async def test_one_zalo_account_cannot_join_two_families(family: Family) -> None:
    bot = f"fixture-bot-{new_id()}"
    zalo = {**ZALO, "zalo_bot_id": bot}
    async with get_sessionmaker().begin() as session:
        other = Family(display_name="Gia đình khác", region="bac", is_demo=True)
        session.add(other)
    try:
        await insert(guardian(family, 1, **zalo))
        with pytest.raises(IntegrityError):
            await insert(Member(family_id=other.id, role="guardian", guardian_rank=1, **zalo))
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(delete(Family).where(Family.id == other.id))


async def test_zalo_columns_are_all_or_nothing(family: Family) -> None:
    with pytest.raises(IntegrityError):
        await insert(guardian(family, 1, zalo_bot_id="fixture-bot-x"))  # thiếu HMAC/chat_enc
    with pytest.raises(IntegrityError):
        await insert(guardian(family, 1, **{**ZALO, "zalo_chat_enc": None}))


async def test_enums_are_checked(family: Family) -> None:
    with pytest.raises(IntegrityError):
        await insert(Family(display_name="x", region="mars"))
    with pytest.raises(IntegrityError):
        await insert(Member(family_id=family.id, role="admin"))
    with pytest.raises(IntegrityError):
        await insert(MessageOut(family_id=family.id, channel="sms", bot_id="b", template_id="t", status="queued"))
    with pytest.raises(IntegrityError):
        await insert(MessageOut(family_id=family.id, channel="zalo", bot_id="b", template_id="t", status="done"))


async def test_messages_out_job_key_is_unique_and_family_may_be_null(family: Family) -> None:
    key = f"{new_id()}:msg:fast_alert"
    row = {"channel": "zalo", "bot_id": "fixture-bot", "template_id": "fast_alert", "quota_month": "2026-10"}
    await insert(MessageOut(family_id=family.id, status="queued", job_key=key, **row))
    with pytest.raises(IntegrityError):
        await insert(MessageOut(family_id=family.id, status="queued", job_key=key, **row))
    # tin trả lời người chưa ghép (chưa có gia đình) vẫn phải được đếm hạn mức ⇒ family_id có thể rỗng
    stranger_key = f"zalo:fixture-bot:{new_id()}"
    await insert(MessageOut(family_id=None, status="sent", job_key=stranger_key, **row))
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(MessageOut).where(MessageOut.job_key.in_([stranger_key, key])))


async def test_deleting_family_removes_members_and_codes_but_keeps_the_quota_history(family: Family) -> None:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name="Sẽ xóa", region="trung", is_demo=True)
        session.add(fam)
    bot = f"b-{new_id()}"
    member = Member(family_id=fam.id, role="guardian", guardian_rank=1, **{**ZALO, "zalo_bot_id": bot})
    await insert(member)
    async with get_sessionmaker().begin() as session:
        session.add(PairingCode(family_id=fam.id, code_hash="cd" * 32, expires_at=func.now() + timedelta(minutes=15)))
        session.add(
            MessageOut(
                family_id=fam.id,
                member_id=member.id,
                channel="zalo",
                bot_id=bot,
                template_id="fast_alert",
                status="sent",
                quota_month="2026-10",
            )
        )
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Family).where(Family.id == fam.id))
    async with get_sessionmaker()() as session:
        for model in (Member, PairingCode):
            assert await session.scalar(select(func.count()).select_from(model).where(model.family_id == fam.id)) == 0
        # tin đã gửi vẫn còn (mồ côi gia đình) để bộ đếm hạn mức theo bot/tháng không bị tụt khi xóa gia đình
        kept = (await session.scalars(select(MessageOut).where(MessageOut.bot_id == bot))).all()
    assert [(m.status, m.family_id, m.member_id) for m in kept] == [("sent", None, None)]
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(MessageOut).where(MessageOut.bot_id == bot))


async def test_pairing_code_hash_is_unique_among_unused_codes(family: Family) -> None:
    expires = func.now() + timedelta(minutes=15)
    code_hash = "ef" * 32
    await insert(PairingCode(family_id=family.id, code_hash=code_hash, expires_at=expires))
    with pytest.raises(IntegrityError):
        await insert(PairingCode(family_id=family.id, code_hash=code_hash, expires_at=expires))
    async with get_sessionmaker().begin() as session:  # mã đã dùng thì cho phép sinh lại cùng dãy số về sau
        await session.execute(
            text("update pairing_codes set used_at = now() where code_hash = :h").bindparams(h=code_hash)
        )
    await insert(PairingCode(family_id=family.id, code_hash=code_hash, expires_at=expires))
