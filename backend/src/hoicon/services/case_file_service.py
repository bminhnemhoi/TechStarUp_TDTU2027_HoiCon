"""Hồ sơ vụ việc (spec 031): dựng `content` TẤT ĐỊNH từ dữ kiện máy chủ đã có (FR-004). Không số điện thoại đầy đủ, h1,
HMAC, tên gói, lời kể tự do hay tên thật: chỉ khóa enum ⇒ câu cố định (`agents/texts.py`), 3 số cuối, bí danh gia đình.
Khớp `docs/schemas/case_file.v1.json#/$defs/content`."""

import logging
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.agents import texts
from hoicon.agents.llm_router import LlmRouter, load_prompt
from hoicon.db.models import (
    AgentRun,
    AgentStep,
    CaseFile,
    Incident,
    IncidentTransition,
    Member,
    RiskEventRecord,
    Verification,
)
from hoicon.domain.pii import mask_text

logger = logging.getLogger(__name__)

CONTENT_LEVELS = ("low", "medium", "high", "critical")
APP_CATEGORIES = {"bank", "wallet", "securities", "sideloaded", "remote_control"}
VERDICTS = {
    "dangerous": "dangerous",
    "warning": "warning",
}  # phán quyết khác (safe/unknown) ⇒ "unknown": chưa thấy cảnh báo


def _line(text: str) -> str:
    return text[:300]


async def _event(session: AsyncSession, incident: Incident) -> RiskEventRecord | None:
    if incident.opened_by_event_id is not None:
        found = await session.get(RiskEventRecord, incident.opened_by_event_id)
        if found is not None:
            return found
    return await session.scalar(
        select(RiskEventRecord)
        .where(RiskEventRecord.incident_id == incident.id)
        .order_by(RiskEventRecord.occurred_at)
        .limit(1)
    )


async def _answers(session: AsyncSession, incident_id: UUID) -> list[dict[str, str]]:
    """Câu trả lời E8 theo thứ tự: `ask_elder.output` chỉ có `question_id` + `answer` (mã), không lời kể."""
    rows = await session.scalars(
        select(AgentStep)
        .join(AgentRun, AgentRun.id == AgentStep.run_id)
        .where(AgentRun.thread_id == str(incident_id), AgentStep.node == "ask_elder")
        .order_by(AgentStep.at, AgentStep.id)
    )
    out = []
    for step in rows:
        output = step.output or {}
        question, answer = output.get("question_id"), output.get("answer")
        if question in texts.QUESTIONS and answer in texts.ANSWER_VI:
            out.append({"question_id": question, "answer": answer})
    return out


async def _threat_flagged(session: AsyncSession, incident_id: UUID) -> bool:
    step = await session.scalar(
        select(AgentStep)
        .join(AgentRun, AgentRun.id == AgentStep.run_id)
        .where(AgentRun.thread_id == str(incident_id), AgentStep.node == "ingest")
        .order_by(AgentStep.at)
        .limit(1)
    )
    return bool(step and (step.output or {}).get("threat") == "flagged")


def _decision(transitions: list[IncidentTransition]) -> str:
    """`graph_scam` ⇒ người nhà chọn "lừa đảo" (Zalo 2); đường khác tới `case_open` là `emergency_pause`."""
    for t in transitions:
        if t.to_state == "case_open":
            return "scam" if (t.reason or "").endswith("scam") else "emergency_pause"
    return "emergency_pause"


