"""Coach hằng tuần + báo "mất bảo vệ" (spec 032, plan D1): hai job, KHÔNG LangGraph, không LLM.

- `protection_watch` mỗi giờ: thiết bị của gia đình thật, người cao tuổi còn đồng ý `guardian_alerts`, mà (a) `silent`:
  heartbeat cuối cũ hơn 24 giờ, hoặc (b) `permission_off`: 2 khung heartbeat gần nhất đều `protected = false`. Mỗi ĐỢT
  một tin (khóa `protection:{thiết bị}:{mốc}`), tối đa 1 tin/thiết bị/24 giờ, không gửi 21:00–07:00 giờ VN (07:00 gửi).
- `coach_weekly` 19:00 Chủ nhật giờ VN: một tin cho mỗi người giám hộ còn bật bản tin (khóa
  `weekly:{người}:{năm}-W{tuần}`), nội dung tất định, độ phủ dùng cùng hàm với `ops pilot`.
- Chống trùng bằng khóa `jobs.idempotency_key`/`messages_out.job_key`; trace bằng `agent_runs(graph='coach')` +
  `agent_steps` (chỉ số đếm và khóa mẫu, không văn bản tin).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import yaml
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.agents import texts
from hoicon.agents.runtime import safe_alias
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, AgentStep, Device, DeviceHeartbeat, Drill, Family, Incident, Job, Member
from hoicon.jobs.queue import enqueue
from hoicon.services import consent_gate
from hoicon.services.heartbeat_service import SLOT_SECONDS, family_coverage

logger = logging.getLogger(__name__)

VN = ZoneInfo("Asia/Ho_Chi_Minh")
SILENT_AFTER = timedelta(hours=24)
QUIET_FROM, QUIET_TO = 21, 7  # giờ im lặng [21:00, 07:00) giờ VN
MIN_GAP = timedelta(hours=24)  # tối đa 1 tin mất bảo vệ / thiết bị / 24 giờ
PERMISSION_OFF_SLOTS = 2
TIPS_FILE = Path(__file__).resolve().parents[4] / "data" / "coach" / "tips.vi.yaml"
WEEKLY_HOUR = 19  # Chủ nhật 19:00 giờ VN
RESOLVED_PREFIX = "resolved_"


def _vn(moment: datetime) -> datetime:
    return moment.astimezone(VN)


def in_quiet_hours(now: datetime) -> bool:
    hour = _vn(now).hour
    return hour >= QUIET_FROM or hour < QUIET_TO


def hour_key(now: datetime) -> str:
    return f"protection_watch:{_vn(now).strftime('%Y-%m-%dT%H')}"


async def schedule_hourly(sessions: async_sessionmaker, *, now: datetime | None = None) -> str:
    """Xếp job `protection_watch` của giờ hiện tại (lũy đẳng nhờ khóa giờ VN) ⇒ khóa job."""
    key = hour_key(now or datetime.now(UTC))
    await enqueue(sessions, "protection_watch", {}, key=key)
    return key


def iso_week(moment: datetime) -> str:
    year, week, _ = _vn(moment).isocalendar()
    return f"{year}-W{week:02d}"


def weekly_run_at(now: datetime) -> datetime:
    """Mốc chạy của tuần ISO hiện tại: Chủ nhật 19:00 giờ VN. Đã qua nhưng vẫn trong Chủ nhật ⇒ chạy ngay; sang tuần
    sau (thứ Hai trở đi) ⇒ mốc của tuần sau không phải bù ở đây (khóa tuần mới tự xếp)."""
    local = _vn(now)
    sunday = (local + timedelta(days=6 - local.weekday())).replace(hour=WEEKLY_HOUR, minute=0, second=0, microsecond=0)
    return sunday


async def schedule_weekly(sessions: async_sessionmaker, *, now: datetime | None = None) -> str:
    """Xếp job `coach_weekly` của tuần ISO hiện tại, chạy lúc Chủ nhật 19:00 VN (lũy đẳng nhờ khóa tuần)."""
    moment = now or datetime.now(UTC)
    key = f"coach_weekly:{iso_week(moment)}"
    delay = max(0.0, (weekly_run_at(moment) - moment.astimezone(VN)).total_seconds())
    await enqueue(sessions, "coach_weekly", {"week": iso_week(moment)}, key=key, delay_s=delay)
    return key


# --- Phát hiện mất bảo vệ ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Lapse:
    device_id: UUID
    family_id: UUID
    member_id: UUID  # người cao tuổi
    kind: str  # "silent" | "permission_off"
    since: datetime  # mốc bắt đầu đợt (giờ UTC)

    @property
    def key(self) -> str:
        return f"protection:{self.device_id}:{int(self.since.timestamp())}"


async def _permission_off_since(session: AsyncSession, device_id: UUID) -> datetime | None:
    """Mốc khung `false` ĐẦU TIÊN của đợt liên tiếp mới nhất; None nếu chưa đủ 2 khung `false` gần nhất."""
    rows = (
        await session.execute(
            select(DeviceHeartbeat.slot, DeviceHeartbeat.protected)
            .where(DeviceHeartbeat.device_id == device_id)
            .order_by(DeviceHeartbeat.slot.desc())
            .limit(400)
        )
    ).all()
    run: list[datetime] = []
    for slot, protected in rows:
        if protected:
            break
        run.append(slot)
    return run[-1] if len(run) >= PERMISSION_OFF_SLOTS else None


async def find_protection_lapses(session: AsyncSession, now: datetime, *, family_id: UUID | None = None) -> list[Lapse]:
    """Mọi đợt mất bảo vệ đang diễn ra (chưa lọc giờ im lặng/chống trùng). Loại: thiết bị đã thu hồi, gia đình demo/xóa,
    người cao tuổi chưa/không còn đồng ý `guardian_alerts`, thiết bị chưa từng gửi heartbeat."""
    query = (
        select(Device, Family.id)
        .join(Family, Family.id == Device.family_id)
        .where(Device.revoked_at.is_(None), Family.is_demo.is_(False), Family.deleted_at.is_(None))
        .order_by(Device.created_at, Device.id)
    )
    if family_id is not None:  # chỉ để test thu hẹp phạm vi trên DB dùng chung
        query = query.where(Family.id == family_id)
    devices = (await session.execute(query)).all()
    lapses: list[Lapse] = []
    for device, family_id in devices:
        ever = await session.scalar(
            select(func.count()).select_from(DeviceHeartbeat).where(DeviceHeartbeat.device_id == device.id)
        )
        if not ever:
            continue
        if not (await consent_gate.state_for(session, device.member_id)).guardian_alerts:
            continue
        if device.last_heartbeat_at < now - SILENT_AFTER:
            lapses.append(Lapse(device.id, family_id, device.member_id, "silent", device.last_heartbeat_at))
            continue  # đã im lặng thì khung `false` cũ không còn là chuyện "quyền tắt"
        since = await _permission_off_since(session, device.id)
        if since is not None:
            lapses.append(Lapse(device.id, family_id, device.member_id, "permission_off", since))
    return lapses


async def pick_guardian(session: AsyncSession, family_id: UUID) -> Member | None:
    """Người giám hộ hạng 1 có chat Zalo; không có ⇒ hạng 2 (FR-003). None ⇒ không ai nhận được."""
    return await session.scalar(
        select(Member)
        .where(
            Member.family_id == family_id,
            Member.role == "guardian",
            Member.deleted_at.is_(None),
            Member.zalo_chat_enc.is_not(None),
        )
        .order_by(Member.guardian_rank.asc().nullslast(), Member.created_at)
        .limit(1)
    )


async def _run_for(session: AsyncSession, thread_id: str) -> AgentRun:
    run = await session.scalar(select(AgentRun).where(AgentRun.thread_id == thread_id))
    if run is None:
        run = AgentRun(graph="coach", thread_id=thread_id, status="done", finished_at=func.now())
        session.add(run)
        await session.flush()
    return run


def _since_label(moment: datetime) -> str:
    local = _vn(moment)
    return f"{local:%H:%M} ngày {local.day} tháng {local.month}"


async def run_protection_watch(
    sessions: async_sessionmaker,
    *,
    now: datetime | None = None,
    enabled: bool | None = None,
    family_id: UUID | None = None,
) -> int:
    """Một lượt `protection_watch` ⇒ số tin đã xếp. Cờ `HOICON_PROTECTION_WATCH` tắt hoặc giờ im lặng ⇒ 0."""
    moment = now or datetime.now(UTC)
    if enabled is None:
        enabled = get_settings().protection_watch
    if not enabled or in_quiet_hours(moment):
        return 0
    queued = 0
    async with sessions.begin() as session:
        lapses = await find_protection_lapses(session, moment, family_id=family_id)
        for lapse in lapses:
            recent = await session.scalar(
                select(func.count())
                .select_from(Job)
                .where(
                    Job.kind == "notify_guardian",
                    Job.idempotency_key.startswith(f"protection:{lapse.device_id}:", autoescape=True),
                    Job.payload["queued_at"].astext
                    > (moment - MIN_GAP).isoformat(),  # đồng hồ của lượt chạy, không của DB
                )
            )
            if recent:
                continue
            guardian = await pick_guardian(session, lapse.family_id)
            protected = await session.get(Member, lapse.member_id)
            if guardian is None or protected is None:
                continue
            alias = safe_alias(protected.alias)
            text = (
                texts.guardian_protection_silent(alias, _since_label(lapse.since))
                if lapse.kind == "silent"
                else texts.guardian_protection_permission_off(alias)
            )
            payload = {
                "template": f"protection_{lapse.kind}",
                "family_id": str(lapse.family_id),
                "guardian_rank": guardian.guardian_rank or 1,
                "member_id": str(guardian.id),
                "protected_member_id": str(protected.id),  # spec 037 FR-002: kiểm đồng ý lúc gửi
                "text": text,
                "is_demo": False,
                "is_drill": False,
                "urgent": False,
                "job_key": lapse.key,
                "queued_at": moment.isoformat(),
            }
            await enqueue(session, "notify_guardian", payload, key=lapse.key)
            queued += 1
        run = await _run_for(session, f"coach-watch:{_vn(moment):%Y-%m-%d}")
        session.add(
            AgentStep(
                run_id=run.id,
                node="protection_watch",
                output={"lapses": len(lapses), "queued": queued, "hour": _vn(moment).hour},
            )
        )
    return queued


# --- Bản tin tuần --------------------------------------------------------------------------------------------


def load_tips(*, prod: bool | None = None) -> list[str]:
    """Các mẹo được phép hiện. Chưa duyệt (`approved: false`) ⇒ bản prod không có mẹo; dev/test vẫn hiện để thử."""
    if prod is None:
        prod = get_settings().env.strip().lower() in ("prod", "production")
    doc = yaml.safe_load(TIPS_FILE.read_text(encoding="utf-8"))
    if prod and doc.get("approved") is not True:
        return []
    return [str(t["text_vi"]) for t in doc.get("tips", [])]


def tip_for(moment: datetime, tips: Sequence[str]) -> str | None:
    if not tips:
        return None
    return tips[_vn(moment).isocalendar().week % len(tips)]


async def _digest_numbers(session: AsyncSession, family_id: UUID, member_id: UUID, now: datetime) -> dict[str, Any]:
    since = now - timedelta(days=7)
    incidents, resolved = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(Incident.state.like(f"{RESOLVED_PREFIX}%") | (Incident.state == "closed")),
            ).where(
                Incident.family_id == family_id,
                Incident.opened_at >= since,
                Incident.is_drill.is_(False),
                Incident.is_demo.is_(False),
            )
        )
    ).one()
    drills = await session.scalar(
        select(func.count())
        .select_from(Drill)
        .where(Drill.member_id == member_id, Drill.status.in_(("passed", "failed")), Drill.completed_at >= since)
    )
    coverage = await family_coverage(session, family_id, 7, now)
    return {"incidents": incidents, "resolved": resolved, "drills": drills or 0, "coverage": coverage}


async def run_coach_weekly(
    sessions: async_sessionmaker,
    *,
    now: datetime | None = None,
    tips: Sequence[str] | None = None,
    family_id: UUID | None = None,
) -> int:
    """Một lượt `coach_weekly` ⇒ số tin đã xếp. Lũy đẳng theo tuần (khóa tin + khóa lượt coach)."""
    moment = now or datetime.now(UTC)
    week = iso_week(moment)
    shown_tips = load_tips() if tips is None else list(tips)
    queued = 0
    async with sessions() as session:
        query = (
            select(Family.id).where(Family.is_demo.is_(False), Family.deleted_at.is_(None)).order_by(Family.created_at)
        )
        if family_id is not None:  # chỉ để test thu hẹp phạm vi trên DB dùng chung
            query = query.where(Family.id == family_id)
        families = (await session.scalars(query)).all()
    for fid in families:
        try:
            queued += await _weekly_for_family(sessions, fid, moment, week, shown_tips)
        except Exception as exc:  # một gia đình lỗi không chặn các nhà còn lại
            logger.warning("coach_weekly: bỏ qua một gia đình (%s)", type(exc).__name__)
    return queued


async def _weekly_for_family(
    sessions: async_sessionmaker, family_id: UUID, moment: datetime, week: str, tips: Sequence[str]
) -> int:
    async with sessions.begin() as session:
        device = await session.scalar(
            select(Device)
            .where(Device.family_id == family_id, Device.revoked_at.is_(None))
            .order_by(Device.created_at)
            .limit(1)
        )
        if device is None:
            return 0
        if not (await consent_gate.state_for(session, device.member_id)).guardian_alerts:
            return 0
        guardians = (
            await session.scalars(
                select(Member).where(
                    Member.family_id == family_id,
                    Member.role == "guardian",
                    Member.deleted_at.is_(None),
                    Member.weekly_digest_enabled.is_(True),
                    Member.zalo_chat_enc.is_not(None),
                )
            )
        ).all()
        if not guardians:
            return 0
        thread = f"coach:{family_id}:{week}"
        if await session.scalar(select(AgentRun.id).where(AgentRun.thread_id == thread)):
            return 0  # lượt này đã chạy (chạy lại cùng tuần không tạo thêm gì)
        protected = await session.get(Member, device.member_id)
        alias = safe_alias(protected.alias if protected else None)
        numbers = await _digest_numbers(session, family_id, device.member_id, moment)
        tip = tip_for(moment, tips)
        text = texts.weekly_digest(
            alias, numbers["incidents"], numbers["resolved"], numbers["coverage"], numbers["drills"], tip
        )
        run = await _run_for(session, thread)
        session.add(
            AgentStep(
                run_id=run.id,
                node="collect",
                output={
                    "incidents": numbers["incidents"],
                    "resolved": numbers["resolved"],
                    "drills": numbers["drills"],
                    "coverage_pct": None if numbers["coverage"] is None else texts.round_coverage(numbers["coverage"]),
                },
            )
        )
        variant = "incident" if numbers["incidents"] else ("no_data" if numbers["coverage"] is None else "quiet")
        session.add(
            AgentStep(
                run_id=run.id,
                node="compose",
                output={"template": "weekly_digest", "variant": variant, "tip": bool(tip)},
            )
        )
        for guardian in guardians:
            key = f"weekly:{guardian.id}:{week}"
            payload = {
                "template": "weekly_digest",
                "family_id": str(family_id),
                "guardian_rank": guardian.guardian_rank or 1,
                "member_id": str(guardian.id),
                "protected_member_id": str(device.member_id),  # spec 037 FR-002: kiểm đồng ý lúc gửi
                "text": text,
                "is_demo": False,
                "is_drill": False,
                "urgent": False,
                "quota_class": "digest",
                "job_key": key,
            }
            await enqueue(session, "notify_guardian", payload, key=key)
        session.add(
            AgentStep(run_id=run.id, node="send", output={"queued": len(guardians), "template": "weekly_digest"})
        )
        return len(guardians)


__all__ = ["SLOT_SECONDS", "Lapse", "find_protection_lapses", "run_coach_weekly", "run_protection_watch"]
