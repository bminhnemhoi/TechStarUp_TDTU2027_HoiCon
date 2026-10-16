"""Spec 024 trên Postgres thật: câu hỏi nhanh E8, đồ thị tự chạy từ `POST /v1/events`, hẹn giờ T1/T3 và quyết định
của người giám hộ ngoài đồ thị.

1. `POST /v1/events` (mức cao) ⇒ job `start_graph` KHÔNG mang h1/tên gói (ADR-006); chạy lại job không mở lượt thứ hai.
2. `GET pending-question` đúng `elder_question.v1.json`, hạn = mốc bộ hẹn giờ; `POST answers` xếp job, không chạy LLM
   trong request; câu trả lời sai câu hỏi/đến muộn ⇒ `expired`.
3. Người giám hộ quyết qua `/a/` (hay JWT) ⇒ T1 đến hạn KHÔNG gửi nhắc, đồ thị kết thúc theo trạng thái sự cố.
4. T3 không ai trả lời ⇒ sự cố `resolved_no_response` (actor `timer`); Zalo "2" ⇒ `case_open`, không bị đồ thị ghi đè.
5. Trả lời "Không quen người gọi" nâng mức trên sàn dù LLM cố hạ (SC-002).
"""

import json
import re
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from consent_support import call, pair_device, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, select
from test_api_events import make_event, post
from test_incident_graph import deps

from hoicon.agents.runtime import IncidentRuntime, clean_resume
from hoicon.agents.spike import demo_event
from hoicon.channels.fcm import get_fcm_client
from hoicon.channels.guardian import ChannelDeps
from hoicon.channels.zalo import MockZaloClient
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, Family, Incident, IncidentTransition, Job
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import RiskEvent
from hoicon.jobs.queue import Handler
from hoicon.jobs.worker import incident_handlers
from hoicon.ops.pairing_code import create_pairing_code
from hoicon.services.incident_service import apply_guardian_decision
from hoicon.services.runtime_service import set_runtime

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
QUESTION = Draft202012Validator(
    json.loads((SCHEMAS / "elder_question.v1.json").read_text(encoding="utf-8")), format_checker=FormatChecker()
)
RAW_PHONE = re.compile(r"(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}")


@dataclass
class Asked:
    """Sự cố thật đã mở qua `POST /v1/events`, đồ thị đang chờ người cao tuổi ở `ask_elder`."""

    token: str
    incident: str
    runtime: IncidentRuntime
    handlers: dict[str, Handler]
    question_id: str


async def job(key: str) -> Job | None:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(Job).where(Job.idempotency_key == key))


async def run_job(a: Asked, key: str) -> None:
    """Chạy đúng một job theo khóa (không `run_once`: DB dev dùng chung có thể còn job đến hạn của nơi khác)."""
    found = await job(key)
    assert found is not None, key
    await a.handlers[found.kind](dict(found.payload))


async def incident_row(incident_id: str) -> Incident:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        return incident


@pytest.fixture
async def token(device_world: Any) -> str:
    return (await pair_device(device_world.code))["access_token"]


@pytest.fixture
async def asked(token: str, threads: list[str]) -> AsyncIterator[Asked]:
    body = (await post(token, make_event())).json()
    assert body["incident_opened"] is True, body
    incident = body["incident_id"]
    threads.append(incident)
    d = deps(timer_t1_s=120, timer_t2_s=300, timer_t3_s=900)
    async with IncidentRuntime.open(d) as runtime:
        set_runtime(runtime)
        channel = ChannelDeps(get_sessionmaker(), MockZaloClient(), get_settings())
        a = Asked(token, incident, runtime, incident_handlers(runtime, channel), "")
        await run_job(a, f"{incident}:graph:start")
        status = await runtime.status(incident)
        assert status.waiting_for == "ask_elder", status
        a.question_id = status.interrupt["question_id"]
        try:
            yield a
        finally:
            set_runtime(None)


async def test_elder_endpoints_require_device_token(device_world: Any) -> None:
    incident = new_id()
    assert (await call("GET", f"/v1/incidents/{incident}/pending-question")).status_code == 401
    body = {"question_id": "q_caller_authority", "answer": "yes"}
    assert (await call("POST", f"/v1/incidents/{incident}/answers", json=body)).status_code == 401


