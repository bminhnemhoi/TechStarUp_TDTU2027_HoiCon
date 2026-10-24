"""Hạn lưu dữ liệu (spec 034 FR-002, SC-001): thực thi những gì `docs/DATA-MODEL.md` §6 đã cam kết. KHÔNG gọi LLM.

Mỗi loại là một hàm riêng nhận `now` (test lùi thời gian không cần chờ), xử lý theo lô tối đa `BATCH` dòng, mỗi lô một
giao dịch (không khóa bảng lâu), lũy đẳng (chạy lại không đổi gì). `dry_run=True` chỉ đếm số dòng sẽ bị đụng, không ghi.
Chỉ log số dòng theo loại, không bao giờ log nội dung.

`consents` KHÔNG BAO GIỜ bị đụng ở đây (bằng chứng đồng ý, Nghị định 356/2025). `messages_out` không có cột văn bản:
toàn văn tin gửi người giám hộ nằm trong `jobs.payload` và bị xóa cùng `jobs` sau 30 ngày; dòng `messages_out` được
giữ để đếm hạn mức Zalo theo tháng.

Checkpoint LangGraph xóa qua `adelete_thread` (kết nối riêng của bộ lưu checkpoint, nên ngoài giao dịch SQLAlchemy).
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Delete, Update, delete, func, null, or_, select, text, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.db.models import (
    ActionToken,
    AgentRun,
    AgentStep,
    Device,
    DeviceHeartbeat,
    Drill,
    Incident,
    Job,
    RiskEventRecord,
    Verification,
)
from hoicon.jobs.queue import enqueue

logger = logging.getLogger(__name__)

BATCH = 1000
VN_TZ = timezone(timedelta(hours=7))  # Việt Nam không có giờ mùa hè

# MỘT chỗ duy nhất giữ hạn lưu. `tests/integration/test_retention.py` so khớp với bảng §6 của DATA-MODEL.md.
RETENTION: dict[str, timedelta] = {
    "risk_events": timedelta(days=90),  # từ `received_at`
    "agent_steps_content": timedelta(days=30),  # làm rỗng `input_redacted`/`output`, giữ số đo
    "incidents": timedelta(days=365),  # "12 tháng" từ `closed_at`; CASCADE nhật ký chuyển, xác minh, token
    "checkpoints": timedelta(days=7),  # sau `closed_at` của sự cố
    "jobs": timedelta(days=30),  # sau `done_at`
    "action_tokens": timedelta(days=30),  # sau `expires_at`
    "verifications": timedelta(days=90),  # từ `at`
    "drills": timedelta(days=365),  # "12 tháng" từ `created_at`
    "device_heartbeats": timedelta(days=90),  # từ `slot` (spec 029)
}

# Thiết bị demo của /sim (spec 033 D9) sống ngắn hơn dữ liệu thật: không nằm trong RETENTION (bảng §6).
SIM_DEVICE_TTL = timedelta(hours=24)
SIM_LABEL_PREFIX = "sim:"  # trùng `sim_service.SIM_LABEL_PREFIX` (có test); không import vì sim_service kéo cả router

DeleteThread = Callable[[str], Awaitable[None]]


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


async def _run_batches(sessions: async_sessionmaker, build: Callable[[int], Delete | Update], dry: Any) -> int:
    """Chạy `build(BATCH)` lặp lại, mỗi lô một giao dịch, tới khi một lô không đầy. `dry` là câu đếm cho --dry-run."""
    if dry is not None:
        async with sessions() as session:
            return await session.scalar(dry) or 0
    total = 0
    while True:
        async with sessions.begin() as session:
            done = (await session.execute(build(BATCH))).rowcount
        total += done
        if done < BATCH:
            return total


async def _table_exists(session: AsyncSession, name: str) -> bool:
    return (await session.scalar(text("select to_regclass(:n) is not null"), {"n": f"public.{name}"})) is True


async def purge_risk_events(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    cutoff = now - RETENTION["risk_events"]
    where = RiskEventRecord.received_at < cutoff

    def build(n: int) -> Delete:
        return delete(RiskEventRecord).where(RiskEventRecord.id.in_(select(RiskEventRecord.id).where(where).limit(n)))

    dry = select(func.count()).select_from(RiskEventRecord).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def blank_agent_steps(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    """Làm rỗng nội dung (không xóa dòng): giữ `latency`, `tokens`, `cost` cho báo cáo chi phí."""
    cutoff = now - RETENTION["agent_steps_content"]
    where = (AgentStep.at < cutoff) & or_(AgentStep.input_redacted.is_not(None), AgentStep.output.is_not(None))

    def build(n: int) -> Update:
        return (
            update(AgentStep)
            .where(AgentStep.id.in_(select(AgentStep.id).where(where).limit(n)))
            .values(input_redacted=null(), output=null())
        )

    dry = select(func.count()).select_from(AgentStep).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def purge_checkpoints(
    sessions: async_sessionmaker, delete_thread: DeleteThread, *, now: datetime, dry_run: bool = False
) -> int:
    """Checkpoint của sự cố đã đóng quá 7 ngày. `agent_steps` đủ cho trace nên đồ thị không cần checkpoint nữa."""
    cutoff = now - RETENTION["checkpoints"]
    has_checkpoint = text("EXISTS (SELECT 1 FROM checkpoints c WHERE c.thread_id = incidents.id::text)")
    where = (Incident.closed_at < cutoff) & has_checkpoint
    if dry_run:
        async with sessions() as session:
            return await session.scalar(select(func.count()).select_from(Incident).where(where)) or 0
    total = 0
    while True:
        async with sessions() as session:
            ids = list(await session.scalars(select(Incident.id).where(where).limit(BATCH)))
        for incident_id in ids:
            await delete_thread(str(incident_id))
        total += len(ids)
        if len(ids) < BATCH:
            return total


async def purge_incidents(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    """Sự cố đã đóng quá 12 tháng. CASCADE: nhật ký chuyển, xác minh, action token; `risk_events.incident_id` SET NULL.
    `agent_runs` không có khóa ngoại tới sự cố nên xóa tường minh (CASCADE sang `agent_steps`)."""
    cutoff = now - RETENTION["incidents"]
    where = Incident.closed_at < cutoff
    if dry_run:
        async with sessions() as session:
            return await session.scalar(select(func.count()).select_from(Incident).where(where)) or 0
    total = 0
    while True:
        async with sessions.begin() as session:
            ids = list(await session.scalars(select(Incident.id).where(where).limit(BATCH)))
            if ids:
                threads = [
                    str(i) for i in ids
                ]  # đồ thị thật khóa theo `thread_id` (= id sự cố); `incident_id` có thể NULL
                await session.execute(
                    delete(AgentRun).where(or_(AgentRun.incident_id.in_(ids), AgentRun.thread_id.in_(threads)))
                )
                await session.execute(delete(Incident).where(Incident.id.in_(ids)))
        total += len(ids)
        if len(ids) < BATCH:
            return total


async def purge_jobs(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    """`jobs` đã xong quá 30 ngày (payload chứa toàn văn tin gửi người giám hộ)."""
    where = Job.done_at < now - RETENTION["jobs"]

    def build(n: int) -> Delete:
        return delete(Job).where(Job.id.in_(select(Job.id).where(where).limit(n)))

    return await _run_batches(sessions, build, select(func.count()).select_from(Job).where(where) if dry_run else None)


async def purge_action_tokens(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    where = ActionToken.expires_at < now - RETENTION["action_tokens"]

    def build(n: int) -> Delete:
        return delete(ActionToken).where(ActionToken.id.in_(select(ActionToken.id).where(where).limit(n)))

    dry = select(func.count()).select_from(ActionToken).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def purge_verifications(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    where = Verification.at < now - RETENTION["verifications"]

    def build(n: int) -> Delete:
        return delete(Verification).where(Verification.id.in_(select(Verification.id).where(where).limit(n)))

    dry = select(func.count()).select_from(Verification).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def purge_drills(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    where = Drill.created_at < now - RETENTION["drills"]

    def build(n: int) -> Delete:
        return delete(Drill).where(Drill.id.in_(select(Drill.id).where(where).limit(n)))

    dry = select(func.count()).select_from(Drill).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def purge_device_heartbeats(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    where = DeviceHeartbeat.slot < now - RETENTION["device_heartbeats"]

    def build(n: int) -> Delete:
        keys = select(DeviceHeartbeat.device_id, DeviceHeartbeat.slot).where(where).limit(n)
        return delete(DeviceHeartbeat).where(tuple_(DeviceHeartbeat.device_id, DeviceHeartbeat.slot).in_(keys))

    dry = select(func.count()).select_from(DeviceHeartbeat).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def purge_sim_devices(sessions: async_sessionmaker, *, now: datetime, dry_run: bool = False) -> int:
    """Thiết bị `sim:` quá 24 giờ mà mọi sự cố của nó đã đóng quá 24 giờ (không sự cố ⇒ theo tuổi thiết bị).
    Sự cố KHÔNG bị xóa (`incidents.device_id` SET NULL, hạn lưu sự cố giữ nguyên) nên lượt cũ không còn là sim."""
    cutoff = now - SIM_DEVICE_TTL
    still_live = (
        select(Incident.id)
        .where(Incident.device_id == Device.id)
        .where(or_(Incident.closed_at.is_(None), Incident.closed_at >= cutoff))
        .exists()
    )
    where = Device.label.startswith(SIM_LABEL_PREFIX, autoescape=True) & (Device.created_at < cutoff) & ~still_live

    def build(n: int) -> Delete:
        return delete(Device).where(Device.id.in_(select(Device.id).where(where).limit(n)))

    dry = select(func.count()).select_from(Device).where(where) if dry_run else None
    return await _run_batches(sessions, build, dry)


async def run_retention(
    sessions: async_sessionmaker,
    delete_thread: DeleteThread | None,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Chạy mọi loại, theo thứ tự an toàn (checkpoint trước sự cố, vì cần `incidents` để biết thread). `delete_thread`
    rỗng (không có kết nối checkpoint) ⇒ bỏ qua checkpoint và báo -1 cho loại đó, không âm thầm coi là đã xong."""
    moment = _now(now)
    report: dict[str, int] = {}
    report["risk_events"] = await purge_risk_events(sessions, now=moment, dry_run=dry_run)
    report["agent_steps_content"] = await blank_agent_steps(sessions, now=moment, dry_run=dry_run)
    if delete_thread is None and not dry_run:
        report["checkpoints"] = -1
    else:
        report["checkpoints"] = await purge_checkpoints(
            sessions, delete_thread or _no_delete, now=moment, dry_run=dry_run
        )
    report["incidents"] = await purge_incidents(sessions, now=moment, dry_run=dry_run)
    report["jobs"] = await purge_jobs(sessions, now=moment, dry_run=dry_run)
    report["action_tokens"] = await purge_action_tokens(sessions, now=moment, dry_run=dry_run)
    report["device_heartbeats"] = await purge_device_heartbeats(sessions, now=moment, dry_run=dry_run)
    report["sim_devices"] = await purge_sim_devices(sessions, now=moment, dry_run=dry_run)
    async with sessions() as session:
        has_verifications = await _table_exists(session, "verifications")
        has_drills = await _table_exists(session, "drills")
    if has_verifications:
        report["verifications"] = await purge_verifications(sessions, now=moment, dry_run=dry_run)
    if has_drills:
        report["drills"] = await purge_drills(sessions, now=moment, dry_run=dry_run)
    verb = "sẽ xử lý" if dry_run else "đã xử lý"
    logger.info("retention %s: %s", verb, ", ".join(f"{kind}={count}" for kind, count in report.items()))
    return report


async def _no_delete(_: str) -> None:  # dry-run không bao giờ gọi tới
    raise RuntimeError("dry-run không được xóa checkpoint")


def retention_key(now: datetime) -> str:
    """Khóa job hằng ngày theo ngày giờ Việt Nam: nhiều worker/lần khởi động trong một ngày chỉ xếp một job."""
    return f"retention:{now.astimezone(VN_TZ).date().isoformat()}"


async def schedule_daily(sessions: async_sessionmaker, *, now: datetime | None = None) -> str:
    """Xếp job `retention` của ngày hôm nay (lũy đẳng nhờ khóa) ⇒ khóa job."""
    key = retention_key(_now(now))
    await enqueue(sessions, "retention", {}, key=key)
    return key
