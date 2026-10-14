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
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents import texts
from hoicon.agents.incident_graph import Deps, build_graph
from hoicon.db.models import AgentRun
from hoicon.domain.events import RiskEvent
from hoicon.domain.pii import note_flags
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
    if isinstance(value.get("note"), str) and value["note"].strip():
        clean["note_flags"] = note_flags(value["note"][:2000])
    return clean or {"invalid": True}


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

    async def start(self, event: RiskEvent, *, incident_id: str, elder_alias: str, is_demo: bool = False) -> RunStatus:
        if not _ALIAS.match(elder_alias):
            raise ValueError("elder_alias là cách xưng hô ngắn (≤ 20 ký tự, không chữ số), không phải họ tên đầy đủ")
        # ADR-006: máy chủ không lưu h1 (dò ngược được ra số điện thoại của người gọi) ⇒ tra danh sách đe dọa NGAY,
        # chỉ đưa kết quả + 3 số cuối vào state/checkpoint. Tên gói app ngân hàng cũng không lưu.
        threat = lookup_h1(event.caller.h1).model_dump() if event.caller else {"verdict": "unknown"}
        event_data = event.model_dump(mode="json", exclude_none=True, exclude={"caller": {"h1"}, "app": {"package"}})
        async with self._sessions.begin() as session:
            run = AgentRun(graph="incident", thread_id=incident_id, is_drill=event.is_drill, is_demo=is_demo)
            session.add(run)
        state = {
            "incident_id": incident_id,
            "run_id": str(run.id),
            "is_drill": event.is_drill,
            "is_demo": is_demo,
            "elder_alias": elder_alias,
            "event": event_data,
            "threat": threat,
            "rule_floor": event.rule_floor.value,
        }
        async with self._thread_lock(incident_id):
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
