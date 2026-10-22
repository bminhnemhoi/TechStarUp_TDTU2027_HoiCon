"""Dữ liệu dùng chung cho test Coach (spec 032): gia đình THẬT (không demo) có thiết bị, hai người giám hộ, đồng ý
`guardian_alerts`, heartbeat tùy chỉnh. Mọi định danh hư cấu; dọn sạch sau test."""

import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

from consent_support import SHA, purge_family
from sqlalchemy import delete, text

from hoicon.db.models import (
    AgentRun,
    Consent,
    Device,
    DeviceHeartbeat,
    Family,
    Job,
    Member,
)
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate

# Thứ Ba 10:00 giờ VN: ngoài giờ im lặng.
NOW = datetime(2026, 10, 20, 3, 0, tzinfo=UTC)
SLOT = timedelta(minutes=15)


def vn_utc(hour: int, minute: int = 0, day: int = 20) -> datetime:
    """Giờ Việt Nam ⇒ UTC (UTC+7), tháng 10/2026."""
    return datetime(2026, 10, day, hour, minute, tzinfo=UTC) - timedelta(hours=7)


def chat_fields(with_chat: bool = True) -> dict[str, Any]:
    """Các cột Zalo đi cùng nhau (ràng buộc `zalo_all_or_none`); bản mã GIẢ, tài khoản duy nhất mỗi người."""
    if not with_chat:
        return {"zalo_bot_id": None, "zalo_user_hmac": None, "zalo_hmac_kid": None, "zalo_chat_enc": None}
    return {
        "zalo_bot_id": "bot-gia",
        "zalo_user_hmac": secrets.token_hex(32),
        "zalo_hmac_kid": 1,
        "zalo_chat_enc": "chat-enc-gia",
    }


async def seed_family(
    *,
    demo: bool = False,
    consent: bool = True,
    last_heartbeat: datetime | None = NOW - timedelta(minutes=5),
    protected_slots: list[bool] | None = None,
    revoked: bool = False,
    created_at: datetime | None = None,
    with_chat: bool = True,
    digest: tuple[bool, bool] = (True, True),
) -> SimpleNamespace:
    """`protected_slots`: các khung 15 phút GẦN NHẤT (cũ → mới), kết thúc ngay trước `last_heartbeat`."""
    consent_gate.reset_cache()
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=f"test-032-{secrets.token_hex(3)}", region="nam", is_demo=demo)
        session.add(family)
        await session.flush()
        g1 = Member(
            family_id=family.id,
            role="guardian",
            guardian_rank=1,
            weekly_digest_enabled=digest[0],
            **chat_fields(with_chat),
        )
        g2 = Member(
            family_id=family.id,
            role="guardian",
            guardian_rank=2,
            weekly_digest_enabled=digest[1],
            **chat_fields(with_chat),
        )
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add_all([g1, g2, protected])
        await session.flush()
        device = Device(
            family_id=family.id,
            member_id=protected.id,
            app_version="0.3.0",
            rules_version="r1",
            device_secret_hash=secrets.token_hex(32),
            last_heartbeat_at=last_heartbeat or NOW,
            revoked_at=NOW if revoked else None,
            created_at=created_at or NOW - timedelta(days=30),
        )
        session.add(device)
        await session.flush()
        if consent:
            for purpose in ("core_protection", "guardian_alerts"):
                session.add(
                    Consent(
                        family_id=family.id,
                        member_id=protected.id,
                        purpose=purpose,
                        granted=True,
                        consent_version="v1.0",
                        text_sha256=SHA,
                        channel="app",
                    )
                )
        end = (last_heartbeat or NOW).replace(second=0, microsecond=0)
        end -= timedelta(minutes=end.minute % 15)
        if last_heartbeat is not None:
            for i, ok in enumerate(reversed(protected_slots or [True])):
                session.add(DeviceHeartbeat(device_id=device.id, slot=end - SLOT * i, protected=ok))
        ids = SimpleNamespace(
            family=family.id, device=device.id, guardian1=g1.id, guardian2=g2.id, protected=protected.id
        )
    consent_gate.reset_cache()
    return ids


async def watch_jobs(world: SimpleNamespace, prefix: str = "protection") -> list[Job]:
    from sqlalchemy import select

    async with get_sessionmaker()() as session:
        return list(
            await session.scalars(
                select(Job)
                .where(Job.kind == "notify_guardian", Job.idempotency_key.like(f"{prefix}:%"))
                .where(Job.payload["family_id"].astext == str(world.family))
                .order_by(Job.created_at, Job.idempotency_key)
            )
        )


async def purge(world: SimpleNamespace) -> None:
    consent_gate.reset_cache()
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Job).where(Job.payload["family_id"].astext == str(world.family)))
        await session.execute(text("delete from agent_runs where thread_id like :p"), {"p": f"coach:{world.family}:%"})
    await purge_family(world.family)


async def count_runs(thread_prefix: str) -> int:
    from sqlalchemy import func, select

    async with get_sessionmaker()() as session:
        return int(
            await session.scalar(
                select(func.count()).select_from(AgentRun).where(AgentRun.thread_id.like(thread_prefix))
            )
        )


def payload_text(job: Job) -> str:
    payload: dict[str, Any] = job.payload
    return str(payload["text"])
