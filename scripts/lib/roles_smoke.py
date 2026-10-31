"""Spec 012 T017: một lượt đồ thị + job + checkpoint dưới role `hoicon_app` (do `scripts/try-roles.sh` gọi).

Chạy với `HOICON_DATABASE_URL` trỏ role ứng dụng. Thành công = không thiếu quyền ở đường ghi checkpoint, `agent_runs`,
`agent_steps`, `jobs`; thất bại = in lý do và thoát khác 0."""

import asyncio
import sys
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import text

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.agents.spike import demo_event
from hoicon.config import get_settings
from hoicon.db.session import get_sessionmaker


async def main() -> int:
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60})
    sessions = get_sessionmaker()
    async with sessions() as session:
        who = await session.scalar(text("select current_user"))
    if who != "hoicon_app":
        print(f"Phải chạy dưới hoicon_app, đang là {who}")
        return 1
    deps = Deps(LlmRouter(None, "claude-haiku-5-5", Decimal(1)), sessions, settings)
    thread = str(uuid4())
    async with IncidentRuntime.open(deps) as runtime:
        status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        print(f"đồ thị chạy tới: {status.waiting_for or status.status}")
        await runtime.graph.checkpointer.adelete_thread(thread)
    async with sessions() as session:
        runs = await session.scalar(text("select count(*) from agent_runs where thread_id = :t"), {"t": thread})
        jobs = await session.scalar(
            text("select count(*) from jobs where idempotency_key like :p"), {"p": f"{thread}:%"}
        )
    print(f"agent_runs={runs} jobs={jobs}")
    return 0 if runs and jobs else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop))
