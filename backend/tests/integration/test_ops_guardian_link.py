"""Spec 027 T019: công cụ dev sinh liên kết đăng nhập + dựng/dọn dữ liệu cho E2E; chỉ chạy ở dev, chỉ gia đình demo."""

import argparse
import re
from uuid import UUID

import pytest
from consent_support import call
from sqlalchemy import func, select

from hoicon.config import get_settings
from hoicon.db.models import ActionToken, AgentRun, AgentStep, Family, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.ops import guardian_link
from hoicon.services.action_token_service import hash_token

pytestmark = pytest.mark.integration

JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Origin": "http://localhost:3100"}


@pytest.fixture
def dev_env(require_db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOICON_ENV", "dev")
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()


async def test_seed_link_step_and_cleanup_round_trip(dev_env: None) -> None:
    sessions = get_sessionmaker()
    ids = await guardian_link.seed(sessions)
    family_id = UUID(ids["family_id"])
    try:
        match = re.fullmatch(r"http://localhost:3100/login/([A-Za-z0-9_-]{43})", ids["login_url"])
        assert match is not None
        raw = match.group(1)
        async with sessions() as session:
            token = await session.scalar(select(ActionToken).where(ActionToken.token_hash == hash_token(raw)))
            assert token is not None and token.scope == "guardian_view" and token.incident_id is None
            assert str(token.member_id) == ids["guardian_id"]
        # Liên kết dùng được thật với API phiên.
        res = await call("POST", "/v1/guardian/session", json={"token": raw}, headers=ORIGIN)
        assert res.status_code == 200 and res.json()["family_id"] == ids["family_id"]

        added = await guardian_link.add_step(sessions, UUID(ids["run_id"]), "verify")
        assert added is not None and added["at"]
        async with sessions() as session:
            nodes = list(await session.scalars(select(AgentStep.node).where(AgentStep.run_id == UUID(ids["run_id"]))))
        assert sorted(nodes) == ["ingest", "verify"]
    finally:
        assert await guardian_link.cleanup(sessions, family_id) is True
    async with sessions() as session:
        assert await session.get(Family, family_id) is None
        assert (
            await session.scalar(select(func.count()).select_from(AgentRun).where(AgentRun.id == UUID(ids["run_id"])))
            == 0
        )
        assert (
            await session.scalar(select(func.count()).select_from(Incident).where(Incident.family_id == family_id)) == 0
        )


async def test_it_never_touches_a_real_family(dev_env: None) -> None:
    sessions = get_sessionmaker()
    async with sessions.begin() as session:
        family = Family(display_name="Nhà thật 027", region="nam", is_demo=False)
        session.add(family)
        await session.flush()
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        session.add(guardian)
        await session.flush()
        family_id, guardian_id = family.id, guardian.id
    try:
        assert await guardian_link.make_link(sessions, guardian_id) is None
        assert await guardian_link.cleanup(sessions, family_id) is False
    finally:
        async with sessions.begin() as session:
            await session.delete(await session.get(Family, family_id))


@pytest.mark.parametrize("env", ["prod", "production", "staging", ""])
async def test_refuses_outside_dev(
    require_db: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], env: str
) -> None:
    monkeypatch.setenv("HOICON_ENV", env)
    get_settings.cache_clear()
    args = argparse.Namespace(member=None, seed=True, add_step=None, cleanup=None, base_url="http://x", node="n")
    try:
        assert await guardian_link.run(args) == 2
    finally:
        get_settings.cache_clear()
    out = capsys.readouterr().out
    assert "Từ chối" in out and "login" not in out  # không dựng dữ liệu, không in liên kết
