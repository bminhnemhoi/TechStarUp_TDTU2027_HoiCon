"""Đồ thị sự cố (AGENTS.md) — bản spike P1-S4:

    ingest → fast_alert → risk_scorer ⇄ [INTERRUPT ask_elder] → verification → intervention
           → [INTERRUPT await_guardian ⟲ T1/T2/evidence] → resolve

- `fast_alert` không dùng LLM: tin mẫu tới người giám hộ ngay khi có sự cố (đường cảnh báo không phụ thuộc LLM).
- LLM (`risk_scorer`, `intervention`) chỉ NÂNG mức rủi ro, không bao giờ dưới `rule_floor`; lỗi/quá hạn ⇒ mẫu soạn sẵn.
- Spec 026: `verification` KHÔNG dùng LLM (nguồn dẫn phải là dữ kiện có thật): gom các dòng `verifications` của sự cố,
  nâng mức bằng `max()` và ghi xuyên `incidents.level`. Bằng chứng đến giữa lúc chờ (`evidence`) được `await_guardian`
  (node được phép gửi tin) báo con đúng một lần.
- Tác dụng phụ (gửi tin, hẹn giờ) chỉ ở `fast_alert`, `ask_elder`, `intervention`, `await_guardian`, `resolve` và
  luôn qua hàng đợi job có khóa chống trùng: node chạy lại (interrupt chạy lại node từ đầu; kill -9) không gửi trùng.
- Mỗi node ghi một dòng `agent_steps` (đã che PII). Chuyển trạng thái sự cố qua `IncidentService.transition` ở P2-03.
- Spec 024: người giám hộ có thể quyết NGOÀI đồ thị (link `/a/`, JWT, Zalo 1/2 — spec 023). `intervention` và
  `await_guardian` đọc trạng thái sự cố trước khi gửi gì: đã quyết ⇒ không gửi chi tiết/nhắc/leo thang nữa, đi thẳng
  tới `resolve`; `resolve` ghi kết quả của chính đồ thị (T3 không ai trả lời, "lừa đảo" ⇒ `case_open`) qua
  `IncidentService`.
"""

import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Any, Literal, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents import texts
from hoicon.agents.llm_router import LlmResult, LlmRouter, load_prompt
from hoicon.channels.fcm import notify_elder_fcm
from hoicon.config import Settings
from hoicon.db.models import AgentRun, AgentStep, Verification
from hoicon.domain.risk import RiskLevel, raise_only
from hoicon.jobs.queue import cancel_prefix, enqueue
from hoicon.services.incident_service import (
    GRAPH_OUTCOMES,
    IncidentNotFoundError,
    IncidentService,
    close_from_graph,
    decided_state,
)

QuestionId = Literal["q_caller_authority", "q_asked_transfer", "q_know_caller", "none"]
Tactic = Literal[
    "impersonation_authority",
    "bank_security",
    "family_emergency",
    "investment_job",
    "refund_recovery",
    "unknown",
    "legit_likely",
]
Action = Literal["call_now", "call_and_stay_on_line", "visit_or_call_relative"]


class RiskAssessment(BaseModel):
    level: Literal["none", "low", "medium", "high", "critical"]
    tactic: Tactic
    reasons: list[str] = Field(max_length=3)
    ask_question: QuestionId


# ADR-012: LLM chỉ chọn mã điểm từ danh sách đóng; máy chủ ghép câu cố định (`texts.BRIEF_POINT_VI`). Khớp
# `docs/schemas/guardian_brief.v2.json` (test so enum).
BriefPoint = Literal[
    "unknown_call_then_finance_app",
    "sideloaded_app",
    "call_still_ongoing",
    "flagged_number",
    "caller_claims_authority",
    "asked_transfer_or_code",
    "asked_secrecy",
    "asked_install_app",
    "elder_unsure_of_caller",
    "common_scam_pattern",
    "may_be_routine",
]


class GuardianBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[BriefPoint] = Field(min_length=1, max_length=3)
    action: Action

    @field_validator("points")
    @classmethod
    def _unique(cls, value: list[BriefPoint]) -> list[BriefPoint]:
        if len(set(value)) != len(value):
            raise ValueError("points không được trùng")
        return value


def _append(left: list[str], right: list[str]) -> list[str]:
    return left + right


