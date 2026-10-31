"""Migration 0005 (spec 020): devices, consents (chỉ ghi thêm bằng trigger), trusted_contacts, action_tokens."""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

import pytest
from consent_support import purge_family
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from hoicon.db.models import ActionToken, Consent, Device, Family, Member, TrustedContact
from hoicon.db.session import get_engine, get_sessionmaker

pytestmark = pytest.mark.integration

HEX64 = "ab" * 32  # chuỗi giả, không phải băm của dữ liệu thật


@pytest.fixture
async def world(require_db: None) -> AsyncGenerator[tuple[UUID, UUID]]:
    """(family_id, member_id) giả; dọn cuối test. `consents` chặn DELETE nên tắt trigger CHỈ trong giao dịch dọn."""
    async with get_sessionmaker().begin() as session:
        family = Family(display_name="test-0005", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        ids = (family.id, member.id)
    yield ids
    await purge_family(ids[0])


def consent(family_id: UUID, member_id: UUID, **changes: Any) -> Consent:
    base: dict[str, Any] = {
        "family_id": family_id,
        "member_id": member_id,
        "purpose": "core_protection",
        "granted": True,
        "consent_version": "v1",
        "text_sha256": HEX64,
        "channel": "app",
    }
    return Consent(**{**base, **changes})


async def columns(table: str) -> dict[str, Any]:
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select column_name, data_type, character_maximum_length, is_nullable "
                    "from information_schema.columns where table_name = :t"
                ),
                {"t": table},
            )
        ).all()
    return {r.column_name: r for r in rows}


async def test_columns_match_the_data_model_and_hold_no_raw_pii(require_db: None) -> None:
    expected = {
        "devices": {
            "id",
            "family_id",
            "member_id",
            "platform",
            "label",
            "app_version",
            "rules_version",
            "threat_list_version",
            "permission_state",
            "fcm_token_enc",
            "device_secret_hash",
            "last_heartbeat_at",
            "revoked_at",
            "created_at",
        },
        "consents": {
            "id",
            "family_id",
            "member_id",
            "purpose",
            "granted",
            "consent_version",
            "text_sha256",
            "channel",
            "recorded_at",
        },
        "trusted_contacts": {"id", "family_id", "member_id", "phone_hmac", "phone_kid", "last3", "label", "created_at"},
        "action_tokens": {
            "id",
            "incident_id",
            "member_id",
            "token_hash",
            "scope",
            "expires_at",
            "used_at",
            "created_at",
        },
    }
    for table, names in expected.items():
        cols = await columns(table)
        assert set(cols) == names, table
        # Không cột nào có thể chứa số điện thoại / tên thật / Zalo ID thô (FR-011).
        assert not [c for c in cols if any(w in c for w in ("phone_number", "real_name", "zalo_id", "otp"))]
    cols = await columns("devices")
    assert (cols["device_secret_hash"].data_type, cols["device_secret_hash"].character_maximum_length) == (
        "character",
        64,
    )
    assert cols["permission_state"].data_type == "jsonb"
    assert (await columns("trusted_contacts"))["phone_hmac"].character_maximum_length == 64
    assert (await columns("trusted_contacts"))["last3"].character_maximum_length == 3
    assert (await columns("consents"))["text_sha256"].character_maximum_length == 64


async def test_device_constraints(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    base = {
        "family_id": family_id,
        "member_id": member_id,
        "app_version": "0.2.0",
        "rules_version": "r1",
        "device_secret_hash": HEX64,
    }
    async with get_sessionmaker().begin() as session:
        session.add(Device(**base))
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(Device).where(Device.family_id == family_id))).one()
        assert row.platform == "android" and row.permission_state == {} and row.revoked_at is None
        assert row.last_heartbeat_at is not None and row.created_at is not None
    for bad in ({"platform": "symbian"}, {"device_secret_hash": "ab" * 31}, {"device_secret_hash": "AB" * 32}):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(Device(**{**base, **bad}))
    with pytest.raises(IntegrityError):  # token hash trùng giữa hai thiết bị ⇒ không cho
        async with get_sessionmaker().begin() as session:
            session.add(Device(**base))


async def test_consent_constraints(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    async with get_sessionmaker().begin() as session:
        session.add(consent(family_id, member_id))
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(Consent).where(Consent.family_id == family_id))).one()
        assert row.recorded_at is not None
    for bad in (
        {"purpose": "sell_data"},
        {"channel": "sms"},
        {"text_sha256": "zz" * 32},
        {"text_sha256": "ab" * 31},
    ):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(consent(family_id, member_id, **bad))


