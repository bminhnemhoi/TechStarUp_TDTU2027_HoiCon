import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import delete, text

from hoicon.db.models import AgentRun, Job
from hoicon.db.session import get_engine, get_sessionmaker


async def db_up() -> bool:
    # Chặn thêm một lớp: kể cả khi driver không tôn trọng connect_timeout, test không bao giờ treo.
    try:
        async with asyncio.timeout(8):
            async with get_engine().connect() as conn:
                await conn.execute(text("select 1"))
    except Exception:
        return False
    return True


@pytest.fixture
async def require_db() -> None:
    if not await db_up():
        pytest.skip("Postgres dev chưa chạy (docker compose -f infra/compose.dev.yml up -d)")


@pytest.fixture
async def threads(require_db: None) -> AsyncGenerator[list[str]]:
    """Thread id do test tạo; dọn job + agent_runs (+ steps) sau test để `recover()` của test khác không vướng."""
    created: list[str] = []
    yield created
    async with get_sessionmaker().begin() as session:
        for thread in created:
            await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{thread}:", autoescape=True)))
            await session.execute(delete(AgentRun).where(AgentRun.thread_id == thread))