class IncidentState(TypedDict, total=False):
    incident_id: str
    run_id: str
    family_id: str  # UUID gia đình nhận tin; vắng khi sự cố không gắn gia đình (spec 002)
    sim: bool  # spec 033: sự cố mô phỏng ⇒ tin người giám hộ không bao giờ gửi Zalo thật; vắng = False
    guardian_alerts: bool  # False ⇒ chưa đồng ý báo người giám hộ: không xếp tin Zalo (spec 034); vắng = True
    is_drill: bool
    is_demo: bool
    elder_alias: str
    event: dict[str, Any]  # RiskEvent đã kiểm, KHÔNG có h1 và tên gói (ADR-006)
    rule_floor: str
    level: str
    tactic: str
    reasons: list[str]
    threat: dict[str, Any]
    question_id: str | None
    elder_answer: dict[str, Any] | None
    action: str
    guardian_stage: int
    guardian_decision: str | None
    outcome: str | None
    outbox: Annotated[list[str], _append]  # mã các tin đã xếp hàng (trace), nội dung nằm trong job


# Tóm tắt LLM viết đi thẳng tới người giám hộ ⇒ có chữ số, đường link, tên miền, @, tên kênh chat là bỏ, dùng mẫu.
_UNSAFE_SUMMARY = re.compile(
    r"\d|https?://|www\.|@|\b[\w-]+\.(?:vn|com|net|org|me|ly|io|xyz|info|top|link|site)\b|zalo|telegram|viber",
    re.IGNORECASE,
)


_FINANCE_APPS = ("bank", "wallet", "securities")


def _note_flag(state: Mapping[str, Any], *names: str) -> bool:
    flags = (state.get("elder_answer") or {}).get("note_flags") or {}
    return any(flags.get(n) is True for n in names)


def _answered(state: Mapping[str, Any], question: str, *values: str) -> bool:
    ans = state.get("elder_answer") or {}
    return ans.get("question_id") == question and ans.get("answer") in values


def _brief_conditions(state: Mapping[str, Any], level: RiskLevel) -> dict[str, bool]:
    """Điều kiện dữ kiện tất định của từng mã điểm (ADR-012 §2): chỉ đọc state máy chủ, không đọc chữ của LLM."""
    event = state.get("event") or {}
    app = (event.get("app") or {}).get("category")
    flagged = (state.get("threat") or {}).get("verdict") == "flagged" or bool(
        (event.get("caller") or {}).get("flagged")
    )
    danger = {
        "caller_claims_authority": _answered(state, "q_caller_authority", "yes")
        or _note_flag(state, "mentions_authority"),
        "asked_transfer_or_code": _answered(state, "q_asked_transfer", "yes")
        or _note_flag(state, "mentions_transfer", "mentions_code"),
        "asked_secrecy": _note_flag(state, "mentions_secrecy"),
        "asked_install_app": _note_flag(state, "mentions_app_or_link"),
    }
    return {
        "unknown_call_then_finance_app": app in _FINANCE_APPS,
        "sideloaded_app": app == "sideloaded",
        "call_still_ongoing": (event.get("call") or {}).get("active") is True,
        "flagged_number": flagged,
        **danger,
        "elder_unsure_of_caller": _answered(state, "q_know_caller", "no", "unsure"),
        "common_scam_pattern": True,
        # LLM không được trấn an ở mức high/critical (luật 5), cũng không khi đã có dữ kiện nguy hiểm (số gắn cờ, người
        # gọi xưng cơ quan/đòi tiền/đòi giữ kín/đòi cài app): mức có thể thấp chỉ vì LLM chấm thấp.
        "may_be_routine": level.rank <= RiskLevel.MEDIUM.rank and not flagged and not any(danger.values()),
    }


def brief_points(state: Mapping[str, Any], level: RiskLevel, points: Sequence[str]) -> list[str]:
    """Điểm LLM chọn, bỏ mã lạ/trùng/điều kiện sai, giữ thứ tự; rỗng ⇒ bộ mặc định (mã ứng dụng đúng + chung)."""
    conditions = _brief_conditions(state, level)
    kept: list[str] = []
    for point in points:
        if conditions.get(point) and point not in kept:
            kept.append(point)
    if kept:
        return kept[:3]
    return [p for p in ("unknown_call_then_finance_app", "sideloaded_app") if conditions[p]] + ["common_scam_pattern"]


@dataclass
class Deps:
    router: LlmRouter
    sessions: async_sessionmaker
    settings: Settings


