"""Chạy đồ thị sự cố với checkpoint Postgres (ADR-002, ADR-009).

- Checkpoint `AsyncPostgresSaver` ghi ĐỒNG BỘ sau mỗi bước (`durability="sync"`) ⇒ tiến trình chết (kill -9) thì chạy
  tiếp được từ bước cuối đã ghi (`recover`).
- Mỗi thread (= một sự cố) chỉ một bên được chạy tại một thời điểm: `pg_advisory_lock` theo thread — người giám hộ bấm
  nút và bộ hẹn giờ đến hạn cùng lúc không giẫm lên nhau.
- `resume(expect=…)`: bộ hẹn giờ đến muộn (đồ thị đã đi tiếp) bị bỏ qua thay vì đẩy nhầm giá trị vào chỗ chờ khác.
"""

import logging
import os
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.agents import texts
from hoicon.agents.incident_graph import Deps, build_graph
from hoicon.db.models import AgentRun
from hoicon.domain.events import RiskEvent
from hoicon.domain.pii import NOTE_KEYWORDS, note_flags
from hoicon.mcp_servers.threat import lookup_h1

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunStatus:
    thread_id: str
    status: str  # waiting | done
    waiting_for: str | None
    level: str | None
    outcome: str | None
    interrupt: dict[str, Any] | None


_ALIAS = re.compile(r"^[^\d@<>{}]{1,20}$")
LOCK_TIMEOUT = "10s"


def clean_resume(value: Any) -> dict[str, Any]:
    """Giá trị resume đi thẳng vào bảng `checkpoint_writes` của LangGraph (trước khi node nào kịp chạy) ⇒ chỉ giữ khóa
    cho phép với giá trị hợp lệ. Lời kể tự do (`note`) KHÔNG được lưu: thay bằng cờ tất định (`note_flags`)."""
    if not isinstance(value, dict):
        return {"invalid": True}
    clean: dict[str, Any] = {}
    if value.get("answer") in texts.ANSWERS:
        clean["answer"] = value["answer"]
    if value.get("timeout") is True:
        clean["timeout"] = True
    if value.get("decision") in ("safe", "scam"):
        clean["decision"] = value["decision"]
    if value.get("timer") in ("t1", "t2", "t3"):
        clean["timer"] = value["timer"]
    evidence = value.get("evidence")  # id một dòng `verifications` (spec 026): chỉ giữ nếu đúng là UUID
    if isinstance(evidence, str):
        with suppress(ValueError):
            clean["evidence"] = str(UUID(evidence))
    flags = value.get("note_flags")  # E8 (spec 024): app gửi sẵn cờ tất định, chỉ giữ cờ đã biết có giá trị bool
    if isinstance(flags, dict):
        kept = {k: v for k, v in flags.items() if k in NOTE_KEYWORDS and isinstance(v, bool)}
        if kept:
            clean["note_flags"] = kept
    if isinstance(value.get("note"), str) and value["note"].strip():
        clean["note_flags"] = note_flags(value["note"][:2000])
    return clean or {"invalid": True}


DEFAULT_ALIAS = "Bố/Mẹ"


def safe_alias(alias: str | None) -> str:
    """Cách xưng hô của thành viên nếu hợp lệ cho đồ thị (ngắn, không chữ số), không thì cách gọi chung."""
    return alias if alias and _ALIAS.match(alias) else DEFAULT_ALIAS