async def test_elder_endpoints_hide_other_families(device_world: Any, token: str, threads: list[str]) -> None:
    other_id = new_id()
    async with get_sessionmaker().begin() as session:
        session.add(Family(id=other_id, display_name="Nhà khác", region="nam", is_demo=True))
    other_token = (await pair_device(await create_pairing_code(get_sessionmaker(), other_id)))["access_token"]
    other_incident = (await post(other_token, make_event())).json()["incident_id"]
    threads.append(other_incident)
    try:
        assert (await call("GET", f"/v1/incidents/{other_incident}/pending-question", token=token)).status_code == 404
        body = {"question_id": "q_caller_authority", "answer": "yes"}
        resp = await call("POST", f"/v1/incidents/{other_incident}/answers", token=token, json=body)
        assert resp.status_code == 404
    finally:
        await purge_family(other_id)


async def test_start_graph_job_holds_no_caller_hash_and_runs_once(asked: Asked) -> None:
    start = await job(f"{asked.incident}:graph:start")
    assert start is not None and start.kind == "start_graph"
    dumped = json.dumps(start.payload)
    assert '"h1"' not in dumped and '"package"' not in dumped and not RAW_PHONE.search(dumped)
    assert start.payload["threat"]["verdict"] in ("unknown", "flagged")

    await run_job(asked, f"{asked.incident}:graph:start")  # job chạy lại (worker chết trước `complete`)
    async with get_sessionmaker()() as session:
        runs = await session.scalar(select(func.count()).where(AgentRun.thread_id == asked.incident))
    assert runs == 1

    push = await job(f"{asked.incident}:fcm:ask_elder:{asked.question_id}")
    assert push is not None and set(push.payload) == {"incident_id", "question_id", "is_drill"}
    await run_job(asked, push.idempotency_key)
    assert get_fcm_client().sent[-1].incident_id == asked.incident


async def test_flagged_caller_is_looked_up_inside_the_batch(
    token: str, threads: list[str], seeded_threat: dict[str, Any]
) -> None:
    """Số có trong danh sách đe dọa ⇒ job mang `flagged` (tra trong SAVEPOINT của lô), vẫn không mang h1."""
    h1 = seeded_threat["indicators"][0]["h1"]
    event = make_event()
    event["caller"] = {**event["caller"], "h1": h1}
    body = (await post(token, event)).json()
    assert body["incident_opened"] is True, body
    threads.append(body["incident_id"])
    start = await job(f"{body['incident_id']}:graph:start")
    assert start is not None and start.payload["threat"]["verdict"] == "flagged"
    assert h1 not in json.dumps(start.payload)


async def test_pending_question_then_answer_resumes_graph(asked: Asked) -> None:
    url = f"/v1/incidents/{asked.incident}"
    resp = await call("GET", f"{url}/pending-question", token=asked.token)
    assert resp.status_code == 200, resp.text
    question = resp.json()
    assert [e.message for e in QUESTION.iter_errors(question)] == []
    assert question["text"].startswith("Đây là trợ lý AI HỏiCon.")
    timer = await job(f"{asked.incident}:timer:ask_elder")
    assert timer is not None and datetime.fromisoformat(question["expires_at"]) == timer.run_at

    other = next(q for q in ("q_caller_authority", "q_asked_transfer", "q_know_caller") if q != asked.question_id)
    resp = await call("POST", f"{url}/answers", token=asked.token, json={"question_id": other, "answer": "yes"})
    assert resp.json()["status"] == "expired"  # trả lời một câu không được hỏi

    answer = {"question_id": asked.question_id, "answer": "no", "note_flags": {"mentions_transfer": True}}
    for _ in range(2):  # bấm hai lần ⇒ vẫn một job
        resp = await call("POST", f"{url}/answers", token=asked.token, json=answer)
        assert resp.status_code == 200 and resp.json()["status"] == "accepted", resp.text
    resume = await job(f"{asked.incident}:elder_answer")
    assert resume is not None
    flags = resume.payload["value"].pop("note_flags")
    assert resume.payload["value"] == {"answer": "no"}  # chỉ enum + cờ bool, không văn bản tự do
    assert flags["mentions_transfer"] is True and not any(v for k, v in flags.items() if k != "mentions_transfer")
    assert (await asked.runtime.status(asked.incident)).waiting_for == "ask_elder"  # chưa chạy trong request

    await run_job(asked, f"{asked.incident}:elder_answer")
    status = await asked.runtime.status(asked.incident)
    assert status.waiting_for == "await_guardian" and status.level in ("high", "critical")
    assert (await call("GET", f"{url}/pending-question", token=asked.token)).status_code == 404
    resp = await call("POST", f"{url}/answers", token=asked.token, json=answer)
    assert resp.json()["status"] == "expired"