# Câu trả lời E8 nói rõ dấu hiệu lừa đảo ⇒ mức tối thiểu (tất định, không phụ thuộc LLM — SC-002).
_ANSWER_FLOOR: dict[tuple[str, str], RiskLevel] = {
    ("q_asked_transfer", "yes"): RiskLevel.CRITICAL,
    ("q_caller_authority", "yes"): RiskLevel.HIGH,
    ("q_know_caller", "no"): RiskLevel.HIGH,
}
DECIDED = "decided"  # người giám hộ đã quyết ngoài đồ thị; kết quả thật nằm ở `incidents.state`


def _incident_uuid(state: IncidentState) -> UUID | None:
    """Id sự cố thật; lượt eval (`eval-…`) và demo không gắn sự cố trong bảng `incidents`."""
    try:
        return UUID(state["incident_id"])
    except ValueError:
        return None


# Sơ đồ đồ thị cho web (spec 033 FR-009): nhãn tiếng Việt, nút chờ người, và tên `agent_steps.node` của từng nút (nút
# `verification` ghi bước tên `verify`). Thêm nút mới mà quên bảng này ⇒ `graph_topology()` báo lỗi (có test).
NODE_LABELS_VI: dict[str, str] = {
    "ingest": "Nhận sự kiện",
    "fast_alert": "Báo nhanh người giám hộ",
    "risk_scorer": "Chấm rủi ro",
    "ask_elder": "Hỏi bác",
    "verification": "Xác minh",
    "intervention": "Soạn tin cho con",
    "await_guardian": "Chờ người giám hộ",
    "resolve": "Kết thúc sự cố",
}
INTERRUPT_NODES = frozenset({"ask_elder", "await_guardian"})
STEP_NODES: dict[str, list[str]] = {"verification": ["verify"]}  # còn lại: tên nút = tên bước


