"""Chạy kịch bản qua đồ thị sự cố THẬT (`IncidentRuntime` + `AsyncPostgresSaver`) trên DB eval riêng (spec 030).

LLM = `ReplayClient` cắm vào `LlmRouter`. Không chạy worker nền ⇒ không có tin nào tới Zalo: tin chỉ nằm ở bảng `jobs`
(đọc để kiểm rồi xóa). Mọi sự cố eval có id `eval-<nonce>-<case_id>` và `is_demo=True`.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from sqlalchemy import func, make_url, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime, RunStatus
from hoicon.config import Settings, get_settings
from hoicon.db.models import AgentRun, AgentStep, Job
from hoicon.domain.events import RiskEvent
from hoicon.eval.cases import EVAL_DIR, Case, build_event, case_secrets, elder_reply, incident_id
from hoicon.eval.checks import MAX_ASK_ELDER, CaseResult, checkpoint_bytes, evaluate
from hoicon.eval.replay import ReplayClient
from hoicon.jobs.queue import cancel_prefix
from hoicon.ops.threat_list import SeedError, load_seed

CONNECT_TIMEOUT_S = 5
THREAT_SEED = Path(__file__).resolve().parents[4] / "data" / "threat_seed.demo.json"
ELDER_ALIAS = "Mẹ"
PRODUCTION_ENVS = ("prod", "production")
LONG_TIMER_S = 3600  # hẹn giờ của đồ thị chỉ để có job; không worker nào chạy, và cuối ca job bị xóa


class IsolationError(Exception):
    """Cấu hình eval có nguy cơ chạm DB/dịch vụ thật (CLI ⇒ exit 2)."""


@dataclass
class CaseOutcome:
    case: Case
    result: CaseResult
    violations: list[str]
    failures: list[str]
    cassette: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.violations and not self.failures


def _same_database(a: str, b: str) -> bool:
    """Cùng máy + cổng + tên DB (mật khẩu/tham số/cách viết `localhost` khác nhau vẫn là một DB)."""

    def key(url: str) -> tuple[str, int, str | None]:
        parsed = make_url(url)
        host = "127.0.0.1" if parsed.host in (None, "", "localhost", "::1") else parsed.host
        return host, parsed.port or 5432, parsed.database

    return key(a) == key(b)


def check_isolation(database_url: str, shared_db_ok: bool, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not database_url:
        raise IsolationError("thiếu URL DB eval: đặt HOICON_EVAL_DATABASE_URL hoặc truyền --database-url")
    if settings.env.strip().lower() in PRODUCTION_ENVS:
        raise IsolationError("từ chối chạy eval khi HOICON_ENV=prod")
    if _same_database(database_url, settings.database_url.get_secret_value()) and not shared_db_ok:
        raise IsolationError(
            "URL DB eval trùng DB ứng dụng (HOICON_DATABASE_URL): dùng DB riêng hoặc thêm --shared-db-ok (chỉ cho CI)"
        )
    target = make_url(database_url)
    remote = (target.host or "") not in ("", "localhost", "127.0.0.1", "::1")
    if remote and not shared_db_ok and not re.search(r"eval|test", (target.database or "").lower()):
        raise IsolationError("DB eval ở máy khác phải có tên chứa 'eval' hoặc 'test' (hoặc thêm --shared-db-ok)")


def make_sessionmaker(url: str) -> tuple[async_sessionmaker, AsyncEngine]:
    engine = create_async_engine(
        url, pool_size=5, connect_args={"connect_timeout": CONNECT_TIMEOUT_S}, hide_parameters=True
    )
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _steps(sessions: async_sessionmaker, run_id: uuid.UUID) -> list[dict[str, Any]]:
    async with sessions() as session:
        rows = (await session.scalars(select(AgentStep).where(AgentStep.run_id == run_id).order_by(AgentStep.at))).all()
    return [
        {
            "node": s.node,
            "input_redacted": s.input_redacted,
            "output": s.output,
            "fallback_used": s.fallback_used,
            "llm": s.model_profile is not None,
            "latency_ms": s.latency_ms,
        }
        for s in rows
    ]


async def _guardian_messages(sessions: async_sessionmaker, incident: str) -> list[str]:
    query = (
        select(Job.payload)
        .where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{incident}:msg:", autoescape=True))
        .order_by(Job.created_at, Job.idempotency_key)
    )
    async with sessions() as session:
        return [p["text"] for p in await session.scalars(query)]


async def _drive(
    case: Case, event: RiskEvent, runtime: IncidentRuntime, incident: str
) -> tuple[RunStatus, list[str], int]:
    """start → ask_elder (≤ 3) → nhắc T1 → người giám hộ 2 (T2) → quyết định.

    Trả (trạng thái cuối, các câu hỏi, số lượt hỏi)."""
    status = await runtime.start(event, incident_id=incident, elder_alias=ELDER_ALIAS, is_demo=True)
    questions: list[str] = []
    asks = 0
    while status.waiting_for == "ask_elder":
        questions.append(status.interrupt["text"])
        asks += 1
        if asks > MAX_ASK_ELDER:
            return status, questions, asks  # đồ thị không tự dừng hỏi ⇒ `graph_loop`, không chạy tiếp
        reply = elder_reply(case, status.interrupt["question_id"], first=asks == 1)
        status = await _resume(runtime, incident, reply, "ask_elder")
    if status.waiting_for == "await_guardian":
        status = await _resume(runtime, incident, {"timer": "t1"}, "await_guardian")  # sinh tin nhắc
        status = await _resume(runtime, incident, {"timer": "t2"}, "await_guardian")  # tin cho người giám hộ 2
        decision = "safe" if case.is_benign else "scam"
        status = await _resume(runtime, incident, {"decision": decision}, "await_guardian")
    return status, questions, asks


async def _resume(runtime: IncidentRuntime, incident: str, value: dict[str, Any], expect: str) -> RunStatus:
    status = await runtime.resume(incident, value, expect=expect)
    if status is None:
        raise RuntimeError(f"đồ thị không còn chờ ở {expect}")
    return status


async def _run_case(
    case: Case,
    runtime: IncidentRuntime,
    client: ReplayClient,
    sessions: async_sessionmaker,
    nonce: str,
    cassette_doc: dict[str, Any],
    drill: bool,
) -> CaseOutcome:
    client.load(cassette_doc)
    secrets = case_secrets(case)
    started = time.monotonic()
    if build_event(case) is None:  # luật R0/không mở app tài chính: không có sự cố, không chạy đồ thị
        result = CaseResult(
            case_id=case.id, run_id="no-incident", incident_started=False, secrets=secrets, outcome="no_incident"
        )
        violations, failures = evaluate(case, result, cassette_doc.get("injected_markers", []))
        return CaseOutcome(case, result, violations, failures, cassette_doc)

    incident = incident_id(nonce, case.id)
    event = build_event(case)
    if drill:  # diễn tập: cờ `is_drill` đi suốt đồ thị ⇒ mọi tin phải mang nhãn [DIỄN TẬP] (luật 8)
        event = event.model_copy(update={"is_drill": True})
    result = CaseResult(
        case_id=case.id, rule_floor=event.rule_floor.value, secrets=secrets, outcome="error", is_drill=drill
    )
    try:
        status, questions, asks = await _drive(case, event, runtime, incident)
        async with sessions() as session:
            run_id = await session.scalar(select(AgentRun.id).where(AgentRun.thread_id == incident))
        steps = await _steps(sessions, run_id)
        result.run_id = str(run_id)
        result.questions, result.ask_count = questions, asks
        result.messages = await _guardian_messages(sessions, incident)
        result.steps = steps
        result.checkpoint = await checkpoint_bytes(sessions, incident)
        result.llm_sent = client.sent_text()
        result.levels = [str(s["output"]["level"]) for s in steps if s["node"] in ("ingest", "risk_scorer")]
        result.levels.append(status.level or "none")
        result.final_level = status.level or "none"
        result.notified = bool(result.messages)
        result.outcome = status.outcome or "error"
        result.llm_calls = sum(1 for s in steps if s["llm"])
        result.fallbacks = sum(1 for s in steps if s["llm"] and s["fallback_used"])
    except Exception as exc:  # một ca hỏng không làm hỏng cả lượt: ghi lỗi, ca trượt `unexpected_outcome`
        result.error = type(exc).__name__
    finally:
        if not result.run_id:  # ca lỗi giữa chừng vẫn cần run_id để mở trace
            async with sessions() as session:
                found = await session.scalar(select(AgentRun.id).where(AgentRun.thread_id == incident))
            result.run_id = str(found) if found else ""
        await cancel_prefix(sessions, f"{incident}:")  # tin chưa gửi + hẹn giờ của ca (FR-010)
        result.duration_ms = int((time.monotonic() - started) * 1000)
    violations, failures = evaluate(case, result, cassette_doc.get("injected_markers", []))
    return CaseOutcome(case, result, violations, failures, cassette_doc)


async def _fail_unfinished_runs(sessions: async_sessionmaker, nonce: str) -> None:
    """Ca dở dang (lỗi giữa chừng, `graph_loop`) không được để `running/waiting`.

    Nếu không, `recover()` của ứng dụng sẽ nhặt lại thread eval."""
    stmt = (
        update(AgentRun)
        .where(
            AgentRun.thread_id.startswith(f"eval-{nonce}-", autoescape=True),
            AgentRun.status.in_(("running", "waiting")),
        )
        .values(status="failed", finished_at=func.now())
    )
    async with sessions.begin() as session:
        await session.execute(stmt)


async def _seed_threat_list(sessions: async_sessionmaker, settings: Settings) -> None:
    """Danh sách đe dọa nằm trong DB (spec 003) ⇒ DB eval phải có số demo để ca `flagged` ra `flagged` (idempotent)."""
    try:
        # with_bucket=False: eval không dùng ảnh chụp bucket, nên không cần (và không đòi) khóa mã hóa dữ liệu.
        await load_seed(
            sessions, json.loads(THREAT_SEED.read_text(encoding="utf-8")), env=settings.env, with_bucket=False
        )
    except SeedError as exc:  # vd. HOICON_ENV ngoài dev/test/ci: thông điệp không chứa giá trị
        raise IsolationError(str(exc)) from None
    except RuntimeError as exc:  # thiếu khóa băm; thông điệp chỉ nêu TÊN biến môi trường
        raise IsolationError(
            f"{exc}: eval cần khóa băm số điện thoại để nạp danh sách đe dọa demo (dùng khóa GIẢ)"
        ) from None


async def run_suite(
    cases: list[Case],
    *,
    database_url: str,
    shared_db_ok: bool = False,
    settings: Settings | None = None,
    cassette_dir: Path | None = None,
    nonce: str | None = None,
    suite: str = "smoke",
    drill: bool = False,
) -> list[CaseOutcome]:
    settings = settings or get_settings()
    check_isolation(database_url, shared_db_ok, settings)
    cassette_dir = cassette_dir or EVAL_DIR / "cassettes" / suite
    missing = [c.id for c in cases if not (cassette_dir / f"{c.id}.json").is_file()]
    if missing:
        raise IsolationError(f"thiếu cassette: {', '.join(missing)}")
    cassettes = {c.id: json.loads((cassette_dir / f"{c.id}.json").read_text(encoding="utf-8")) for c in cases}
    nonce = nonce or uuid.uuid4().hex[:8]
    eval_settings = settings.model_copy(
        update={
            "database_url": SecretStr(database_url),
            # eval không bao giờ có khóa/token thật: đồ thị không dùng, nhưng sửa sau này cũng không lấy nhầm được
            "anthropic_api_key": None,
            "gemini_api_key": None,
            "zalo_bot_token": None,
            "zalo_webhook_secret": None,
            "zalo_mode": "mock",
            "timer_ask_elder_s": LONG_TIMER_S,
            "timer_t1_s": LONG_TIMER_S,
            "timer_t2_s": LONG_TIMER_S,
            "timer_t3_s": LONG_TIMER_S,
        }
    )
    sessions, engine = make_sessionmaker(database_url)
    client = ReplayClient()
    router = LlmRouter(client, eval_settings.llm_fast_model, Decimal(1000))
    outcomes: list[CaseOutcome] = []
    try:
        await _seed_threat_list(sessions, settings)
        async with IncidentRuntime.open(Deps(router, sessions, eval_settings)) as runtime:
            for case in cases:  # thứ tự cố định ⇒ chạy lại cho kết quả giống hệt
                outcomes.append(await _run_case(case, runtime, client, sessions, nonce, cassettes[case.id], drill))
    finally:
        await cancel_prefix(sessions, f"eval-{nonce}-")
        await _fail_unfinished_runs(sessions, nonce)
        await engine.dispose()
    return outcomes
