"""`IncidentService` — chỗ DUY NHẤT đổi trạng thái sự cố (spec 021, DATA-MODEL §4, CLAUDE.md luật 11).

Mỗi lần đổi: giữ `pg_advisory_xact_lock(hashtext(incident_id))` (thao tác người giám hộ và bộ hẹn giờ không giẫm nhau),
so `expected_version` (khóa lạc quan: bên đến sau nhận `ConcurrencyConflictError` thay vì ghi đè), kiểm cạnh có trong
`ALLOWED`, rồi ghi `incident_transitions` + tăng `version` cùng một giao dịch. Service KHÔNG commit: người gọi sở hữu
giao dịch (để lô sự kiện, sự cố và nhật ký thành công hoặc hỏng cùng nhau).

Hai bất biến còn được CSDL giữ độc lập với mã này: `level >= rule_floor` (CHECK) và trạng thái cuối không quay lại
(trigger `trg_incidents_terminal`).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.db.models import Family, Incident, IncidentTransition, RiskEventRecord
from hoicon.domain.events import RiskEvent
from hoicon.domain.risk import RiskLevel, raise_only

STATES: Final = frozenset(
    {
        "detected",
        "assessing",
        "awaiting_guardian",
        "verifying",
        "rescore",
        "resolved_safe",
        "resolved_prevented",
        "resolved_false_alarm",
        "resolved_no_response",
        "case_open",
        "closed",
    }
)
RESOLVED: Final = frozenset(state for state in STATES if state.startswith("resolved_"))
TERMINAL: Final = RESOLVED | {"closed"}
ACTORS: Final = frozenset({"device", "agent", "guardian", "timer", "system"})
MAX_REASON = 256
# Cửa sổ liên kết (FR-008, bằng cửa sổ rủi ro 600 s của luật trên máy): sự cố mở mà đã im lặng quá lâu không nuốt thêm
# sự kiện — sự kiện mới mở sự cố MỚI (và cảnh báo mới). Việc đưa sự cố bị bỏ quên ra khỏi `detected` thuộc bộ hẹn giờ.
LINK_WINDOW = timedelta(seconds=600)

# Sơ đồ DATA-MODEL §4: detected → assessing → awaiting_guardian → verifying → rescore → resolved_* | case_open → closed.
# `assessing`/`awaiting_guardian` được kết thúc thẳng (đã rõ an toàn/đã chặn được/không ai trả lời); `closed` chỉ sau
# `case_open`. Mở lại một sự cố đã kết thúc = sự cố MỚI liên kết (bất biến 2), không có cạnh đi ra từ trạng thái cuối.
ALLOWED: Final[dict[str, frozenset[str]]] = {
    "detected": frozenset({"assessing"}),
    "assessing": frozenset({"awaiting_guardian"}) | RESOLVED,
    "awaiting_guardian": frozenset({"verifying", "case_open"}) | RESOLVED,
    "verifying": frozenset({"rescore"}),
    "rescore": frozenset({"case_open"}) | RESOLVED,
    "case_open": frozenset({"closed"}),
    **{state: frozenset() for state in TERMINAL},
}

# FR-008: các loại sự kiện tự mở sự cố dù mức sàn thấp; ngoài ra mức sàn ≥ high cũng mở.
TRIGGER_TYPES: Final = frozenset(
    {"banking_app_foreground", "flagged_number_call", "sideload_detected", "ask_child_pressed"}
)


class IncidentError(Exception):
    """Gốc của lỗi nghiệp vụ sự cố (không chứa dữ liệu cá nhân)."""


class IncidentNotFoundError(IncidentError):
    pass


class InvalidTransitionError(IncidentError):
    """Cạnh không có trong `ALLOWED` (kể cả mọi cạnh đi ra từ trạng thái cuối)."""


class ConcurrencyConflictError(IncidentError):
    """`expected_version` đã cũ: có bên khác đổi sự cố trước (người giám hộ so với bộ hẹn giờ)."""


@dataclass(frozen=True)
class Correlation:
    incident: Incident
    opened: bool  # true nếu chính sự kiện này vừa mở sự cố


async def _lock(session: AsyncSession, key: str) -> None:
    """Khóa tư vấn theo giao dịch, tự nhả khi commit/rollback. Va chạm băm chỉ làm hai khóa chờ nhau."""
    await session.execute(text("select pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


class IncidentService:
    @staticmethod
    async def create_incident(
        session: AsyncSession,
        *,
        family_id: UUID,
        member_id: UUID,
        device_id: UUID | None,
        rule_floor: RiskLevel | str,
        level: RiskLevel | str | None = None,
        is_drill: bool = False,
        drill_id: UUID | None = None,
        opened_by_event_id: UUID | None = None,
        actor: str = "device",
        reason: str | None = None,
    ) -> Incident:
        """Mở sự cố ở `detected`. Mức = cao nhất của sàn, `low` và đề xuất (chỉ nâng, không bao giờ dưới sàn)."""
        floor = RiskLevel(rule_floor)
        if device_id is not None:
            await _lock(session, f"open-incident:{device_id}")  # cùng khóa với correlate_event (khóa lồng nhau hợp lệ)
        proposed = RiskLevel(level) if level is not None else None
        if proposed is not None and proposed.rank < floor.rank:
            raise ValueError("level không được thấp hơn rule_floor")
        if is_drill and drill_id is None:
            raise ValueError("sự cố diễn tập cần drill_id")
        if actor not in ACTORS:
            raise ValueError("actor không hợp lệ")
        family_is_demo = await session.scalar(select(Family.is_demo).where(Family.id == family_id))
        incident = Incident(
            family_id=family_id,
            member_id=member_id,
            device_id=device_id,
            state="detected",
            level=raise_only(floor, RiskLevel.LOW, proposed).value,
            rule_floor=floor.value,
            is_drill=is_drill,
            drill_id=drill_id,
            is_demo=bool(family_is_demo),
            opened_by_event_id=opened_by_event_id,
        )
        session.add(incident)
        await session.flush()
        session.add(
            IncidentTransition(
                incident_id=incident.id, from_state=None, to_state="detected", actor=actor, reason=reason
            )
        )
        await session.flush()
        return incident

    @staticmethod
    async def transition(
        session: AsyncSession,
        incident_id: UUID,
        to_state: str,
        actor: str,
        reason: str | None = None,
        *,
        expected_version: int,
    ) -> Incident:
        """Chuyển trạng thái nguyên tử. `reason` là mã ngắn do máy chủ đặt (≤ 256), không chép văn bản người dùng."""
        if to_state not in STATES:
            raise ValueError("trạng thái không hợp lệ")
        if actor not in ACTORS:
            raise ValueError("actor không hợp lệ")
        if reason is not None and len(reason) > MAX_REASON:
            raise ValueError("reason quá dài")
        await _lock(session, str(incident_id))
        incident = await session.get(Incident, incident_id, populate_existing=True)
        if incident is None:
            raise IncidentNotFoundError(str(incident_id))
        if incident.version != expected_version:
            raise ConcurrencyConflictError(f"version hiện tại {incident.version}, mong đợi {expected_version}")
        if to_state not in ALLOWED[incident.state]:
            raise InvalidTransitionError(f"{incident.state} → {to_state} không được phép")
        from_state = incident.state
        incident.state = to_state
        incident.version += 1
        if to_state in TERMINAL:
            incident.closed_at = datetime.now(UTC)
            if to_state in RESOLVED:
                incident.outcome = to_state.removeprefix("resolved_")
        session.add(
            IncidentTransition(
                incident_id=incident.id, from_state=from_state, to_state=to_state, actor=actor, reason=reason
            )
        )
        await session.flush()
        return incident

    @staticmethod
    async def correlate_event(
        session: AsyncSession, event: RiskEvent, *, device_id: UUID, family_id: UUID, member_id: UUID
    ) -> Correlation | None:
        """Gắn sự kiện (đã có trong `risk_events`) vào sự cố đang mở của thiết bị, hoặc mở sự cố mới nếu đủ điều kiện.

        - Có sự cố đang mở (cùng thiết bị, cùng loại thật/diễn tập, cùng `drill_id`) ⇒ liên kết; sàn cao hơn thì NÂNG
          `rule_floor` + `level` (không bao giờ hạ).
        - Không có và sự kiện thuộc `TRIGGER_TYPES` hoặc sàn ≥ high ⇒ mở sự cố `detected`.
        - Còn lại ⇒ None (sự kiện chỉ nằm trong `risk_events`).
        Khóa theo thiết bị để nhiều lô đồng thời không mở hai sự cố.
        """
        await _lock(session, f"open-incident:{device_id}")
        last_activity = func.coalesce(
            select(func.max(RiskEventRecord.received_at))
            .where(RiskEventRecord.incident_id == Incident.id)
            .scalar_subquery(),
            Incident.opened_at,
        )
        query = (
            select(Incident)
            .where(
                Incident.device_id == device_id,
                Incident.is_drill == event.is_drill,
                Incident.state.not_in(TERMINAL),
                last_activity >= func.now() - LINK_WINDOW,
            )
            .order_by(Incident.opened_at.desc(), Incident.id.desc())
            .limit(1)
        )
        if event.is_drill:
            query = query.where(Incident.drill_id == event.drill_id)
        incident = (await session.scalars(query)).first()
        if incident is not None:
            await _lock(session, str(incident.id))
            await session.refresh(incident)  # bên khác có thể đã kết thúc nó trong lúc ta chờ khóa
            if incident.state in TERMINAL:
                incident = None
        if incident is not None:
            floor = RiskLevel(incident.rule_floor)
            if event.rule_floor.rank > floor.rank:
                incident.rule_floor = event.rule_floor.value
                incident.level = raise_only(RiskLevel(incident.level), event.rule_floor).value
                incident.version += 1
            opened = False
        elif event.type in TRIGGER_TYPES or event.rule_floor.rank >= RiskLevel.HIGH.rank:
            incident = await IncidentService.create_incident(
                session,
                family_id=family_id,
                member_id=member_id,
                device_id=device_id,
                rule_floor=event.rule_floor,
                is_drill=event.is_drill,
                drill_id=event.drill_id,
                opened_by_event_id=event.id,
                reason="risk_event",
            )
            opened = True
        else:
            return None
        await session.execute(
            update(RiskEventRecord).where(RiskEventRecord.id == event.id).values(incident_id=incident.id)
        )
        await session.flush()
        return Correlation(incident, opened)


# Quyết định của người giám hộ (spec 023, web `/a/[token]`, JWT, Zalo 1/2) ⇒ trạng thái đích. "Nghi lừa đảo"
# (`emergency_pause`) KHÔNG kết thúc sự cố: mở hồ sơ (`case_open`) để còn theo dõi; `prevented` chỉ khi đã chặn được.
GUARDIAN_DECISIONS: Final[dict[str, str]] = {
    "safe": "resolved_safe",
    "prevented": "resolved_prevented",
    "false_alarm": "resolved_false_alarm",
    "emergency_pause": "case_open",
}
GUARDIAN_DECIDABLE: Final = frozenset({"detected", "assessing", "awaiting_guardian"})  # còn chờ người giám hộ quyết


async def apply_guardian_decision(
    session: AsyncSession, incident: Incident, decision: str, reason: str | None = None
) -> Incident:
    """Đưa sự cố tới trạng thái của quyết định, đi qua các cạnh trung gian của `ALLOWED` bằng actor `system`.

    Sự cố đã kết thúc ⇒ `InvalidTransitionError`; bên khác đổi trước ⇒ `ConcurrencyConflictError`.
    """
    target = GUARDIAN_DECISIONS[decision]
    if incident.state in TERMINAL:
        raise InvalidTransitionError(f"sự cố đã kết thúc ({incident.state})")
    steps = {"detected": "assessing", "assessing": "awaiting_guardian" if target == "case_open" else None}
    while (step := steps.get(incident.state)) is not None:
        incident = await IncidentService.transition(
            session, incident.id, step, "system", f"guardian_{decision}", expected_version=incident.version
        )
    return await IncidentService.transition(
        session, incident.id, target, "guardian", reason or f"guardian_{decision}", expected_version=incident.version
    )