async def build_content(session: AsyncSession, incident_id: UUID, summary: str | None = None) -> dict[str, Any]:
    """`content` của hồ sơ cho sự cố đã/đang ở `case_open`. `summary` (đã lọc) thay câu mẫu nếu có."""
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise LookupError("Không có sự cố")
    from hoicon.agents.runtime import safe_alias  # nạp muộn: runtime nạp đồ thị, đồ thị nạp module này

    member = await session.get(Member, incident.member_id)
    alias = safe_alias(member.alias if member else None)
    event = await _event(session, incident)
    transitions = list(
        await session.scalars(
            select(IncidentTransition)
            .where(IncidentTransition.incident_id == incident_id)
            .order_by(IncidentTransition.at, IncidentTransition.id)
        )
    )
    answers = await _answers(session, incident_id)
    said = {(a["question_id"], a["answer"]) for a in answers}
    app = event.app_category if event and event.app_category in APP_CATEGORIES else "none"
    authority = ("q_caller_authority", "yes") in said
    transfer = ("q_asked_transfer", "yes") in said
    reasons = []
    if await _threat_flagged(session, incident_id):
        reasons.append("flagged")
    if authority:
        reasons.append("authority")
    if transfer:
        reasons.append("transfer")
    if ("q_know_caller", "no") in said:
        reasons.append("unknown_caller")
    if app == "sideloaded":
        reasons.append("sideloaded")
    if not reasons:
        reasons.append("floor")
    level = incident.level if incident.level in CONTENT_LEVELS else "low"
    verifications = (
        await session.scalars(
            select(Verification)
            .where(Verification.incident_id == incident_id, Verification.kind.in_(("phone", "url")))
            .order_by(Verification.at, Verification.id)
        )
    ).all()
    timeline = [
        {"at": t.at.isoformat(), "text": _line(texts.TRANSITION_VI.get(t.to_state, "HỏiCon cập nhật sự cố"))}
        for t in transitions
    ] or [{"at": incident.opened_at.isoformat(), "text": texts.TRANSITION_VI["detected"]}]
    return {
        "schema_version": 1,
        "ai_label": texts.CASE_FILE_AI_LABEL,
        "summary": summary or texts.case_file_summary(alias, app, level, authority, transfer),
        "elder_alias": alias,
        "level": level,
        "reasons": [_line(texts.CASE_REASON_VI[r]) for r in reasons],
        "rule": _line(texts.RULE_VI.get(event.rule_id if event and event.rule_id else "", texts.RULE_DEFAULT_VI)),
        "caller_last3": event.caller_last3 if event and event.caller_last3 else None,
        "app_category": app,
        "timeline": timeline[:50],
        "elder_answers": [
            {"question": _line(texts.QUESTIONS[a["question_id"]]), "answer": texts.ANSWER_VI[a["answer"]]}
            for a in answers
        ][:10],
        "verifications": [
            {
                "kind": "phone" if v.kind == "phone" else "link",
                "verdict": VERDICTS.get(v.verdict, "unknown"),
                "source": str((v.sources[0].get("name") if v.sources else None) or texts.VERIFICATION_SOURCE_DEFAULT)[
                    :80
                ],
                "list_version": v.list_version,
            }
            for v in verifications
        ][:20],
        "guardian_decision": _decision(transitions),
        "local_fields": [dict(f) for f in texts.CASE_LOCAL_FIELDS],
    }


# --- Đoạn tóm tắt do LLM (FR-005): tùy chọn, lọc nghiêm, hỏng ⇒ câu mẫu ----------------------------------------
MAX_SUMMARY = 600
_UNSAFE_TEXT = re.compile(
    # Mọi chữ số (số tiền bịa là rủi ro lớn nhất của tờ trình báo), tiền viết bằng chữ, link, kênh chat.
    r"\d|https?://|www\.|@|\b[\w-]+\.(?:vn|com|net|org|me|ly|io|xyz|info|top|link|site)\b|zalo|telegram|viber|"
    r"\b(?:triệu|nghìn|ngàn|trăm|tỷ|tỉ|đồng|vnđ|usd)\b",
    re.IGNORECASE,
)
# Lời khuyên nguy hiểm / hứa hẹn không giữ được (luật 13): đối chiếu bằng cụm từ nên chỉ là lớp lọc thô.
_UNSAFE_ADVICE = re.compile(
    r"đừng báo|không cần báo|cứ chuyển|nên chuyển tiền|an toàn rồi|không sao đâu|hoàn tiền|lấy lại được tiền|"
    r"đã báo (?:công an|cơ quan)|đã gửi cho (?:công an|cơ quan)|đã trình báo|công an đã|tiền sẽ về|chắc chắn là lừa|"
    r"đã bị mất|bị mất tiền|đã mất",
    re.IGNORECASE,
)


class CaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(max_length=MAX_SUMMARY)


def safe_summary(text: str, alias: str) -> str | None:
    """Đoạn LLM sau lọc (thay `{alias}`, che PII); None nếu rỗng, quá dài hoặc có số/link/lời khuyên nguy hiểm."""
    text = unicodedata.normalize("NFC", text).strip().replace("{alias}", alias)
    if not text or len(text) > MAX_SUMMARY:
        return None
    if _UNSAFE_TEXT.search(text) or _UNSAFE_ADVICE.search(text) or mask_text(text) != text:
        return None
    return text


async def llm_summary(router: LlmRouter, facts: dict[str, Any], alias: str) -> str | None:
    """Một lời gọi qua `llm_router` (che PII, ngân sách, timeout ≤ 4 s). Không khóa/hỏng/quá hạn/bị lọc ⇒ None.
    (Hồ sơ `strong` chưa có trong router: dùng hồ sơ `fast` hiện có.)"""
    fallback = CaseSummary(summary=texts.case_file_summary(alias, "none", "high", False, False))
    context = {"elder_alias": "{alias}", **facts}
    result = await router.structured(
        prompt=load_prompt("case_file"), context=context, output=CaseSummary, fallback=fallback, max_tokens=400
    )
    if result.fallback_used:
        return None
    return safe_summary(result.output.summary, alias)


async def save_draft(
    sessions: async_sessionmaker,
    *,
    incident_id: UUID,
    family_id: UUID,
    content: dict[str, Any],
    summary_source: str,
    is_demo: bool,
) -> bool:
    """Ghi bản nháp; lũy đẳng (UNIQUE `incident_id`): node chạy lại không nhân bản. ⇒ True nếu vừa tạo."""
    async with sessions.begin() as session:
        created = await session.scalar(
            insert(CaseFile)
            .values(
                incident_id=incident_id,
                family_id=family_id,
                content=content,
                summary_source=summary_source,
                is_demo=is_demo,
            )
            .on_conflict_do_nothing(index_elements=[CaseFile.incident_id])
            .returning(CaseFile.id)
        )
    return created is not None


# --- Máy trạng thái hồ sơ (FR-007) -------------------------------------------------------------------------------
ACTIONS = ("approve", "discard", "mark_sent")
NEXT_STATUS = {
    ("draft", "approve"): "approved",
    ("draft", "discard"): "discarded",
    ("approved", "mark_sent"): "sent",
    ("approved", "discard"): "discarded",
}


class CaseFileConflictError(Exception):
    """Lệnh không hợp lệ với trạng thái hiện tại của hồ sơ (⇒ 409)."""


