"""Mô phỏng cho BGK (spec 033, `/v1/sim/*`): chạy một kịch bản hư cấu qua CÙNG đường với máy thật.

- Sự kiện dựng bằng `eval.cases.build_event`, đi qua `ingest_events` (hàm của `POST /v1/events`): ghi `risk_events`,
  mở sự cố bằng `IncidentService`, cảnh báo nhanh. Khác duy nhất: mỗi lượt có MỘT thiết bị demo riêng (nhãn
  `sim:<kịch bản>`, để hai lượt song song không bị gom vào một sự cố) và đồ thị khởi động tại chỗ (D2), không qua job.
- `llm=replay`: mỗi lượt giữ một `IncidentRuntime` với `ReplayClient(cassette)` trong bộ nhớ (D2); trả lời E8 đi qua đó.
  Không có cassette (ảnh container không chứa `backend/eval`) hoặc runtime đã mất ⇒ `llm_mode: "fallback"`.
- Tin người giám hộ của sự cố mô phỏng KHÔNG tới Zalo (cờ `sim`, FR-004): bản ghi mock là `jobs.payload` đã che PII.
- Hạn mức (FR-008): 10 lượt/giờ/người giám hộ, 3 lượt đang chạy/gia đình; bộ nhớ ⇒ đúng với một tiến trình (ADR-002).
"""

import logging
import secrets
import time
from collections import OrderedDict, deque
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

import yaml
from sqlalchemy import func, select

from hoicon.agents import texts
from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.api.routers.events import ingest_events, start_graph_payload
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, Device, Family, Incident, Job, Member
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import RiskEventIn
from hoicon.domain.pii import mask_text
from hoicon.eval.cases import CASE_ID, SCENARIOS_DIR, build_event, find_cassette, load_case
from hoicon.eval.replay import ReplayClient
from hoicon.services.incident_service import TERMINAL
from hoicon.services.runtime_service import ensure_runtime

logger = logging.getLogger(__name__)

LlmMode = Literal["replay", "live", "fallback"]
NO_RULE_NOTE = "Máy không bật nhắc dừng lại với tình huống này"
MAX_STARTS_PER_HOUR = 10
MAX_ACTIVE_PER_FAMILY = 3
MAX_RUNTIMES = 20
RUNTIME_TTL_S = 3600
SIM_LABEL_PREFIX = "sim:"  # nhãn thiết bị mô phỏng: "sim:<scenario_id>" (đánh dấu bền, không cần migration)
LINK_PLACEHOLDER = "(liên kết xử lý khẩn cấp — bản mô phỏng không có liên kết thật)"
MAX_MESSAGES = 20