async def answer_and_wait_guardian(a: Asked) -> None:
    await a.runtime.resume(a.incident, {"answer": "unsure"}, expect="ask_elder")
    assert (await a.runtime.status(a.incident)).waiting_for == "await_guardian"


async def test_guardian_decision_outside_graph_stops_reminders(asked: Asked) -> None:
    await answer_and_wait_guardian(asked)
    async with get_sessionmaker().begin() as session:  # người giám hộ bấm "An toàn" trên `/a/[token]`
        incident = await session.get(Incident, asked.incident)
        await apply_guardian_decision(session, incident, "safe", "action_link")

    await run_job(asked, f"{asked.incident}:timer:t1")
    assert await job(f"{asked.incident}:msg:reminder") is None
    status = await asked.runtime.status(asked.incident)
    assert status.status == "done" and status.outcome == "resolved_safe"
    assert await job(f"{asked.incident}:timer:t2") is None  # resolve hủy các mốc còn lại
    assert (await incident_row(asked.incident)).state == "resolved_safe"


async def test_t3_without_answer_closes_incident_as_no_response(asked: Asked) -> None:
    await answer_and_wait_guardian(asked)
    await run_job(asked, f"{asked.incident}:timer:t3")
    incident = await incident_row(asked.incident)
    assert incident.state == "resolved_no_response" and incident.outcome == "no_response"
    async with get_sessionmaker()() as session:
        last = await session.scalar(
            select(IncidentTransition).where(
                IncidentTransition.incident_id == incident.id, IncidentTransition.to_state == "resolved_no_response"
            )
        )
    assert last is not None and last.actor == "timer" and last.reason == "graph_no_response"


async def test_zalo_scam_reply_keeps_case_open(asked: Asked) -> None:
    await answer_and_wait_guardian(asked)
    async with get_sessionmaker().begin() as session:  # cùng thứ tự với channels/updates: ghi sự cố rồi resume
        incident = await session.get(Incident, asked.incident)
        await apply_guardian_decision(session, incident, "emergency_pause", "zalo_reply_2")
    status = await asked.runtime.resume(asked.incident, {"decision": "scam"}, expect="await_guardian")
    assert status is not None and status.outcome == "case_open"
    assert (await incident_row(asked.incident)).state == "case_open"


async def test_elder_answer_raises_level_above_floor(threads: list[str]) -> None:
    """LLM giả cố hạ xuống `low` và hỏi `q_know_caller`; "Không quen" ⇒ ít nhất `high` dù sàn chỉ `medium`."""
    base = demo_event().model_dump()
    # h1 ngẫu nhiên: DEMO_H1 nằm trong danh sách đe dọa demo (⇒ `critical` ngay ở ingest, test không còn đo gì).
    caller = {**base["caller"], "h1": secrets.token_hex(32)}
    event = RiskEvent.model_validate({**base, "rule_floor": "medium", "caller": caller})
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(deps()) as runtime:
        status = await runtime.start(event, incident_id=thread, elder_alias="Mẹ", is_demo=True)
        assert status.waiting_for == "ask_elder" and status.level == "medium"
        assert status.interrupt["question_id"] == "q_know_caller"
        status = await runtime.resume(thread, {"answer": "no"}, expect="ask_elder")
    assert status is not None and status.level == "high"


def test_clean_resume_keeps_only_known_boolean_flags() -> None:
    value = {"answer": "yes", "note_flags": {"mentions_code": True, "mentions_money": True, "mentions_secrecy": "x"}}
    assert clean_resume(value) == {"answer": "yes", "note_flags": {"mentions_code": True}}