async def test_consents_are_append_only_update_is_blocked(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    async with get_sessionmaker().begin() as session:
        session.add(consent(family_id, member_id))
    with pytest.raises(DBAPIError, match="append-only"):
        async with get_sessionmaker().begin() as session:
            await session.execute(text("update consents set granted = false where family_id = :f"), {"f": family_id})
    async with get_sessionmaker()() as session:  # giao dịch bị hủy: dòng giữ nguyên
        assert (await session.scalars(select(Consent.granted).where(Consent.family_id == family_id))).one() is True


async def test_consents_are_append_only_delete_is_blocked(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    async with get_sessionmaker().begin() as session:
        session.add(consent(family_id, member_id))
    with pytest.raises(DBAPIError, match="append-only"):
        async with get_sessionmaker().begin() as session:
            await session.execute(text("delete from consents where family_id = :f"), {"f": family_id})
    with pytest.raises(IntegrityError):  # xóa gia đình cũng không được kéo theo xóa bằng chứng đồng ý (FK RESTRICT)
        async with get_sessionmaker().begin() as session:
            await session.execute(text("delete from families where id = :f"), {"f": family_id})
    async with get_sessionmaker()() as session:
        assert len((await session.scalars(select(Consent).where(Consent.family_id == family_id))).all()) == 1


async def test_consents_cannot_be_truncated(require_db: None) -> None:
    with pytest.raises(DBAPIError, match="append-only"):
        async with get_engine().begin() as conn:
            await conn.execute(text("truncate consents"))


async def test_withdrawal_is_a_new_row(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    async with get_sessionmaker().begin() as session:
        session.add(consent(family_id, member_id, granted=True))
        await session.flush()
    async with get_sessionmaker().begin() as session:
        session.add(consent(family_id, member_id, granted=False))
    async with get_sessionmaker()() as session:
        rows = (
            await session.scalars(
                select(Consent.granted).where(Consent.family_id == family_id).order_by(Consent.recorded_at, Consent.id)
            )
        ).all()
    assert list(rows) == [True, False]


async def test_trusted_contact_and_action_token_constraints(world: tuple[UUID, UUID]) -> None:
    family_id, member_id = world
    async with get_sessionmaker().begin() as session:
        session.add(
            TrustedContact(family_id=family_id, member_id=member_id, phone_hmac=HEX64, phone_kid=1, last3="002")
        )
        session.add(
            ActionToken(
                member_id=member_id,
                token_hash="cd" * 32,
                scope="incident_decision",
                expires_at=text("now() + interval '1 hour'"),
            )
        )
    for bad in ({"phone_hmac": "ab" * 31}, {"phone_hmac": "zz" * 32}):
        with pytest.raises(IntegrityError):
            async with get_sessionmaker().begin() as session:
                session.add(
                    TrustedContact(
                        family_id=family_id, member_id=member_id, phone_kid=1, **{"phone_hmac": HEX64, **bad}
                    )
                )
    with pytest.raises(IntegrityError):  # scope lạ
        async with get_sessionmaker().begin() as session:
            session.add(ActionToken(member_id=member_id, token_hash="ef" * 32, scope="root", expires_at=text("now()")))
    with pytest.raises(IntegrityError):  # token_hash duy nhất
        async with get_sessionmaker().begin() as session:
            session.add(
                ActionToken(member_id=member_id, token_hash="cd" * 32, scope="guardian_view", expires_at=text("now()"))
            )


async def test_children_cascade_with_family_but_consents_are_restricted(world: tuple[UUID, UUID]) -> None:
    """Gia đình chưa có đồng ý thì xóa được và kéo theo thiết bị/liên hệ; (có đồng ý ⇒ bị chặn: test trên)."""
    async with get_sessionmaker().begin() as session:
        family = Family(display_name="test-0005-b", region="bac", is_demo=True)
        session.add(family)
        await session.flush()
        member = Member(family_id=family.id, role="protected")
        session.add(member)
        await session.flush()
        session.add(
            Device(
                family_id=family.id,
                member_id=member.id,
                app_version="1",
                rules_version="1",
                device_secret_hash=HEX64.replace("ab", "ba"),
            )
        )
        fid = family.id
    async with get_sessionmaker().begin() as session:
        await session.execute(text("delete from families where id = :f"), {"f": fid})
    async with get_sessionmaker()() as session:
        assert (await session.scalars(select(Device).where(Device.family_id == fid))).first() is None


async def test_consent_triggers_fire_even_when_replication_role_is_replica(require_db: None) -> None:
    """Review #5: `session_replication_role = replica` chỉ bỏ qua trigger ở chế độ ORIGIN; phải là ALWAYS."""
    async with get_engine().connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "select tgname, tgenabled from pg_trigger where tgrelid = 'consents'::regclass and not tgisinternal"
                )
            )
        ).all()
    assert {r.tgname: r.tgenabled for r in rows} == {"trg_consents_immutable": "A", "trg_consents_no_truncate": "A"}