async def apply_action(
    session: AsyncSession, incident_id: UUID, action: str, *, actor: str, member_id: UUID | None
) -> CaseFile:
    """Áp một lệnh lên hồ sơ của sự cố, trong giao dịch của người gọi. `approve`/`discard` xếp job resume đồ thị (đang
    chờ ở `await_case_approval`); `discard`/`mark_sent` đóng sự cố `case_open → closed` qua `IncidentService`. Không
    ghi nội dung ô tự điền (không bao giờ tới máy chủ). Lỗi: `LookupError`, `CaseFileConflictError`."""
    from hoicon.jobs.queue import enqueue
    from hoicon.services.incident_service import IncidentService

    row = await session.scalar(select(CaseFile).where(CaseFile.incident_id == incident_id).with_for_update())
    if row is None:
        raise LookupError("Không có hồ sơ")
    target = NEXT_STATUS.get((row.status, action))
    if target is None:
        raise CaseFileConflictError(f"{row.status}:{action}")
    now = func.now()
    row.status = target
    if action == "approve":
        row.approved_at, row.approved_by = now, member_id
    elif action == "mark_sent":
        row.sent_at = now
    else:
        row.discarded_at = now
    if action in ("approve", "discard"):
        value = {"case_action": action, "actor": actor}
        await enqueue(
            session,
            "graph_resume",
            {"thread_id": str(incident_id), "expect": "await_case_approval", "value": value},
            key=f"{incident_id}:case_action:{action}",
        )
    if action in ("discard", "mark_sent"):
        incident = await session.get(Incident, incident_id, populate_existing=True)
        if incident is not None and incident.state == "case_open":
            reason = "case_sent" if action == "mark_sent" else "case_discarded"
            await IncidentService.transition(
                session, incident_id, "closed", actor, reason, expected_version=incident.version
            )
    await session.flush()
    await session.refresh(row)
    return row


# --- Đóng tự động (FR-008) -------------------------------------------------------------------------------------
AUTOCLOSE_AFTER = timedelta(days=30)


async def run_autoclose(
    sessions: async_sessionmaker, *, now: datetime | None = None, family_id: UUID | None = None
) -> int:
    """Sự cố `case_open` không hoạt động 30 ngày ⇒ `closed` (actor `system`); hồ sơ còn `draft` ⇒ `discarded` (resume
    đồ thị `discard`/`system`); hồ sơ `approved`/`sent` giữ nguyên trạng thái. Lũy đẳng. `family_id` chỉ để test thu hẹp
    phạm vi (đồng hồ giả không được đóng sự cố của người khác trong DB dùng chung). ⇒ số sự cố đã đóng."""
    from hoicon.services.incident_service import IncidentService

    cutoff = (now or datetime.now(UTC)) - AUTOCLOSE_AFTER
    last = func.coalesce(
        select(func.max(IncidentTransition.at)).where(IncidentTransition.incident_id == Incident.id).scalar_subquery(),
        Incident.opened_at,
    )
    async with sessions() as session:
        query = select(Incident.id).where(Incident.state == "case_open", last < cutoff)
        if family_id is not None:
            query = query.where(Incident.family_id == family_id)
        stale = list(await session.scalars(query))
    closed = 0
    for incident_id in stale:
        try:
            async with sessions.begin() as session:
                case = await session.scalar(select(CaseFile).where(CaseFile.incident_id == incident_id))
                if case is not None and case.status == "draft":
                    await apply_action(session, incident_id, "discard", actor="system", member_id=None)
                else:
                    incident = await session.get(Incident, incident_id, populate_existing=True)
                    if incident is None or incident.state != "case_open":
                        continue
                    await IncidentService.transition(
                        session, incident_id, "closed", "system", "case_autoclose", expected_version=incident.version
                    )
            closed += 1
        except Exception as exc:  # một sự cố lỗi/đua với người dùng không được chặn các sự cố còn lại; lần sau thử lại
            logger.warning("case_autoclose: bỏ qua một sự cố (%s)", type(exc).__name__)
    return closed


def autoclose_key(now: datetime) -> str:
    from hoicon.services.retention_service import VN_TZ

    return f"case_autoclose:{now.astimezone(VN_TZ).date().isoformat()}"


async def schedule_daily_autoclose(sessions: async_sessionmaker, *, now: datetime | None = None) -> str:
    """Xếp job `case_autoclose` của ngày hôm nay (lũy đẳng nhờ khóa), cùng nhịp với job `retention`."""
    from hoicon.jobs.queue import enqueue

    key = autoclose_key(now or datetime.now(UTC))
    await enqueue(sessions, "case_autoclose", {}, key=key)
    return key
