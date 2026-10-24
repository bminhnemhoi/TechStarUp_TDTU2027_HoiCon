"""011 T024 #6/#8: đọc đồng ý theo lô — không N+1 ở danh sách web và báo cáo thí điểm."""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Family, Member
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration
SHA = "0" * 64


@contextmanager
def count_consent_queries() -> Iterator[list[str]]:
    seen: list[str] = []

    def before(conn, cursor, statement, params, context, executemany):  # type: ignore[no-untyped-def]
        if "FROM consents" in statement or "from consents" in statement:
            seen.append(statement)

    engine = get_engine().sync_engine
    event.listen(engine, "before_cursor_execute", before)
    try:
        yield seen
    finally:
        event.remove(engine, "before_cursor_execute", before)


@pytest.fixture
async def family(require_db: None) -> Iterator[dict]:
    from consent_support import purge_family

    consent_gate.reset_cache()
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name="test-011-t024", region="nam", is_demo=True)
        session.add(fam)
        await session.flush()
        members = [Member(family_id=fam.id, role="protected", alias=f"M{i}") for i in range(6)]
        session.add_all(members)
        await session.flush()
        ids = [m.id for m in members]
        # 4 người đồng ý guardian_alerts (một người rút sau đó), 2 người chưa có dòng nào
        for member_id in ids[:4]:
            session.add(
                Consent(
                    family_id=fam.id,
                    member_id=member_id,
                    purpose="guardian_alerts",
                    granted=True,
                    consent_version="v1.0",
                    text_sha256=SHA,
                    channel="app",
                )
            )
        session.add(
            Consent(
                family_id=fam.id,
                member_id=ids[3],
                purpose="guardian_alerts",
                granted=False,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
        fam_id = fam.id
    yield {"family": fam_id, "members": ids}
    consent_gate.reset_cache()
    await purge_family(fam_id)


async def test_web_readable_members_reads_consents_in_one_query(family: dict) -> None:
    async with get_sessionmaker()() as session:
        with count_consent_queries() as seen:
            readable = await consent_gate.web_readable_members(session, family["family"])
    assert len(seen) <= 1, f"N+1: {len(seen)} truy vấn consents"
    assert set(readable) == set(family["members"][:3])  # người rút và người chưa đồng ý bị loại


async def test_states_for_returns_the_same_state_as_state_for_and_uses_the_cache(family: dict) -> None:
    async with get_sessionmaker()() as session:
        batch = await consent_gate.states_for(session, family["members"])
        consent_gate.reset_cache()
        for member in family["members"]:
            assert batch[member] == await consent_gate.state_for(session, member)
        consent_gate.reset_cache()
        await consent_gate.states_for(session, family["members"])
        with count_consent_queries() as seen:
            again = await consent_gate.states_for(session, family["members"])  # lần hai: toàn bộ từ đệm
    assert seen == [] and again == batch


async def test_states_for_unknown_member_is_closed_by_default(family: dict) -> None:
    async with get_sessionmaker()() as session:
        stranger = new_id()
        result = await consent_gate.states_for(session, [stranger])
    assert result[stranger] == consent_gate.ConsentState(False, False, False, False)
