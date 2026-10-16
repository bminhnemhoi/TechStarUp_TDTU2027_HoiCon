"""`POST /v1/incidents/{id}/answers` và `GET /v1/incidents/{id}/pending-question` (spec 024, FR-003, FR-004).

App Lính gác kéo câu hỏi E8 đang chờ và gửi câu trả lời về đồ thị tác tử. Chỉ thiết bị cùng gia đình (404 cho sự cố
nhà khác, không lộ sự tồn tại). Câu trả lời chỉ là enum + cờ tất định: không nhận, không lưu văn bản tự do hay giọng
nói (ADR-009). Câu trả lời KHÔNG chạy đồ thị trong request (LLM có thể tới 2 × 4 s): xếp job `graph_resume` có khóa
chống trùng, worker chạy tiếp — người cao tuổi bấm xong là có phản hồi ngay.
"""

import logging
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from hoicon.agents import texts
from hoicon.agents.runtime import RunStatus, clean_resume
from hoicon.api.auth import DeviceClaims, get_current_device
from hoicon.db.models import Incident, Job
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import enqueue
from hoicon.services.incident_service import TERMINAL
from hoicon.services.runtime_service import ensure_runtime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["elder"])

QuestionId = Literal["q_caller_authority", "q_asked_transfer", "q_know_caller"]
NO_QUESTION = "Không có câu hỏi nào đang chờ"
NOT_FOUND = "Sự cố không tồn tại"
BUSY = "Hệ thống đang bận, bác vui lòng thử lại sau ít giây."


class NoteFlags(BaseModel):
    """Cùng bộ cờ với `hoicon.domain.pii.NOTE_KEYWORDS` (thứ LLM nhận), có test giữ khớp."""

    model_config = ConfigDict(extra="forbid")

    mentions_authority: bool = False
    mentions_transfer: bool = False
    mentions_code: bool = False
    mentions_secrecy: bool = False
    mentions_app_or_link: bool = False


class ElderAnswerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: QuestionId
    answer: Literal["yes", "no", "unsure", "timeout"]
    note_flags: NoteFlags | None = None


class ElderAnswerResult(BaseModel):
    status: Literal["accepted", "expired", "already_resolved"]
    incident_id: UUID
    level: str


class PendingQuestionOut(BaseModel):
    incident_id: UUID
    question_id: QuestionId
    text: str
    is_drill: bool
    answers: list[str]
    expires_at: datetime


async def _own_incident(incident_id: UUID, claims: DeviceClaims) -> Incident:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, incident_id)
    if incident is None or incident.family_id != claims.family_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return incident


async def _waiting_question(incident_id: UUID) -> dict[str, Any] | None:
    """Nội dung interrupt `ask_elder` nếu đồ thị đang chờ người cao tuổi, không thì None."""
    try:
        runtime = await ensure_runtime()
        run: RunStatus = await runtime.status(str(incident_id))
    except psycopg.Error as exc:  # DB không với tới / pool hết hạn chờ (PoolTimeout cũng là psycopg.Error)
        logger.warning("elder: không đọc được trạng thái đồ thị (%s)", type(exc).__name__)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=BUSY, headers={"Retry-After": "2"}) from None
    if run.waiting_for != "ask_elder" or not run.interrupt:
        return None
    return run.interrupt


@router.post("/incidents/{incident_id}/answers", response_model=ElderAnswerResult)
async def submit_elder_answer(
    incident_id: UUID, answer_in: ElderAnswerIn, claims: Annotated[DeviceClaims, Depends(get_current_device)]
) -> ElderAnswerResult:
    """Nhận câu trả lời E8. Đồ thị không còn chờ câu này (đã quá hạn, đã trả lời) ⇒ `expired`."""
    incident = await _own_incident(incident_id, claims)
    if incident.state in TERMINAL:
        return ElderAnswerResult(status="already_resolved", incident_id=incident_id, level=incident.level)
    waiting = await _waiting_question(incident_id)
    if waiting is None or waiting.get("question_id") != answer_in.question_id:
        return ElderAnswerResult(status="expired", incident_id=incident_id, level=incident.level)
    raw: dict[str, Any] = ({"timeout": True} if answer_in.answer == "timeout" else {"answer": answer_in.answer}) | (
        {"note_flags": answer_in.note_flags.model_dump()} if answer_in.note_flags else {}
    )
    payload = {"thread_id": str(incident_id), "expect": "ask_elder", "value": clean_resume(raw)}
    async with get_sessionmaker().begin() as session:  # bấm hai lần ⇒ một job (khóa theo sự cố)
        await enqueue(session, "graph_resume", payload, key=f"{incident_id}:elder_answer")
    logger.info("elder_answer: incident=%s answer=%s", incident_id, answer_in.answer)
    return ElderAnswerResult(status="accepted", incident_id=incident_id, level=incident.level)


@router.get("/incidents/{incident_id}/pending-question", response_model=PendingQuestionOut)
async def get_pending_question(
    incident_id: UUID, claims: Annotated[DeviceClaims, Depends(get_current_device)]
) -> PendingQuestionOut:
    """Câu hỏi E8 đang chờ (app kéo khi nhận FCM, hoặc tự hỏi khi FCM chậm/mất mạng). Không có ⇒ 404."""
    incident = await _own_incident(incident_id, claims)
    if incident.state in TERMINAL:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_QUESTION)
    waiting = await _waiting_question(incident_id)
    if waiting is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_QUESTION)
    async with get_sessionmaker()() as session:  # hạn trả lời = mốc của bộ hẹn giờ `ask_elder` (đặt trước interrupt)
        expires_at = await session.scalar(
            select(Job.run_at).where(Job.idempotency_key == f"{incident_id}:timer:ask_elder")
        )
    if expires_at is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=NO_QUESTION)
    question_id = waiting["question_id"]
    return PendingQuestionOut(
        incident_id=incident_id,
        question_id=question_id,
        text=texts.question_for_elder(question_id, incident.is_drill),
        is_drill=incident.is_drill,
        answers=list(texts.ANSWERS),
        expires_at=expires_at,
    )
