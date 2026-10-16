import asyncio
import secrets
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, func, select, text

from hoicon.config import Settings, get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, Family, Incident, Job, Member, MessageOut, PairingCode
from hoicon.db.session import get_engine, get_sessionmaker
from hoicon.domain.pii import encrypt_chat_id, hmac_h1, hmac_pairing_code, hmac_zalo


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


@pytest.fixture(scope="module")
async def target() -> tuple[str, bool]:
    """(URL DB eval, shared_db_ok) của spec 030; skip nếu DB eval chưa chạy/chưa migrate."""
    from eval_support import eval_target
    from sqlalchemy.ext.asyncio import create_async_engine

    url, shared = eval_target()
    engine = create_async_engine(url, connect_args={"connect_timeout": 5})
    try:
        async with asyncio.timeout(8), engine.connect() as conn:
            await conn.exec_driver_sql("select 1")
    except Exception:
        pytest.skip("DB eval chưa chạy/chưa migrate (xem specs/030-eval-smoke/quickstart.md)")
    finally:
        await engine.dispose()
    return url, shared


@pytest.fixture
async def threads(require_db: None) -> AsyncGenerator[list[str]]:
    """Thread id do test tạo; dọn job + agent_runs (+ steps) sau test để `recover()` của test khác không vướng."""
    created: list[str] = []
    yield created
    async with get_sessionmaker().begin() as session:
        for thread in created:
            await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{thread}:", autoescape=True)))
            await session.execute(delete(AgentRun).where(AgentRun.thread_id == thread))


# --- Kênh Zalo (spec 002) -------------------------------------------------------------------------------------------


@pytest.fixture
def zalo_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Khóa GIẢ cho test (không phụ thuộc tệp bí mật của máy): pepper + khóa dữ liệu; xóa cache cấu hình quanh test."""
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    monkeypatch.setenv("HOICON_DATA_KEY_1", "aa" * 32)
    yield
    get_settings.cache_clear()


@pytest.fixture
def service_keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Đủ ba khóa mà `/readyz` đòi (spec 034): pepper, khóa dữ liệu, khóa JWT thiết bị. Chuỗi GIẢ, công khai."""
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    monkeypatch.setenv("HOICON_DATA_KEY_1", "aa" * 32)
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "integration-test-key-" + "k" * 32)  # gitleaks:allow
    yield
    get_settings.cache_clear()


