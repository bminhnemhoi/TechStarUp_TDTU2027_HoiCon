"""Vòng đời một bài diễn tập (spec 028, P2-13): đặt lịch, mời, ghi kết quả, hết hạn. KHÔNG gọi LLM.

Mọi đổi `drills.status` đi qua MỘT hàm `advance` theo bảng cạnh `ALLOWED` (trạng thái cuối không có cạnh đi ra):

    scheduled ─offer─► offered ─(kết quả completed)─► in_progress ─► passed | failed
        │                 ├─ declined ("Để lúc khác")
        │                 └─ aborted ("Dừng", hoặc cuộc gọi thật đến)
        └──── quá window_end ─► expired  (offered/in_progress: quá window_end + 1 giờ ân hạn ⇒ expired)

Máy chỉ báo `completed`/`aborted`/`declined` kèm MÃ lựa chọn; máy chủ tự chấm lại từ kịch bản của mình (`domain.drill`),
không tin điểm hay trạng thái do máy gửi. Mọi thao tác ghi của một gia đình giữ `pg_advisory_xact_lock` theo gia đình
(hai thiết bị/ops không giẫm nhau, hạn mức tháng không bị vượt khi đặt lịch song song), rồi khóa dòng bài.

Riêng tư: không lưu văn bản tự do; job tin tổng kết chỉ mang id + xưng hô + câu chữ đã duyệt của kịch bản.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.agents import texts
from hoicon.config import DEV_ENVS, get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Drill, Family, Member
from hoicon.domain import drill as dr
from hoicon.jobs.queue import enqueue

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))  # Việt Nam không có giờ mùa hè
MONTHLY_LIMIT = 2  # PILOT-PROTOCOL: tối đa 2 bài/tháng dương lịch (giờ VN) cho cả gia đình
MIN_WINDOW = timedelta(minutes=30)  # máy hỏi theo nhịp heartbeat 15 phút ⇒ ít nhất một lần trong khung
MAX_WINDOW = timedelta(hours=4)
GRACE = timedelta(hours=1)  # kết quả gửi muộn (mất mạng) vẫn nhận tới window_end + GRACE
CLIENT_CLOCK_SLACK = timedelta(minutes=5)
FINAL = ("passed", "failed", "aborted", "declined", "expired")
OPEN = ("scheduled", "offered", "in_progress")

ALLOWED: dict[str, frozenset[str]] = {
    "scheduled": frozenset({"offered", "expired"}),
    "offered": frozenset({"in_progress", "declined", "aborted", "expired"}),
    "in_progress": frozenset({"passed", "failed", "aborted", "expired"}),
    **{state: frozenset() for state in FINAL},
}


class DrillError(Exception):
    """Gốc của lỗi nghiệp vụ diễn tập."""


class DrillRefused(DrillError):
    """Đặt lịch bị từ chối; `code` là mã ổn định (ops in ra, test so sánh), không chứa dữ liệu cá nhân."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class DrillNotFound(DrillError):
    """Không có bài này trong gia đình/người cao tuổi này (cố ý không phân biệt "không tồn tại" với "của nhà khác")."""


class InvalidDrillTransition(DrillError):
    """Cạnh không có trong `ALLOWED`, hoặc bài đã ở trạng thái không nhận kết quả."""


class ResultConflict(DrillError):
    """Bài đã có kết quả khác với kết quả vừa gửi."""


@dataclass(frozen=True)
class ResultOutcome:
    drill: Drill
    replay: bool  # gửi lại đúng kết quả đã có ⇒ không làm gì thêm


async def _lock(session: AsyncSession, family_id: UUID) -> None:
    """Khóa tư vấn theo gia đình cho mọi ghi về diễn tập (khóa riêng, không đụng khóa sự cố)."""
    await session.execute(text("select pg_advisory_xact_lock(hashtext(:key))"), {"key": f"drill-family:{family_id}"})


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _month_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """Đầu tháng dương lịch (giờ VN) chứa `moment` và đầu tháng sau, đổi về UTC."""
    local = moment.astimezone(VN_TZ)
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    following = (start + timedelta(days=32)).replace(day=1)
    return start.astimezone(UTC), following.astimezone(UTC)


