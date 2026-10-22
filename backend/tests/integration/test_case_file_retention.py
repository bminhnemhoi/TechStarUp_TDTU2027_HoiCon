"""Spec 031 FR-009 (SC-005): `case_files` đi theo sự cố (hạn 12 tháng) và theo xóa dữ liệu gia đình."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from case_support import purge_case, seed_case
from sqlalchemy import func, select

from hoicon.agents.runtime import open_checkpointer
from hoicon.config import get_settings
from hoicon.db.models import CaseFile
from hoicon.db.session import get_sessionmaker
from hoicon.services import case_file_service, purge_service, retention_service

pytestmark = pytest.mark.integration

CLOSED_AT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
async def world(require_db: None) -> AsyncIterator[SimpleNamespace]:
    w = await seed_case(with_run=False, state="closed", closed_at=CLOSED_AT)
    async with get_sessionmaker().begin() as session:
        content = await case_file_service.build_content(session, w.incident)
        session.add(CaseFile(incident_id=w.incident, family_id=w.family, content=content, is_demo=True))
    yield w
    await purge_case(w)


async def count(w: SimpleNamespace) -> int:
    async with get_sessionmaker()() as session:
        return int(
            await session.scalar(select(func.count()).select_from(CaseFile).where(CaseFile.family_id == w.family))
        )


async def test_the_incident_retention_selects_the_closed_incident_after_twelve_months(world: SimpleNamespace) -> None:
    """Xóa thật chỉ qua `ON DELETE CASCADE` (test_schema_0011). Ở đây chứng minh job 12 tháng chọn trúng sự cố có hồ sơ
    (dry-run, để khỏi xóa dữ liệu dùng chung của người khác trong DB dev)."""
    before = await retention_service.purge_incidents(
        get_sessionmaker(), now=CLOSED_AT + timedelta(days=364), dry_run=True
    )
    after = await retention_service.purge_incidents(
        get_sessionmaker(), now=CLOSED_AT + timedelta(days=366), dry_run=True
    )
    assert after >= before + 1
    assert await count(world) == 1


async def test_deleting_the_family_on_request_removes_the_case_file(world: SimpleNamespace) -> None:
    url = get_settings().database_url.get_secret_value()
    async with open_checkpointer(url) as saver:
        await purge_service.purge_family(get_sessionmaker(), saver.adelete_thread, world.family)
    assert await count(world) == 0
