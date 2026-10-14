"""CLI spike P1-S4 — chạy đồ thị sự cố đầu–cuối, đo độ trễ từng lượt, thử chạy tiếp sau kill -9.

    uv run --directory backend python -m hoicon.agents.spike demo            # một sự cố, hẹn giờ rút ngắn
    uv run --directory backend python -m hoicon.agents.spike bench --n 20    # p50/p95 từng lượt + chi phí
    uv run --directory backend python -m hoicon.agents.spike recover         # chạy tiếp các lần chạy dở dang

Không có HOICON_ANTHROPIC_API_KEY ⇒ mọi node LLM rơi về mẫu (đo phần điều phối: checkpoint, job, trace).
`crash` chỉ dùng cho test kill -9 (tests/integration/test_graph_durable.py). Dữ liệu demo hư cấu, `is_demo`.
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep
from hoicon.db.session import get_sessionmaker
from hoicon.domain.events import RiskEvent
from hoicon.jobs.queue import cancel_prefix
from hoicon.jobs.worker import incident_handlers, run_worker

# Sự cố "giả danh công an" hư cấu: h1 của số demo flagged_caller (data/threat_seed.demo.json), cuộc gọi 7 phút.
DEMO_H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
ELDER_NOTE = "Họ nói là công an, bảo tôi chuyển tiền vào tài khoản tạm giữ để xác minh"


def demo_event(is_drill: bool = False) -> RiskEvent:
    return RiskEvent.model_validate(
        {
            "id": str(new_id()),
            "schema_version": 1,
            "type": "banking_app_foreground",
            "occurred_at": datetime.now(UTC).isoformat(),
            "rule_id": "R1",
            "rule_floor": "high",
            "is_drill": is_drill,
            "caller": {"h1": DEMO_H1, "last3": "002", "in_contacts": False},
            "call": {"direction": "incoming", "active": True, "duration_s": 420},
            "app": {"category": "bank", "package": "vn.hoicon.demobank"},
        }
    )


def deps(router: LlmRouter | None = None, **timers: int) -> Deps:
    settings = get_settings().model_copy(update=timers)
    return Deps(router=router or LlmRouter.from_settings(), sessions=get_sessionmaker(), settings=settings)


async def demo() -> None:
    d = deps(timer_ask_elder_s=30, timer_t1_s=2, timer_t2_s=4, timer_t3_s=30)
    stop = asyncio.Event()
    async with IncidentRuntime.open(d) as runtime:
        worker = asyncio.create_task(run_worker(d.sessions, incident_handlers(runtime), stop, poll_s=0.2))
        thread = str(new_id())
        t0 = time.monotonic()

        def show(label: str, status: Any) -> None:
            print(
                f"{time.monotonic() - t0:6.2f}s  {label:<22} → {status.status} @ {status.waiting_for}"
                f" · level={status.level}"
            )

        status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
        show("start", status)
        if status.waiting_for == "ask_elder":
            print(f"         E8 hỏi: {status.interrupt['text']}")
            status = await runtime.resume(thread, {"answer": "yes", "note": ELDER_NOTE}, expect="ask_elder")
            show("elder answered", status)
        await asyncio.sleep(5)  # T1 nhắc (2 s), T2 chuyển người giám hộ 2 (4 s) do worker chạy
        status = await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
        show("guardian: scam", status)
        stop.set()
        await worker
        async with d.sessions() as session:
            run = (await session.scalars(select(AgentRun).where(AgentRun.thread_id == thread))).one()
            steps = (
                await session.scalars(select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.at))
            ).all()
        print(f"\noutcome={status.outcome} · chi phí={run.cost_usd} USD · {len(steps)} bước:")
        for s in steps:
            tag = "mẫu" if s.fallback_used else (s.model or "-")
            print(f"  {s.node:<15} {s.latency_ms:>5} ms  {tag:<18} {json.dumps(s.output, ensure_ascii=False)}")


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


async def bench(n: int) -> None:
    d = deps()
    turns: dict[str, list[float]] = {"start→ask_elder": [], "answer→await_guardian": [], "decision→done": []}
    async with IncidentRuntime.open(d) as runtime:
        for _ in range(n):
            thread = str(new_id())
            t = time.monotonic()
            status = await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)
            turns["start→ask_elder"].append(time.monotonic() - t)
            if status.waiting_for == "ask_elder":
                t = time.monotonic()
                await runtime.resume(thread, {"answer": "yes", "note": ELDER_NOTE}, expect="ask_elder")
                turns["answer→await_guardian"].append(time.monotonic() - t)
            t = time.monotonic()
            await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
            turns["decision→done"].append(time.monotonic() - t)
            # bench không chạy worker: dọn tin chưa gửi + checkpoint để DB dev không ứ job demo (giữ agent_runs/steps)
            await cancel_prefix(d.sessions, f"{thread}:")
            await runtime.graph.checkpointer.adelete_thread(thread)
    async with d.sessions() as session:
        runs = (await session.scalars(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(n))).all()
    cost = sum((r.cost_usd for r in runs), Decimal(0))
    print(f"n={n} · model={d.router.fast_model} · có khóa API={d.settings.anthropic_api_key is not None}")
    for name, values in turns.items():
        if values:
            print(
                f"  {name:<24} p50 {statistics.median(values):.3f}s · p95 {percentile(values, 0.95):.3f}s · "
                f"max {max(values):.3f}s"
            )
    print(f"  chi phí trung bình/sự cố: {cost / n:.6f} USD")


class _BlockingClient:
    """`crash`: báo đã vào LLM rồi treo, để test giết tiến trình đúng lúc đang ở giữa node risk_scorer."""

    def with_options(self, **_: Any) -> "_BlockingClient":
        return self

    @property
    def messages(self) -> "_BlockingClient":
        return self

    async def parse(self, **_: Any) -> Any:
        print("LLM_CALL_STARTED", flush=True)
        await asyncio.sleep(3600)


async def crash(thread: str) -> None:
    router = LlmRouter(_BlockingClient(), get_settings().llm_fast_model, Decimal(1))
    async with IncidentRuntime.open(deps(router)) as runtime:
        await runtime.start(demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True)


async def recover() -> None:
    d = deps()
    async with IncidentRuntime.open(d) as runtime:
        for status in await runtime.recover():
            print(f"{status.thread_id}: {status.status} @ {status.waiting_for}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="hoicon.agents.spike")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    sub.add_parser("bench").add_argument("--n", type=int, default=20)
    sub.add_parser("crash").add_argument("--thread", required=True)
    sub.add_parser("recover")
    args = parser.parse_args()
    coro = {
        "demo": demo,
        "bench": lambda: bench(args.n),
        "crash": lambda: crash(args.thread),
        "recover": recover,
    }[args.cmd]()
    # psycopg async không chạy trên ProactorEventLoop (mặc định của Windows).
    asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)


if __name__ == "__main__":
    main()