class SimError(Exception):
    """Lỗi nghiệp vụ của mô phỏng; `status` là mã HTTP route trả về."""

    def __init__(self, status: int, detail: str, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.status, self.detail, self.retry_after = status, detail, retry_after


@dataclass
class _Entry:
    mode: LlmMode
    expires: float
    runtime: IncidentRuntime | None = None  # chỉ `replay`; live/fallback dùng runtime chung của tiến trình
    stack: AsyncExitStack | None = None


_registry: OrderedDict[UUID, _Entry] = OrderedDict()
_starts: dict[UUID, deque[float]] = {}


def reset() -> None:
    """Test: xóa hạn mức và registry (không đóng runtime — test tự đóng nếu mở)."""
    _registry.clear()
    _starts.clear()


# --- kịch bản ------------------------------------------------------------------------------------------------------

# Nhãn nhóm thủ đoạn cho ô chọn (FR-015): nhóm mới ở `scenario.v1.json` thiếu nhãn ⇒ test đỏ, `title_vi` ném KeyError.
SCENARIO_TITLE_VI: dict[str, str] = {
    "fake_police": "Giả danh công an",
    "fake_tax": "Giả danh cơ quan thuế",
    "fake_evn": "Giả danh điện lực",
    "deepfake_relative": "Giả giọng/mặt người thân",
    "task_scam": "Việc làm online",
    "recovery_scam": "Hứa lấy lại tiền",
    "fake_vneid": "Giả danh VNeID",
    "fake_bank": "Giả danh ngân hàng",
    "investment": "Mời đầu tư",
    "fake_delivery": "Giả danh giao hàng",
    "prize_gift": "Trúng thưởng, quà tặng",
    "fake_health": "Giả danh y tế",
    "benign_bank": "Cuộc gọi thật: ngân hàng",
    "benign_relative_new_number": "Cuộc gọi thật: người thân đổi số",
    "benign_shipper": "Cuộc gọi thật: người giao hàng",
    "benign_official": "Cuộc gọi thật: cơ quan",
    "benign_utility": "Cuộc gọi thật: điện, nước",
    "benign_family": "Cuộc gọi thật: người nhà",
}


def title_vi(case_id: str, category: str) -> str:
    """Tên ngắn tiếng Việt, tất định: nhãn nhóm + " · ca " + số cuối của id (bỏ số 0 đầu)."""
    return f"{SCENARIO_TITLE_VI[category]} · ca {int(case_id.rsplit('_', 1)[1])}"


def list_scenarios() -> list[dict[str, Any]]:
    """`sim_scenarios.v1`: không có `elder_note`, `source_ref` hay tín hiệu máy (chỉ thứ BGK cần để chọn)."""
    out: list[dict[str, Any]] = []
    for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        out.append(
            {
                "id": raw["id"],
                "category": raw["category"],
                "title_vi": title_vi(raw["id"], raw["category"]),
                "is_benign": bool(raw["is_benign"]),
                "injection": bool(raw.get("injection", False)),
                "draft": bool(raw.get("draft", False)),
                "script_vi": str(raw["script_vi"]).strip(),
            }
        )
    return out


# --- hạn mức -------------------------------------------------------------------------------------------------------


def _check_hourly(guardian_id: UUID, now: float) -> None:
    window = _starts.setdefault(guardian_id, deque())
    while window and now - window[0] >= 3600:
        window.popleft()
    if len(window) >= MAX_STARTS_PER_HOUR:
        raise SimError(429, "Đã chạy nhiều lượt mô phỏng, vui lòng thử lại sau.", max(1, int(3600 - (now - window[0]))))


async def _active_sim_incidents(family_id: UUID) -> int:
    query = (
        select(func.count())
        .select_from(Incident)
        .join(Device, Device.id == Incident.device_id)
        .where(
            Incident.family_id == family_id,
            Device.label.startswith(SIM_LABEL_PREFIX),
            Incident.state.not_in(tuple(TERMINAL)),
        )
    )
    async with get_sessionmaker()() as session:
        return int(await session.scalar(query) or 0)


# --- runtime phát lại (D2) -----------------------------------------------------------------------------------------


async def _drop(incident_id: UUID) -> None:
    entry = _registry.pop(incident_id, None)
    if entry is not None and entry.stack is not None:
        await entry.stack.aclose()


async def _prune(now: float) -> None:
    for key in [k for k, e in _registry.items() if e.expires <= now]:
        await _drop(key)
    while len(_registry) > MAX_RUNTIMES:
        await _drop(next(iter(_registry)))


async def _open_replay(case_id: str) -> tuple[IncidentRuntime, AsyncExitStack] | None:
    """Runtime với `ReplayClient(cassette)`; None nếu không có cassette (ảnh container không chứa `backend/eval`)."""
    try:
        path = find_cassette(case_id, "full")
    except FileNotFoundError:
        return None
    settings = get_settings()
    router = LlmRouter(ReplayClient.from_path(path), settings.llm_fast_model, Decimal(1000))
    stack = AsyncExitStack()
    try:
        runtime = await stack.enter_async_context(IncidentRuntime.open(Deps(router, get_sessionmaker(), settings)))
    except BaseException:
        await stack.aclose()
        raise
    return runtime, stack


async def _runtime_for(incident_id: UUID) -> tuple[IncidentRuntime, LlmMode]:
    """Runtime của lượt (replay) hoặc runtime chung; lượt đã mất khỏi registry ⇒ runtime chung + `fallback`."""
    await _prune(time.monotonic())
    entry = _registry.get(incident_id)
    if entry is None:
        return await ensure_runtime(), "fallback"
    return entry.runtime or await ensure_runtime(), entry.mode


# --- khởi động một lượt --------------------------------------------------------------------------------------------


def _sim_event(case_id: str) -> RiskEventIn | None:
    event = build_event(load_case(case_id))
    if event is None:
        return None
    data = event.model_dump(mode="json", exclude_none=True)
    data.update(id=str(new_id()), occurred_at=datetime.now(UTC).isoformat(), app_version="sim-1", rules_version="sim-1")
    return RiskEventIn.model_validate(data)


async def _demo_family_member(family_id: UUID) -> UUID:
    async with get_sessionmaker()() as session:
        family = await session.get(Family, family_id)
        if family is None or not family.is_demo:
            raise SimError(404, "Không tìm thấy")
        member = await session.scalar(
            select(Member.id)
            .where(Member.family_id == family_id, Member.role == "protected", Member.deleted_at.is_(None))
            .order_by(Member.created_at)
            .limit(1)
        )
    if member is None:
        raise SimError(404, "Không tìm thấy")
    return member


async def _new_sim_device(family_id: UUID, member_id: UUID, scenario_id: str) -> UUID:
    async with get_sessionmaker().begin() as session:
        device = Device(
            family_id=family_id,
            member_id=member_id,
            platform="web",
            label=f"{SIM_LABEL_PREFIX}{scenario_id}",
            app_version="sim-1",
            rules_version="sim-1",
            device_secret_hash=secrets.token_hex(32),  # băm ngẫu nhiên: thiết bị mô phỏng không có bí mật dùng được
        )
        session.add(device)
        await session.flush()
        return device.id


def _resolve_mode(requested: str, replay_open: bool) -> LlmMode:
    if requested == "replay":
        return "replay" if replay_open else "fallback"
    return "live" if get_settings().anthropic_api_key else "fallback"


async def start_run(guardian_id: UUID, family_id: UUID, scenario_id: str, llm: str) -> dict[str, Any]:
    if not CASE_ID.fullmatch(scenario_id):
        raise SimError(404, "Không có kịch bản này")
    try:
        case = load_case(scenario_id)
    except (FileNotFoundError, ValueError, KeyError):
        raise SimError(404, "Không có kịch bản này") from None
    member_id = await _demo_family_member(family_id)
    event = _sim_event(scenario_id)
    if event is None:  # luật trên máy không bật: không có sự cố, không tốn hạn mức
        return _view(case.id, "replay" if llm == "replay" else "fallback", None, None, None, [], NO_RULE_NOTE)
    now = time.monotonic()
    _check_hourly(guardian_id, now)
    if await _active_sim_incidents(family_id) >= MAX_ACTIVE_PER_FAMILY:
        raise SimError(429, "Đang có quá nhiều lượt mô phỏng chưa xong, hãy kết thúc bớt rồi thử lại.", 30)
    _starts[guardian_id].append(now)

    replay = await _open_replay(case.id) if llm == "replay" else None
    registered = False
    mode = _resolve_mode(llm, replay is not None)
    try:
        device_id = await _new_sim_device(family_id, member_id, case.id)
        ingested = await ingest_events(
            [event],
            device_id=device_id,
            family_id=family_id,
            member_id=member_id,
            guardian_alerts=True,  # gia đình demo: bỏ qua cổng đồng ý (không có người thật), tin vẫn chỉ ghi mock
            sim=True,
            defer_graph=True,
        )
        if ingested.incident_id is None or not ingested.pending_starts:
            raise SimError(500, "Không mở được sự cố mô phỏng")
        incident, started = ingested.pending_starts[0]
        async with get_sessionmaker().begin() as session:
            payload = await start_graph_payload(session, incident, started, guardian_alerts=True, sim=True)
        runtime = replay[0] if replay else await ensure_runtime()
        entry = _Entry(
            mode, time.monotonic() + RUNTIME_TTL_S, replay[0] if replay else None, replay[1] if replay else None
        )
        _registry[incident.id] = entry
        registered = True
        await _prune(time.monotonic())
        await runtime.start_prepared(
            payload["event"],
            payload["threat"],
            incident_id=payload["incident_id"],
            elder_alias=payload["elder_alias"],
            family_id=payload["family_id"],
            is_demo=True,
            guardian_alerts=True,
            sim=True,
        )
    except BaseException:
        if replay is not None and not registered:
            await replay[1].aclose()
        raise
    return await view(incident.id, family_id)


# --- khung nhìn ----------------------------------------------------------------------------------------------------


def _view(
    scenario_id: str,
    mode: LlmMode,
    incident: Incident | None,
    run_id: UUID | None,
    pending: dict[str, Any] | None,
    messages: list[dict[str, Any]],
    note: str | None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "is_demo": True,
        "llm_mode": mode,
        "incident_id": str(incident.id) if incident else None,
        "run_id": str(run_id) if run_id else None,
        "state": incident.state if incident else None,
        "level": incident.level if incident else "none",
        "pending_question": pending,
        "guardian_messages": messages,
        "note": note,
    }


async def _sim_incident(session: Any, incident_id: UUID, family_id: UUID) -> tuple[Incident, str] | None:
    """(sự cố, mã kịch bản) của sự cố MÔ PHỎNG thuộc gia đình phiên; sự cố thật/nhà khác ⇒ None ⇒ 404 (không lộ)."""
    row = (
        await session.execute(
            select(Incident, Device.label)
            .join(Device, Device.id == Incident.device_id)
            .where(
                Incident.id == incident_id,
                Incident.family_id == family_id,
                Device.label.startswith(SIM_LABEL_PREFIX),
            )
        )
    ).one_or_none()
    return None if row is None else (row[0], row[1].removeprefix(SIM_LABEL_PREFIX))


async def _messages(session: Any, incident_id: UUID) -> list[dict[str, Any]]:
    rows = await session.execute(
        select(Job.payload, Job.created_at)
        .where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{incident_id}:msg:", autoescape=True))
        .order_by(Job.created_at, Job.idempotency_key)
        .limit(MAX_MESSAGES)
    )
    return [
        {
            "at": created.isoformat(),
            "template": str(payload.get("template", "unknown"))[:32],
            "text": mask_text(str(payload["text"]).replace(texts.ACTION_LINK_SLOT, LINK_PLACEHOLDER))[:1000],
        }
        for payload, created in rows
        if payload.get("sim") and payload.get("text")
    ]


async def _pending_question(incident: Incident, runtime: IncidentRuntime) -> dict[str, Any] | None:
    if incident.state in TERMINAL:
        return None
    run = await runtime.status(str(incident.id))
    if run.waiting_for != "ask_elder" or not run.interrupt:
        return None
    question_id = run.interrupt["question_id"]
    async with get_sessionmaker()() as session:
        expires_at = await session.scalar(
            select(Job.run_at).where(Job.idempotency_key == f"{incident.id}:timer:ask_elder")
        )
    return {
        "incident_id": str(incident.id),
        "question_id": question_id,
        "text": texts.question_for_elder(question_id, False),
        "is_drill": False,
        "answers": list(texts.ANSWERS),
        "expires_at": (expires_at or datetime.now(UTC) + timedelta(seconds=60)).isoformat(),
    }


async def view(incident_id: UUID, family_id: UUID) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        found = await _sim_incident(session, incident_id, family_id)
        if found is None:
            raise SimError(404, "Không tìm thấy")
        incident, scenario_id = found
        run_id = await session.scalar(select(AgentRun.id).where(AgentRun.thread_id == str(incident_id)))
        messages = await _messages(session, incident_id)
    runtime, mode = await _runtime_for(incident_id)
    pending = await _pending_question(incident, runtime)
    return _view(scenario_id, mode, incident, run_id, pending, messages, None)


async def answer(incident_id: UUID, family_id: UUID, value: dict[str, Any], question_id: str) -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        found = await _sim_incident(session, incident_id, family_id)
    if found is None:
        raise SimError(404, "Không tìm thấy")
    incident = found[0]
    runtime, _ = await _runtime_for(incident_id)
    pending = await _pending_question(incident, runtime)
    if pending is None or pending["question_id"] != question_id:
        raise SimError(409, "Câu hỏi này không còn chờ trả lời")
    status = await runtime.resume(str(incident_id), value, expect="ask_elder")
    if status is None:
        raise SimError(409, "Câu hỏi này không còn chờ trả lời")
    return await view(incident_id, family_id)