def build_graph(deps: Deps) -> StateGraph:
    risk_prompt = load_prompt("risk_scorer")
    brief_prompt = load_prompt("intervention")

    async def decided(state: IncidentState) -> str | None:
        incident_id = _incident_uuid(state)
        if incident_id is None:
            return None
        async with deps.sessions() as session:
            return await decided_state(session, incident_id)

    async def step(
        state: IncidentState,
        node: str,
        started: float,
        output: dict[str, Any],
        llm: LlmResult | None = None,
        input_redacted: dict[str, Any] | None = None,
    ) -> None:
        cost = llm.cost_usd if llm else Decimal(0)
        async with deps.sessions.begin() as session:
            session.add(
                AgentStep(
                    run_id=UUID(state["run_id"]),
                    node=node,
                    model_profile="fast" if llm else None,
                    model=llm.model if llm and not llm.fallback_used else None,
                    prompt_version=llm.prompt_version if llm else None,
                    input_redacted=llm.input_redacted if llm else input_redacted,
                    output=output,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    tokens_in=llm.tokens_in if llm else 0,
                    tokens_out=llm.tokens_out if llm else 0,
                    cost_usd=cost,
                    fallback_used=llm.fallback_used if llm else False,
                    error=llm.error if llm else None,
                )
            )
            if cost:
                await session.execute(
                    update(AgentRun)
                    .where(AgentRun.id == UUID(state["run_id"]))
                    .values(cost_usd=AgentRun.cost_usd + cost)
                )

    async def notify(state: IncidentState, template: str, text: str, guardian_rank: int = 1) -> list[str]:
        """Xếp tin cho người giám hộ (Zalo ở P1-S3/P2-07, qua bộ kiểm hạn mức `messages_out`)."""
        if state.get("guardian_alerts", True) is False:  # spec 034 FR-005: không có đồng ý thì không có tin
            return []
        key = f"{state['incident_id']}:msg:{template}"
        payload = {
            "incident_id": state["incident_id"],
            "family_id": state.get("family_id"),  # None khi chưa gắn gia đình (checkpoint cũ cũng đọc được)
            "template": template,
            "text": text,
            "guardian_rank": guardian_rank,
            # luật 8: bên gửi Zalo phải biết đây là diễn tập/demo (chặn số hư cấu, không báo như sự cố thật)
            "is_drill": state["is_drill"],
            "is_demo": state.get("is_demo", False),
        }
        if state.get("sim"):
            payload["sim"] = True
        await enqueue(deps.sessions, "notify_guardian", payload, key=key)
        return [template]

    async def timer(state: IncidentState, name: str, after_s: int, expect: str, value: dict[str, Any]) -> None:
        """Hẹn giờ resume đồ thị. Khóa theo tên ⇒ node chạy lại không dời mốc giờ đã đặt."""
        await enqueue(
            deps.sessions,
            "graph_resume",
            {"thread_id": state["incident_id"], "expect": expect, "value": value},
            delay_s=after_s,
            key=f"{state['incident_id']}:timer:{name}",
        )

    def context(state: IncidentState) -> dict[str, Any]:
        event = state["event"]
        return {
            "rule_floor": state["rule_floor"],
            "current_level": state["level"],
            "rule_id": event.get("rule_id"),
            "app_category": (event.get("app") or {}).get("category"),
            "call": event.get("call"),
            "caller_in_contacts": (event.get("caller") or {}).get("in_contacts"),
            "threat_verdict": state.get("threat", {}).get("verdict"),
            "elder_answer": state.get("elder_answer"),
            "is_drill": state["is_drill"],
        }

    async def ingest(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        caller = state["event"].get("caller")
        threat = state.get("threat") or {"verdict": "unknown"}  # đã tra ở runtime.start (h1 không vào state)
        flagged = threat["verdict"] == "flagged" or bool(caller and caller.get("flagged"))
        floor = RiskLevel(state["rule_floor"])
        level = raise_only(floor, RiskLevel.CRITICAL if flagged else None)
        output = {"level": level, "threat": threat["verdict"]}
        await step(state, "ingest", started, output, input_redacted={"event_type": state["event"]["type"]})
        return {"level": level.value, "guardian_stage": 0, "outbox": []}

    async def fast_alert(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        event = state["event"]
        text = texts.guardian_fast_alert(
            state["elder_alias"],
            (event.get("caller") or {}).get("last3"),
            (event.get("app") or {}).get("category", "other"),
            state["is_drill"],
        )
        sent = await notify(state, "fast_alert", text)
        await step(state, "fast_alert", started, {"template": "fast_alert"})
        return {"outbox": sent, "guardian_stage": 1}

    async def risk_scorer(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        floor = RiskLevel(state["rule_floor"])
        elder_ans = state.get("elder_answer")
        answered = elder_ans is not None
        forced_level = _ANSWER_FLOOR.get((elder_ans.get("question_id"), elder_ans.get("answer"))) if elder_ans else None
        fallback = RiskAssessment(
            level=(forced_level or RiskLevel(state["level"])).value,
            tactic="unknown",
            reasons=[
                "Người cao tuổi xác nhận dấu hiệu lừa đảo ở câu hỏi nhanh"
                if forced_level
                else "Dùng mức sàn của luật trên máy (chưa có đánh giá AI)"
            ],
            ask_question="none" if answered else "q_asked_transfer",
        )
        # Không có văn bản tự do nào: lời kể của người cao tuổi chỉ còn là cờ tất định (runtime.clean_resume).
        llm = await deps.router.structured(
            prompt=risk_prompt, context=context(state), output=RiskAssessment, fallback=fallback
        )
        assessed = llm.output
        level = raise_only(floor, RiskLevel(state["level"]), RiskLevel(assessed.level), forced_level)
        question = None if answered or assessed.ask_question == "none" else assessed.ask_question
        output = {"level": level, "tactic": assessed.tactic, "question": question, "llm_level": assessed.level}
        await step(state, "risk_scorer", started, output, llm)
        return {"level": level.value, "tactic": assessed.tactic, "reasons": assessed.reasons, "question_id": question}

    async def ask_elder(state: IncidentState) -> dict[str, Any]:
        # Chạy lại từ đầu khi resume ⇒ mọi thứ trước interrupt() phải idempotent (job có khóa).
        started = time.monotonic()
        question_id = state["question_id"] or "q_asked_transfer"
        text = texts.question_for_elder(question_id, state["is_drill"])
        await timer(state, "ask_elder", deps.settings.timer_ask_elder_s, "ask_elder", {"timeout": True})
        await notify_elder_fcm(
            deps.sessions, incident_id=state["incident_id"], question_id=question_id, is_drill=state["is_drill"]
        )
        answer = interrupt(
            {"kind": "ask_elder", "question_id": question_id, "text": text, "answers": list(texts.ANSWERS)}
        )
        # `answer` đã qua runtime.clean_resume. Hẹn giờ ask_elder để nguyên: đến muộn thì `expect` bỏ qua, còn nếu tiến
        # trình chết ngay sau đây thì chính nó gỡ kẹt cho sự cố.
        elder_answer = {"question_id": question_id, "answer": answer.get("answer", "timeout")}
        if answer.get("note_flags"):
            elder_answer["note_flags"] = answer["note_flags"]
        await step(state, "ask_elder", started, elder_answer)
        return {"elder_answer": elder_answer}

    async def verification(state: IncidentState) -> dict[str, Any]:
        """Tất định: `level = max(state.level, sàn từ các kết luận xác minh của sự cố)`, ghi xuyên `incidents.level` (cả
        mức `risk_scorer` đã nâng). Không bao giờ hạ. Lượt eval/demo không có sự cố thật ⇒ bỏ qua DB."""
        started = time.monotonic()
        before = RiskLevel(state["level"])
        incident_id = _incident_uuid(state)
        if incident_id is None:
            await step(state, "verify", started, {"skipped": "no_incident"})
            return {}
        counts = {"dangerous": 0, "warning": 0}
        found = True
        async with deps.sessions.begin() as session:
            verdicts = await session.scalars(
                select(Verification.verdict).where(Verification.incident_id == incident_id)
            )
            checked = 0
            for verdict in verdicts:
                checked += 1
                if verdict in counts:
                    counts[verdict] += 1
            floor = RiskLevel.CRITICAL if counts["dangerous"] else RiskLevel.HIGH if counts["warning"] else None
            after = raise_only(before, floor)
            if after is not RiskLevel.NONE:  # `raise_level` từ chối NONE; mức NONE thì không có gì để ghi xuyên
                try:
                    stored = await IncidentService.raise_level(session, incident_id, after, "graph_verify")
                    after = raise_only(
                        after, RiskLevel(stored.level)
                    )  # DB có thể đã cao hơn (tra cứu/correlate chen vào)
                except IncidentNotFoundError:  # id hợp lệ nhưng không có dòng `incidents` (demo): chỉ đồ thị nâng mức
                    found = False
        output: dict[str, Any] = {
            "checked": checked,
            **counts,
            "level_before": before.value,
            "level_after": after.value,
        }
        if not found:
            output["skipped"] = "no_incident"
        await step(state, "verify", started, output)
        return {"level": after.value}

    async def evidence_message(state: IncidentState, verification_id: str) -> list[str]:
        """Tin `evidence`: chỉ cho dòng xác minh `dangerous` thuộc ĐÚNG sự cố này; còn lại không gửi gì."""
        incident_id = _incident_uuid(state)
        if incident_id is None:
            return []
        async with deps.sessions() as session:
            row = (
                await session.execute(
                    select(Verification.kind, Verification.last3).where(
                        Verification.id == UUID(verification_id),
                        Verification.incident_id == incident_id,
                        Verification.verdict == "dangerous",
                    )
                )
            ).first()
        if row is None:
            return []
        text = texts.guardian_evidence(state["elder_alias"], row.kind, row.last3, state["is_drill"])
        return await notify(state, "evidence", text)  # khóa theo mẫu ⇒ mỗi sự cố tối đa một tin

    async def intervention(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        if (done := await decided(state)) is not None:  # người giám hộ đã quyết: không gửi chi tiết thừa
            await step(state, "intervention", started, {"skipped": done})
            return {"guardian_decision": DECIDED}
        level = RiskLevel(state["level"])
        # Không còn câu mẫu tự do: fallback cũng chỉ là bộ điểm mặc định (ADR-012), câu ghép từ `BRIEF_POINT_VI`.
        fallback = GuardianBrief(
            points=brief_points(state, level, []),  # type: ignore[arg-type]
            action="call_and_stay_on_line" if level == RiskLevel.CRITICAL else "call_now",
        )
        # Chỉ siêu dữ liệu + enum; cách xưng hô thật không gửi cho LLM (chỗ giữ "{alias}" được thay sau).
        brief_context = {
            "elder_alias": "{alias}",
            "level": level.value,
            "tactic": state.get("tactic"),
            "elder_answer": state.get("elder_answer"),
            "is_drill": state["is_drill"],
        }
        llm = await deps.router.structured(
            prompt=brief_prompt, context=brief_context, output=GuardianBrief, fallback=fallback
        )
        # Chữ của LLM không bao giờ tới người giám hộ: chỉ giữ mã điểm có dữ kiện đúng, câu do `texts` ghép (ADR-012).
        chosen = list(llm.output.points)
        kept = brief_points(state, level, chosen)
        summary = texts.brief_summary(state["elder_alias"], kept)
        # Mức rất cao luôn kèm "gọi ngay và giữ máy" — LLM không được làm nhẹ lời khuyên.
        action = "call_and_stay_on_line" if level == RiskLevel.CRITICAL else llm.output.action
        text = texts.guardian_detail(state["elder_alias"], level, summary, action, state["is_drill"])
        sent = await notify(state, "detail", text)
        output = {
            "action": action,
            "template": "detail",
            "points_kept": kept,
            "points_dropped": [p for p in chosen if p not in kept],
        }
        await step(state, "intervention", started, output, llm)
        return {"outbox": sent, "action": action}

    async def await_guardian(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        # Chạy lại từ đầu ở MỖI lần resume (T1/T2/T3, Zalo): người giám hộ quyết qua `/a/` thì không nhắc/leo thang nữa.
        if await decided(state) is not None:
            await step(state, "await_guardian", started, {"resumed_with": DECIDED})
            return {"guardian_decision": DECIDED}
        s = deps.settings
        for name, after_s in (("t1", s.timer_t1_s), ("t2", s.timer_t2_s), ("t3", s.timer_t3_s)):
            await timer(state, name, after_s, "await_guardian", {"timer": name})
        value = interrupt({"kind": "await_guardian", "stage": state.get("guardian_stage", 1)})
        update_: dict[str, Any] = {}
        decision = value.get("decision") if isinstance(value, dict) else None
        timer_name = value.get("timer") if isinstance(value, dict) else None
        evidence = value.get("evidence") if isinstance(value, dict) else None
        if decision in ("safe", "scam"):
            update_["guardian_decision"] = decision
        elif timer_name == "t1":
            update_["outbox"] = await notify(
                state, "reminder", texts.guardian_reminder(state["elder_alias"], state["is_drill"])
            )
        elif timer_name == "t2":
            text = texts.guardian_escalation(state["elder_alias"], state["is_drill"])
            update_["outbox"] = await notify(state, "escalation", text, guardian_rank=2)
            update_["guardian_stage"] = 2
        elif timer_name == "t3":
            update_["guardian_decision"] = "no_response"
        elif evidence:  # kết quả tra cứu nguy hiểm đến giữa lúc chờ (spec 026): quay lại chờ sau khi báo con
            update_["outbox"] = await evidence_message(state, evidence)
        resumed = decision or timer_name or ("evidence" if evidence else "invalid")
        await step(state, "await_guardian", started, {"resumed_with": resumed})
        return update_

    async def resolve(state: IncidentState) -> dict[str, Any]:
        started = time.monotonic()
        decision = state["guardian_decision"] or "no_response"
        incident_id = _incident_uuid(state)
        if incident_id is None:  # eval/demo: không có sự cố để ghi
            outcome = GRAPH_OUTCOMES[decision][0] if decision != DECIDED else "decided"
        elif decision == DECIDED:
            async with deps.sessions() as session:
                outcome = await decided_state(session, incident_id) or "decided"
        else:
            async with deps.sessions.begin() as session:
                outcome = await close_from_graph(session, incident_id, decision)
        await cancel_prefix(deps.sessions, f"{state['incident_id']}:timer:")
        await step(state, "resolve", started, {"outcome": outcome, "level": state["level"]})
        return {"outcome": outcome}

    graph = StateGraph(IncidentState)
    for name, fn in (
        ("ingest", ingest),
        ("fast_alert", fast_alert),
        ("risk_scorer", risk_scorer),
        ("ask_elder", ask_elder),
        ("verification", verification),
        ("intervention", intervention),
        ("await_guardian", await_guardian),
        ("resolve", resolve),
    ):
        graph.add_node(name, fn)
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "fast_alert")
    graph.add_edge("fast_alert", "risk_scorer")
    graph.add_conditional_edges(
        "risk_scorer", lambda s: "ask_elder" if s.get("question_id") else "verification", ["ask_elder", "verification"]
    )
    graph.add_edge("ask_elder", "risk_scorer")
    graph.add_edge("verification", "intervention")
    graph.add_conditional_edges(
        "intervention",
        lambda s: "resolve" if s.get("guardian_decision") == DECIDED else "await_guardian",
        ["resolve", "await_guardian"],
    )
    graph.add_conditional_edges(
        "await_guardian",
        lambda s: "resolve" if s.get("guardian_decision") else "await_guardian",
        ["resolve", "await_guardian"],
    )
    graph.add_edge("resolve", END)
    return graph