async def prepare_event(
    sessions: async_sessionmaker | AsyncSession, event: RiskEvent
) -> tuple[dict[str, Any], dict[str, Any]]:
    """ADR-006: máy chủ không lưu h1 (dò ngược được ra số điện thoại của người gọi) ⇒ tra danh sách đe dọa NGAY, chỉ
    giữ kết quả + 3 số cuối. Tên gói app ngân hàng cũng bỏ. ⇒ (threat, event_data) an toàn để lưu (job, state).
    Truyền `AsyncSession` đang mở (`POST /v1/events`) ⇒ tra trong SAVEPOINT của giao dịch đó: không mượn kết nối thứ
    hai khi đang giữ khóa thiết bị, và tra lỗi không làm hỏng cả lô."""
    threat: dict[str, Any] = {"verdict": "unknown"}
    if event.caller:
        try:
            if isinstance(sessions, AsyncSession):
                async with sessions.begin_nested():
                    threat = (await lookup_h1(sessions, event.caller.h1)).model_dump()
            else:
                threat = (await lookup_h1(sessions, event.caller.h1)).model_dump()
        except Exception as exc:  # danh sách lỗi KHÔNG được chặn đường cảnh báo: mức sàn của máy vẫn áp dụng (luật 5)
            logger.warning("threat lookup failed: %s", type(exc).__name__)  # không ghi thông điệp (chuỗi kết nối)
            threat = {"verdict": "unknown", "error": type(exc).__name__}
    event_data = event.model_dump(mode="json", exclude_none=True, exclude={"caller": {"h1"}, "app": {"package"}})
    return threat, event_data


def _psycopg_url(sqlalchemy_url: str) -> str:
    return sqlalchemy_url.replace("postgresql+psycopg://", "postgresql://", 1)