@dataclass
class ZaloWorld:
    """Một bot + một gia đình demo + các người giám hộ đã ghép, trên Postgres thật; dọn sạch sau test."""

    bot_id: str
    settings: Settings
    client: Any
    deps: Any  # ChannelDeps
    family: Family
    guardians: dict[int, Member] = field(default_factory=dict)
    zalo_ids: dict[int, tuple[str, str]] = field(default_factory=dict)  # hạng → (user_id, chat_id) HƯ CẤU
    incidents: list[str] = field(default_factory=list)
    protected_id: Any = None  # thành viên được bảo vệ, tạo khi cần cho sự cố

    def new_incident(self) -> str:
        """Sự cố THẬT trong DB (spec 021: `messages_out.incident_id` có FK). Đồng bộ để giữ nguyên chỗ gọi cũ ⇒ dùng
        engine đồng bộ riêng, không đụng vòng lặp sự kiện của test."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        incident = new_id()
        engine = create_engine(get_settings().database_url.get_secret_value(), pool_pre_ping=False)
        try:
            with Session(engine) as session, session.begin():
                if self.protected_id is None:
                    member = Member(family_id=self.family.id, role="protected")
                    session.add(member)
                    session.flush()
                    self.protected_id = member.id
                session.add(
                    Incident(
                        id=incident,
                        family_id=self.family.id,
                        member_id=self.protected_id,
                        level="high",
                        rule_floor="high",
                        is_demo=True,
                    )
                )
        finally:
            engine.dispose()
        self.incidents.append(str(incident))
        return str(incident)

    async def add_guardian(self, rank: int) -> Member:
        user_id, chat_id = f"fixture-user-{rank}-{new_id().hex[:8]}", f"fixture-chat-{rank}-{new_id().hex[:8]}"
        kid, user_hmac = hmac_zalo(self.bot_id, user_id)
        member = Member(
            family_id=self.family.id,
            role="guardian",
            guardian_rank=rank,
            zalo_bot_id=self.bot_id,
            zalo_user_hmac=user_hmac,
            zalo_hmac_kid=kid,
            zalo_chat_enc=encrypt_chat_id(chat_id, user_hmac),
        )
        async with get_sessionmaker().begin() as session:
            session.add(member)
        self.guardians[rank], self.zalo_ids[rank] = member, (user_id, chat_id)
        return member

    def update_payload(
        self, user_id: str, *, kind: str, value: str | None = None, message_id: str | None = None
    ) -> dict[str, Any]:
        """Job `zalo_update` y như webhook xếp (chat_id của người lạ = `chat-of-<user_id>`, HƯ CẤU)."""
        kid, user_hmac = hmac_zalo(self.bot_id, user_id)
        payload: dict[str, Any] = {
            "bot_id": self.bot_id,
            "message_id": message_id or f"fixture-msg-{new_id().hex[:12]}",
            "user_hmac": user_hmac,
            "hmac_kid": kid,
            "chat_enc": encrypt_chat_id(f"chat-of-{user_id}", user_hmac),
            "kind": kind,
        }
        if kind == "start" and value:
            payload["code_hash"] = hmac_pairing_code(value)
        if kind == "choice":
            payload["choice"] = value
        return payload

    async def make_code(
        self, *, expires_in: timedelta = timedelta(minutes=15), used: bool = False, family: Family | None = None
    ) -> str:
        code = f"{secrets.randbelow(10**6):06d}"
        async with get_sessionmaker().begin() as session:
            session.add(
                PairingCode(
                    family_id=(family or self.family).id,
                    code_hash=hmac_pairing_code(code),
                    expires_at=func.now() + expires_in,
                    used_at=func.now() if used else None,
                )
            )
        return code

    def sent_to(self, user_id: str) -> list[str]:
        """Văn bản mock đã gửi cho người lạ (chat_id = `chat-of-<user_id>`)."""
        return [m.text for m in self.client.sent if m.chat_id == f"chat-of-{user_id}"]

    async def members(self) -> list[Member]:
        async with get_sessionmaker()() as session:
            return list(await session.scalars(select(Member).where(Member.zalo_bot_id == self.bot_id)))

    async def rows(self) -> list[MessageOut]:
        async with get_sessionmaker()() as session:
            query = select(MessageOut).where(MessageOut.bot_id == self.bot_id).order_by(MessageOut.created_at)
            return list(await session.scalars(query))


@pytest.fixture
async def zalo_world(require_db: None, zalo_env: None) -> AsyncGenerator[ZaloWorld]:
    from hoicon.channels.guardian import ChannelDeps
    from hoicon.channels.zalo import MockZaloClient

    bot_id = f"test-{new_id().hex[:12]}"
    # Hạn mức nhỏ để test ngưỡng 80%/95% chỉ cần vài dòng: 20 ⇒ cảnh báo ở 16, giữ tin không khẩn ở 19.
    settings = get_settings().model_copy(update={"zalo_bot_id": bot_id, "zalo_monthly_quota": 20})
    family = Family(display_name="Gia đình mẫu", region="nam", is_demo=True)
    async with get_sessionmaker().begin() as session:
        session.add(family)
    client = MockZaloClient()
    world = ZaloWorld(bot_id, settings, client, ChannelDeps(get_sessionmaker(), client, settings), family)
    yield world
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(MessageOut).where(MessageOut.bot_id == bot_id))
        await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"zalo:{bot_id}:", autoescape=True)))
        for incident in world.incidents:
            await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{incident}:", autoescape=True)))
        await session.execute(delete(Incident).where(Incident.family_id == family.id))
        await session.execute(delete(Member).where(Member.zalo_bot_id == bot_id))
        if world.protected_id is not None:
            await session.execute(delete(Member).where(Member.id == world.protected_id))
        await session.execute(delete(Family).where(Family.id == family.id))


# --- Danh sách đe dọa (spec 003) ------------------------------------------------------------------------------------


DEMO_SEED = Path(__file__).resolve().parents[3] / "data" / "threat_seed.demo.json"


@pytest.fixture
def fake_pepper(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Khóa băm GIẢ cho test (không phụ thuộc tệp bí mật của máy); xóa cache cấu hình quanh test."""
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "1")
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_data_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Khóa mã hóa dữ liệu GIẢ (`bucket_enc`, `zalo_chat_enc`) cho test; xóa cache cấu hình quanh test."""
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DATA_KEY_KID", "1")
    monkeypatch.setenv("HOICON_DATA_KEY_1", "aa" * 32)
    yield
    get_settings.cache_clear()


@pytest.fixture
async def seeded_threat(require_db: None, fake_pepper: None, fake_data_key: None) -> AsyncGenerator[dict[str, Any]]:
    """Danh sách đe dọa DEMO (số hư cấu) trong DB ứng dụng, băm bằng khóa GIẢ; xóa đúng các dòng đó khi xong."""
    import json

    from hoicon.db.models import ThreatIndicator
    from hoicon.ops.threat_list import load_seed

    doc = json.loads(await asyncio.to_thread(DEMO_SEED.read_text, "utf-8"))
    await load_seed(get_sessionmaker(), doc, env="dev")
    # Chỉ xóa đúng các dòng HMAC theo khóa GIẢ: dòng demo nạp bằng khóa thật của máy dev (cùng list_version) phải còn.
    mine = [hmac_h1(item["h1"]) for item in doc["indicators"]]
    yield doc
    async with get_sessionmaker().begin() as session:
        for kid, digest in mine:
            await session.execute(
                delete(ThreatIndicator).where(ThreatIndicator.value_kid == kid, ThreatIndicator.value_hmac == digest)
            )


# --- Ghép đôi thiết bị & sổ đồng ý (spec 020) -----------------------------------------------------------------------


@dataclass
class DeviceWorld:
    """Một gia đình demo + một mã ghép còn hạn, trên Postgres thật; khóa JWT/pepper GIẢ; dọn sạch sau test."""

    family_id: Any
    display_name: str
    code: str

    async def new_code(self) -> str:
        from hoicon.ops.pairing_code import create_pairing_code

        return await create_pairing_code(get_sessionmaker(), self.family_id)


@pytest.fixture
async def device_world(require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[DeviceWorld]:
    from consent_support import purge_family

    from hoicon.api.routers import pairing
    from hoicon.ops.pairing_code import create_pairing_code

    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", "11" * 32)
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "integration-test-key-" + "k" * 32)  # gitleaks:allow
    pairing.reset_limits()
    name = f"test-020-{secrets.token_hex(4)}"
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=name, region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        family_id = family.id
    code = await create_pairing_code(get_sessionmaker(), family_id)
    yield DeviceWorld(family_id, name, code)
    await purge_family(family_id)
    pairing.reset_limits()
    get_settings.cache_clear()


@pytest.fixture
async def trace_world(require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[dict[str, Any]]:
    """Hai gia đình demo, mỗi nhà một người giám hộ; một sự cố + một lượt `done` có 4 bước "đầu độc" ở nhà thứ nhất."""
    from consent_support import purge_family
    from trace_support import AT, JWT_KEY, add_run

    from hoicon.api.auth import issue_guardian_access_token
    from hoicon.services import trace_service

    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()
    trace_service._reset_slots()
    ids: dict[str, Any] = {"runs": []}
    async with get_sessionmaker().begin() as session:
        for tag in ("a", "b"):
            family = Family(display_name=f"Gia đình mẫu 025{tag}", region="nam", is_demo=True)
            session.add(family)
            await session.flush()
            protected = Member(family_id=family.id, role="protected", alias="Mẹ")
            guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
            session.add_all([protected, guardian])
            await session.flush()
            incident = Incident(
                family_id=family.id, member_id=protected.id, state="resolved_safe", level="high", rule_floor="high",
                is_demo=True, outcome="safe", closed_at=AT,
            )  # fmt: skip
            session.add(incident)
            await session.flush()
            ids[tag] = {"family": family.id, "guardian": guardian.id, "incident": incident.id}
    ids["a"]["run"] = await add_run(ids["a"]["incident"], ids)
    ids["a"]["token"] = issue_guardian_access_token(ids["a"]["guardian"], ids["a"]["family"])
    ids["b"]["token"] = issue_guardian_access_token(ids["b"]["guardian"], ids["b"]["family"])
    yield ids
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(AgentRun).where(AgentRun.id.in_(ids["runs"])))
    for tag in ("a", "b"):
        await purge_family(ids[tag]["family"])
    trace_service._reset_slots()
    get_settings.cache_clear()