def _approved_or_dev(script: dict[str, Any]) -> bool:
    """Nội dung chưa được Minh duyệt chỉ chạy ở dev/test/ci; mọi môi trường khác đóng (đóng khi chưa duyệt, FR-010)."""
    return bool(script["approved"]) or get_settings().env in DEV_ENVS


async def _has_consent(session: AsyncSession, member_id: UUID) -> bool:
    latest = await session.scalar(
        select(Consent.granted)
        .where(Consent.member_id == member_id, Consent.purpose == "drills")
        .order_by(Consent.recorded_at.desc(), Consent.id.desc())
        .limit(1)
    )
    return latest is True


def _trusted_time(value: datetime | None, now: datetime) -> datetime:
    """Mốc do máy báo chỉ là thông tin: lệch quá xa thì dùng giờ máy chủ."""
    if value is None or value > now + CLIENT_CLOCK_SLACK or value < now - timedelta(days=7):
        return now
    return value


class DrillService:
    @staticmethod
    def advance(drill: Drill, target: str) -> None:
        """Hàm DUY NHẤT đổi `drill.status`."""
        if target not in ALLOWED.get(drill.status, frozenset()):
            raise InvalidDrillTransition(f"{drill.status} → {target}")
        drill.status = target

    @staticmethod
    async def schedule(
        session: AsyncSession,
        *,
        family_id: UUID,
        member_id: UUID,
        window_start: datetime,
        window_end: datetime,
        script_id: str,
        by: str,
        now: datetime | None = None,
    ) -> Drill:
        """Đặt lịch một bài (giao dịch của người gọi). Từ chối bằng `DrillRefused(code)`, không ghi gì."""
        now = _now(now)
        script = dr.get_script(script_id)
        if script is None:
            raise DrillRefused("script_unknown")
        if not _approved_or_dev(script):
            raise DrillRefused("script_not_approved")
        if window_start.tzinfo is None or window_end.tzinfo is None or window_end <= window_start:
            raise DrillRefused("window_invalid")
        if window_end <= now:
            raise DrillRefused("window_past")
        if window_end - window_start < MIN_WINDOW:
            raise DrillRefused("window_too_short")
        if window_end - window_start > MAX_WINDOW:
            raise DrillRefused("window_too_long")
        member = await session.get(Member, member_id)
        if member is None or member.family_id != family_id or member.role != "protected":
            raise DrillRefused("member_not_found")
        await _lock(session, family_id)
        if not await _has_consent(session, member_id):
            raise DrillRefused("consent_missing")
        overlap = await session.scalar(
            select(Drill.id)
            .where(
                Drill.member_id == member_id,
                Drill.status.in_(OPEN),
                Drill.window_start < window_end,
                Drill.window_end > window_start,
            )
            .limit(1)
        )
        if overlap is not None:
            raise DrillRefused("window_overlaps")
        first, following = _month_bounds(window_start)
        # Bài đặt rồi hủy khi chưa từng mời (expired, offered_at rỗng) không tốn lượt; bài đã mời rồi từ chối/hết hạn
        # thì có (không nhắc một người nhiều lần trong tháng).
        used = await session.scalar(
            select(func.count())
            .select_from(Drill)
            .where(
                Drill.family_id == family_id,
                Drill.window_start >= first,
                Drill.window_start < following,
                or_(Drill.status != "expired", Drill.offered_at.is_not(None)),
            )
        )
        if (used or 0) >= MONTHLY_LIMIT:
            raise DrillRefused("monthly_limit")
        family = await session.get(Family, family_id)
        drill = Drill(
            id=new_id(),
            family_id=family_id,
            member_id=member_id,
            scheduled_by=by,
            script_id=script_id,
            window_start=window_start,
            window_end=window_end,
            status="scheduled",
            is_demo=bool(family.is_demo) if family else False,
        )
        session.add(drill)
        await session.flush()
        # Bộ hẹn giờ hết hạn: một job một bài, chạy sau ân hạn (handler lũy đẳng, chạy lại vô hại).
        delay = max(0.0, (window_end + GRACE - now).total_seconds()) + 60
        await enqueue(session, "drill_expire", {"drill_id": str(drill.id)}, delay_s=delay, key=f"{drill.id}:expire")
        logger.info("drills: đã đặt lịch bài %s", drill.id)
        return drill

    @staticmethod
    async def offer(
        session: AsyncSession, *, family_id: UUID, member_id: UUID, now: datetime | None = None
    ) -> Drill | None:
        """Bài đang trong khung giờ của người cao tuổi (chưa trả lời) hoặc None. Lần đầu ⇒ `offered`."""
        now = _now(now)
        await _lock(session, family_id)
        if not await _has_consent(session, member_id):
            return None
        drill = await session.scalar(
            select(Drill)
            .where(
                Drill.family_id == family_id,
                Drill.member_id == member_id,
                Drill.status.in_(("scheduled", "offered")),
                Drill.window_start <= now,
                Drill.window_end >= now,
            )
            .order_by(Drill.window_start)
            .limit(1)
            .with_for_update()
        )
        if drill is None:
            return None
        script = dr.get_script(drill.script_id)
        if script is None or not _approved_or_dev(script):
            return None
        if drill.status == "scheduled":
            DrillService.advance(drill, "offered")
            drill.offered_at = now
            logger.info("drills: đã mời bài %s", drill.id)
        return drill

    @staticmethod
    async def record_result(
        session: AsyncSession,
        *,
        family_id: UUID,
        member_id: UUID,
        drill_id: UUID,
        status: str,
        answers: list[dict[str, Any]],
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        now: datetime | None = None,
    ) -> ResultOutcome:
        """Ghi kết quả máy gửi (lũy đẳng theo bài). `status` ∈ {declined, aborted, completed}; `completed` chấm lại.

        Lỗi: `DrillNotFound` (không phải bài của người này), `dr.InvalidAnswers` (đáp án sai cấu trúc), `ResultConflict`
        (đã có kết quả khác), `InvalidDrillTransition` (bài chưa mời hoặc đã hết hạn)."""
        now = _now(now)
        await _lock(session, family_id)
        drill = await session.scalar(select(Drill).where(Drill.id == drill_id).with_for_update())
        if drill is None or drill.family_id != family_id or drill.member_id != member_id:
            raise DrillNotFound(str(drill_id))
        script = dr.get_script(drill.script_id)
        if script is None:
            raise InvalidDrillTransition("script_unknown")
        grade: dr.Grade | None = None
        if status == "declined":
            if answers:
                raise dr.InvalidAnswers("từ chối thì không có câu trả lời")
            clean: list[dict[str, Any]] = []
        elif status == "aborted":
            clean = dr.normalize_answers(script, answers, complete=False)
        else:
            grade = dr.grade(script, answers)
            clean = dr.normalize_answers(script, answers, complete=True)

        if drill.status in FINAL:
            if _same_result(drill, status, clean):
                return ResultOutcome(drill, replay=True)
            raise ResultConflict(drill.status)
        if drill.status not in ("offered", "in_progress"):
            raise InvalidDrillTransition(f"{drill.status} chưa nhận kết quả")

        started = _trusted_time(started_at, now)
        if status == "declined":
            DrillService.advance(drill, "declined")
        elif status == "aborted":
            DrillService.advance(drill, "aborted")
            drill.answers = clean
            drill.started_at = drill.started_at or (started if clean else None)
        else:
            if grade is None:  # không xảy ra: `completed` luôn có điểm; giữ để kiểu chặt và để lỗi lập trình lộ ra
                raise InvalidDrillTransition("completed without a grade")
            if drill.status == "offered":
                DrillService.advance(drill, "in_progress")
            drill.started_at = drill.started_at or started
            DrillService.advance(drill, "passed" if grade.passed else "failed")
            drill.score = grade.score
            drill.answers = clean
            drill.completed_at = _trusted_time(completed_at, now)
        if status != "declined":
            await _queue_debrief(
                session, drill, script, None if status == "aborted" else grade is not None and grade.passed
            )
        logger.info("drills: bài %s kết thúc %s", drill.id, drill.status)
        return ResultOutcome(drill, replay=False)

    @staticmethod
    async def expire(session: AsyncSession, *, now: datetime | None = None, limit: int = 200) -> int:
        """Đánh `expired` cho bài quá hạn: `scheduled` quá `window_end`; `offered`/`in_progress` quá `window_end` + ân
        hạn. Không gửi tin. Bỏ qua dòng đang bị giao dịch khác khóa (nhận kết quả đúng lúc)."""
        now = _now(now)
        due = (
            select(Drill)
            .where(
                or_(
                    and_(Drill.status == "scheduled", Drill.window_end < now),
                    and_(Drill.status.in_(("offered", "in_progress")), Drill.window_end < now - GRACE),
                )
            )
            .order_by(Drill.window_end)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        drills = list(await session.scalars(due))
        for drill in drills:
            DrillService.advance(drill, "expired")
        if drills:
            logger.info("drills: đã cho hết hạn %d bài", len(drills))
        return len(drills)

    @staticmethod
    async def cancel(session: AsyncSession, *, family_id: UUID, drill_id: UUID) -> Drill:
        """Hủy một bài chưa bắt đầu (ops): kết thúc sớm bằng `expired`."""
        await _lock(session, family_id)
        drill = await session.scalar(select(Drill).where(Drill.id == drill_id).with_for_update())
        if drill is None or drill.family_id != family_id:
            raise DrillNotFound(str(drill_id))
        if drill.status not in ("scheduled", "offered"):
            raise InvalidDrillTransition(f"không hủy được bài đang {drill.status}")
        DrillService.advance(drill, "expired")
        return drill

    @staticmethod
    async def list_for_family(session: AsyncSession, family_id: UUID, limit: int = 50) -> list[Drill]:
        return list(
            await session.scalars(
                select(Drill).where(Drill.family_id == family_id).order_by(Drill.window_start.desc()).limit(limit)
            )
        )


def _same_result(drill: Drill, status: str, clean: list[dict[str, Any]]) -> bool:
    """Kết quả gửi lại có trùng với kết quả đã ghi không (để trả 200 thay vì 409)."""
    if status == "declined":
        return drill.status == "declined"
    if status == "aborted":
        return drill.status == "aborted" and (drill.answers or []) == clean
    return drill.status in ("passed", "failed") and (drill.answers or []) == clean


async def _queue_debrief(session: AsyncSession, drill: Drill, script: dict[str, Any], passed: bool | None) -> None:
    """Xếp tin tổng kết cho người giám hộ hạng 1 (FR-006): một tin mỗi bài nhờ khóa `{drill}:msg:debrief`."""
    from hoicon.agents.runtime import safe_alias  # nạp muộn: runtime kéo theo đồ thị LangGraph

    elder = await session.get(Member, drill.member_id)
    alias = safe_alias(elder.alias if elder else None)
    payload = {
        "template": "debrief",
        "family_id": str(drill.family_id),
        "guardian_rank": 1,
        "drill_id": str(drill.id),
        "protected_member_id": str(drill.member_id),  # spec 037 FR-002: kiểm đồng ý lúc gửi
        "text": texts.drill_debrief(alias, passed, dr.red_flags(script)),
        "is_demo": bool(drill.is_demo),
        "is_drill": True,
    }
    await enqueue(session, "notify_guardian", payload, key=f"{drill.id}:msg:debrief")