class IncidentRuntime:
    def __init__(self, graph: CompiledStateGraph, sessions: async_sessionmaker) -> None:
        self.graph = graph
        self._sessions = sessions

    @classmethod
    @asynccontextmanager
    async def open(cls, deps: Deps) -> AsyncGenerator["IncidentRuntime", None]:
        # langchain-core có sẵn LangSmith: một biến môi trường sót trên máy là state bị gửi ra nước ngoài ⇒ tắt cứng.
        os.environ["LANGSMITH_TRACING"] = os.environ["LANGCHAIN_TRACING_V2"] = "false"
        url = _psycopg_url(deps.settings.database_url.get_secret_value())
        # LangGraph đòi autocommit + dict_row; prepare_threshold=0 để chạy được sau pgbouncer.
        kwargs = {"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row, "connect_timeout": 5}
        async with AsyncConnectionPool(url, min_size=1, max_size=5, kwargs=kwargs, open=False) as pool:
            saver = AsyncPostgresSaver(pool)
            await saver.setup()  # tạo/nâng bảng checkpoint của LangGraph (idempotent)
            yield cls(build_graph(deps).compile(checkpointer=saver), deps.sessions)

    @asynccontextmanager
    async def _thread_lock(self, thread_id: str) -> AsyncGenerator[None, None]:
        async with self._sessions() as session:
            key = text("SELECT hashtextextended(:t, 0)").bindparams(t=f"incident:{thread_id}")
            lock_id = (await session.execute(key)).scalar_one()
            # Chờ khóa có hạn: bên giữ khóa cần kết nối từ cùng pool; quá hạn ⇒ lỗi rõ ràng, job thử lại sau.
            await session.execute(text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))
            await session.execute(text("SELECT pg_advisory_lock(:k)").bindparams(k=lock_id))
            try:
                yield
            finally:
                await session.execute(text("SELECT pg_advisory_unlock(:k)").bindparams(k=lock_id))
                await session.commit()

    async def start(
        self,
        event: RiskEvent,
        *,
        incident_id: str,
        elder_alias: str,
        is_demo: bool = False,
        family_id: str | None = None,
    ) -> RunStatus:
        """`family_id` (UUID, tùy chọn): gia đình nhận tin; có thì vào state và payload `notify_guardian` (spec 002)."""
        threat, event_data = await prepare_event(self._sessions, event)
        return await self.start_prepared(
            event_data, threat, incident_id=incident_id, elder_alias=elder_alias, is_demo=is_demo, family_id=family_id
        )

    async def start_prepared(
        self,
        event_data: dict[str, Any],
        threat: dict[str, Any],
        *,
        incident_id: str,
        elder_alias: str,
        is_demo: bool = False,
        family_id: str | None = None,
    ) -> RunStatus:
        """Chạy đồ thị từ sự kiện đã qua `prepare_event` (job `start_graph`, spec 024). Thread đã có trạng thái ⇒ không
        chạy lại (job thử lại sau khi đồ thị đã chạy không mở lượt thứ hai)."""
        if not _ALIAS.match(elder_alias):
            raise ValueError("elder_alias là cách xưng hô ngắn (≤ 20 ký tự, không chữ số), không phải họ tên đầy đủ")
        if family_id is not None:
            family_id = str(UUID(family_id))  # ValueError nếu không phải UUID; chuẩn hóa dạng chữ thường có gạch ngang
        if "h1" in (event_data.get("caller") or {}) or "package" in (event_data.get("app") or {}):
            raise ValueError("event_data phải qua prepare_event(): không mang h1 hay tên gói")
        is_drill = bool(event_data.get("is_drill", False))
        async with self._thread_lock(incident_id):
            if (await self.graph.aget_state(self._config(incident_id))).values:
                logger.info("start ignored: thread already has a run")
                return await self.status(incident_id)
            async with self._sessions.begin() as session:
                run = AgentRun(graph="incident", thread_id=incident_id, is_drill=is_drill, is_demo=is_demo)
                session.add(run)
            state = {
                "incident_id": incident_id,
                "run_id": str(run.id),
                "is_drill": is_drill,
                "is_demo": is_demo,
                "elder_alias": elder_alias,
                "event": event_data,
                "threat": threat,
                "rule_floor": event_data["rule_floor"],
            }
            if family_id is not None:  # không đặt khóa khi không có ⇒ state/checkpoint sự cố không gia đình không đổi
                state["family_id"] = family_id
            await self.graph.ainvoke(state, self._config(incident_id), durability="sync")
            return await self._record(incident_id)

    async def resume(self, thread_id: str, value: Any, expect: str | None = None) -> RunStatus | None:
        """Đưa `value` vào chỗ đồ thị đang chờ. Trả None nếu đồ thị không còn chờ ở `expect` (giá trị đến muộn)."""
        value = clean_resume(value)
        async with self._thread_lock(thread_id):
            snapshot = await self.graph.aget_state(self._config(thread_id))
            if not snapshot.next or (expect and expect not in snapshot.next):
                logger.info("resume ignored: thread waits at %s, expected %s", snapshot.next, expect)
                return None
            await self._set_status(thread_id, "running")  # chết giữa lượt này ⇒ recover() nhặt lại
            await self.graph.ainvoke(Command(resume=value), self._config(thread_id), durability="sync")
            return await self._record(thread_id)

    async def recover(self) -> list[RunStatus]:
        """Chạy tiếp mọi lần chạy dở dang (tiến trình trước chết khi đang ở trạng thái `running`)."""
        async with self._sessions() as session:
            threads = (await session.scalars(select(AgentRun.thread_id).where(AgentRun.status == "running"))).all()
        recovered = []
        for thread_id in threads:
            async with self._thread_lock(thread_id):
                snapshot = await self.graph.aget_state(self._config(thread_id))
                if not snapshot.values:  # chết trước checkpoint đầu tiên: không còn trạng thái để chạy tiếp
                    await self._set_status(thread_id, "failed")
                    continue
                if snapshot.next and not snapshot.interrupts:
                    logger.info("recovering thread at %s", snapshot.next)
                    await self.graph.ainvoke(None, self._config(thread_id), durability="sync")
                recovered.append(await self._record(thread_id))
        return recovered

    async def status(self, thread_id: str) -> RunStatus:
        snapshot = await self.graph.aget_state(self._config(thread_id))
        values = snapshot.values
        pending = snapshot.interrupts[0].value if snapshot.interrupts else None
        return RunStatus(
            thread_id=thread_id,
            status="waiting" if snapshot.next else "done",
            waiting_for=snapshot.next[0] if snapshot.next else None,
            level=values.get("level"),
            outcome=values.get("outcome"),
            interrupt=pending,
        )

    async def _record(self, thread_id: str) -> RunStatus:
        current = await self.status(thread_id)
        await self._set_status(thread_id, current.status)
        return current

    async def _set_status(self, thread_id: str, status: str) -> None:
        values: dict[str, Any] = {"status": status}
        if status in ("done", "failed"):
            values["finished_at"] = func.now()
        async with self._sessions.begin() as session:
            await session.execute(update(AgentRun).where(AgentRun.thread_id == thread_id).values(**values))

    @staticmethod
    def _config(thread_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": thread_id}}
