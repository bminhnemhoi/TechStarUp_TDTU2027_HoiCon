"""Kiểm thử tích hợp cho ActionTokenService (Spec 023, FR-002, SC-003)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from consent_support import purge_family

from hoicon.db.ids import new_id
from hoicon.db.models import ActionToken, Family, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services.action_token_service import (
    ActionTokenService,
    TokenExpiredError,
    TokenNotFoundError,
    TokenUsedError,
    hash_token,
)

pytestmark = pytest.mark.integration


@pytest.fixture
async def sample_incident(require_db: None) -> tuple[UUID, UUID, UUID]:
    """Tạo Family, Member, Incident mẫu để gắn ActionToken."""
    family_id = new_id()
    member_id = new_id()
    incident_id = new_id()

    async with get_sessionmaker().begin() as session:
        family = Family(id=family_id, display_name="Gia đình Test", region="nam")
        session.add(family)
        await session.flush()
        member = Member(
            id=member_id,
            family_id=family_id,
            role="protected",
            alias="Mẹ",
        )
        session.add(member)
        await session.flush()
        incident = Incident(
            id=incident_id,
            family_id=family_id,
            member_id=member_id,
            device_id=None,
            state="awaiting_guardian",
            level="high",
            rule_floor="high",
            version=1,
            is_drill=False,
            opened_by_event_id=None,
        )
        session.add(incident)

    yield family_id, member_id, incident_id

    await purge_family(family_id)


async def test_create_token_stores_sha256_hash_never_raw_token(sample_incident: tuple[UUID, UUID, UUID]) -> None:
    _family_id, member_id, incident_id = sample_incident

    async with get_sessionmaker().begin() as session:
        record, raw_token = await ActionTokenService.create_token(
            session,
            incident_id=incident_id,
            member_id=member_id,
            scope="incident_decision",
        )
        token_id = record.id

    assert len(raw_token) >= 32
    expected_hash = hash_token(raw_token)
    assert record.token_hash == expected_hash
    assert record.used_at is None
    assert record.expires_at > datetime.now(UTC)

    # Đọc lại từ DB kiểm tra tuyệt đối không lưu raw token
    async with get_sessionmaker()() as session:
        db_record = await session.get(ActionToken, token_id)
        assert db_record is not None
        assert db_record.token_hash == expected_hash
        assert raw_token not in db_record.token_hash


async def test_verify_and_consume_token_lifecycle(sample_incident: tuple[UUID, UUID, UUID]) -> None:
    _family_id, member_id, incident_id = sample_incident

    async with get_sessionmaker().begin() as session:
        _, raw_token = await ActionTokenService.create_token(
            session,
            incident_id=incident_id,
            member_id=member_id,
        )

    # Verify hợp lệ
    async with get_sessionmaker().begin() as session:
        verified = await ActionTokenService.verify_token(session, raw_token)
        assert verified.incident_id == incident_id
        assert verified.used_at is None

    # Consume thành công
    async with get_sessionmaker().begin() as session:
        consumed = await ActionTokenService.consume_token(session, raw_token)
        assert consumed.used_at is not None

    # Consume hoặc Verify lần 2 ⇒ Bị từ chối TokenUsedError (chống dùng lại)
    async with get_sessionmaker().begin() as session:
        with pytest.raises(TokenUsedError):
            await ActionTokenService.verify_token(session, raw_token)

        with pytest.raises(TokenUsedError):
            await ActionTokenService.consume_token(session, raw_token)


async def test_verify_token_expired_rejected(sample_incident: tuple[UUID, UUID, UUID]) -> None:
    _family_id, member_id, incident_id = sample_incident

    # Tạo token đã hết hạn (TTL âm)
    async with get_sessionmaker().begin() as session:
        _, raw_token = await ActionTokenService.create_token(
            session,
            incident_id=incident_id,
            member_id=member_id,
            ttl=-timedelta(minutes=5),
        )

    async with get_sessionmaker().begin() as session:
        with pytest.raises(TokenExpiredError):
            await ActionTokenService.verify_token(session, raw_token)


async def test_verify_token_not_found_rejected(require_db: None) -> None:
    fake_token = ActionTokenService.generate_raw_token()
    async with get_sessionmaker().begin() as session:
        with pytest.raises(TokenNotFoundError):
            await ActionTokenService.verify_token(session, fake_token)


async def test_action_view_data_format(sample_incident: tuple[UUID, UUID, UUID]) -> None:
    _family_id, member_id, incident_id = sample_incident

    async with get_sessionmaker().begin() as session:
        _, raw_token = await ActionTokenService.create_token(
            session,
            incident_id=incident_id,
            member_id=member_id,
        )

    async with get_sessionmaker()() as session:
        view = await ActionTokenService.get_action_view_data(session, raw_token)
        assert view is not None
        assert view["token_valid"] is True
        assert view["scope"] == "incident_decision"
        assert view["incident"]["id"] == str(incident_id)
        assert view["incident"]["state"] == "awaiting_guardian"
        assert view["incident"]["level"] == "high"
        assert "cuộc gọi lạ" in view["incident"]["summary_text"].lower()
        assert view["incident"]["protected_member_label"] == "Mẹ"


async def test_a_guardian_view_token_bound_to_an_incident_does_not_open_the_action_page(
    sample_incident: tuple[UUID, UUID, UUID],
) -> None:
    """Rà soát 037 T009 #8: trang hành động chỉ nhận token `incident_decision`."""
    _family_id, member_id, incident_id = sample_incident
    async with get_sessionmaker().begin() as session:
        _, view_token = await ActionTokenService.create_token(
            session, incident_id=incident_id, member_id=member_id, scope="guardian_view"
        )
        _, decision_token = await ActionTokenService.create_token(session, incident_id=incident_id, member_id=member_id)
    async with get_sessionmaker()() as session:
        assert await ActionTokenService.get_action_view_data(session, view_token) is None
        assert await ActionTokenService.get_action_view_data(session, decision_token) is not None
