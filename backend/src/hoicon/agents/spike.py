"""CLI spike P1-S4 — chạy đồ thị sự cố đầu–cuối, đo độ trễ từng lượt, thử chạy tiếp sau kill -9.

    uv run --directory backend python -m hoicon.agents.spike demo            # một sự cố, hẹn giờ rút ngắn
    uv run --directory backend python -m hoicon.agents.spike demo --family <tên>   # gửi tin tới gia đình dev (spec 002)
    uv run --directory backend python -m hoicon.agents.spike bench --n 20    # p50/p95 từng lượt + chi phí
    uv run --directory backend python -m hoicon.agents.spike bench --n 20 --model claude-haiku-4-5 --json out.json
    uv run --directory backend python -m hoicon.agents.spike recover         # chạy tiếp các lần chạy dở dang

Không có HOICON_ANTHROPIC_API_KEY ⇒ mọi node LLM rơi về mẫu (đo phần điều phối: checkpoint, job, trace).
`crash` chỉ dùng cho test kill -9 (tests/integration/test_graph_durable.py). Dữ liệu demo hư cấu, `is_demo`.
"""

import argparse
import asyncio
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import MODELS, LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, AgentStep, Family, Incident, Job, Member, MessageOut
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
    return Deps(
        router=router or LlmRouter.from_settings(sessions=get_sessionmaker()),
        sessions=get_sessionmaker(),
        settings=settings,
    )


async def family_id_by_name(sessions: Any, name: str) -> str:
    """Gia đình dev tạo bằng `python -m hoicon.ops.pairing_code --family <tên>` (sự cố demo chỉ tới gia đình demo)."""
    async with sessions() as session:
        found = (await session.scalars(select(Family.id).where(Family.display_name == name))).first()
    if found is None:
        raise SystemExit(f"Không thấy gia đình dev '{name}'. Tạo: python -m hoicon.ops.pairing_code --family {name}")
    return str(found)


async def ensure_demo_incident(sessions: Any, family_id: str, incident: str) -> None:
    """Sự cố demo gửi tin cho người giám hộ cần hàng `incidents` thật (spec 021: `messages_out.incident_id` có FK)."""
    async with sessions.begin() as session:
        member_id = await session.scalar(
            select(Member.id).where(Member.family_id == UUID(family_id), Member.role == "protected").limit(1)
        )
        if member_id is None:
            member = Member(family_id=UUID(family_id), role="protected")
            session.add(member)
            await session.flush()
            member_id = member.id
        session.add(
            Incident(
                id=UUID(incident),
                family_id=UUID(family_id),
                member_id=member_id,
                level="high",
                rule_floor="high",
                is_demo=True,
            )
        )


async def report_messages(sessions: Any, incident: str) -> None:
    """Tin đã gửi cho sự cố + độ trễ `jobs.created_at → messages_out.sent_at` (nguồn số đo SC-001, spec 002 R4)."""
    query = (
        select(MessageOut, Job.created_at)
        .join(Job, Job.idempotency_key == MessageOut.job_key)
        .where(MessageOut.incident_id == UUID(incident))
        .order_by(Job.created_at)
    )
    async with sessions() as session:
        rows = (await session.execute(query)).all()
    print(f"\ntin gửi người giám hộ ({len(rows)}):")
    for message, queued_at in rows:
        latency = f"{(message.sent_at - queued_at).total_seconds() * 1000:7.0f} ms" if message.sent_at else "      –"
        print(f"  {message.template_id:<12} {message.status:<18} {latency}  {message.error or ''}")


async def demo(family: str | None = None) -> None:
    d = deps(timer_ask_elder_s=30, timer_t1_s=2, timer_t2_s=4, timer_t3_s=30)
    family_id = await family_id_by_name(d.sessions, family) if family else None
    print(f"gửi tin: {d.settings.zalo_mode} · gia đình: {family or '(không — chỉ log)'}")
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

        if family_id:
            await ensure_demo_incident(d.sessions, family_id, thread)
        status = await runtime.start(
            demo_event(), incident_id=thread, elder_alias="Mẹ", is_demo=True, family_id=family_id
        )
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
        if family_id:
            await report_messages(d.sessions, thread)
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


def host_description() -> str:
    """Mô tả máy đo (hệ điều hành, kiến trúc, số lõi) — không hostname, không tên người dùng."""
    return f"{platform.system()} {platform.machine()} · {os.cpu_count()} lõi"


async def bench(n: int, model: str | None = None, json_path: Path | None = None) -> dict[str, Any]:
    """Đo `n` sự cố đầu–cuối. `model` ghi đè `llm_fast_model` (phải có trong bảng giá) CHỈ cho lần đo này.

    Trả (và ghi ra `json_path` nếu có) báo cáo theo `docs/schemas/bench_report.v1.json`. Không có khóa API ⇒
    `llm_mode = "fallback"`: số đo chỉ là điều phối (checkpoint, job, trace), KHÔNG phải số của model."""
    settings = get_settings()
    if model is not None:
        if model not in MODELS:
            print(
                f"Model chưa có giá trong bảng giá (llm_router.MODELS): {model}. Có: {', '.join(MODELS)}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        settings = settings.model_copy(update={"llm_fast_model": model})
    router = LlmRouter.from_settings(settings, get_sessionmaker())
    d = Deps(router=router, sessions=get_sessionmaker(), settings=settings)
    turns: dict[str, list[float]] = {"start→ask_elder": [], "answer→await_guardian": [], "decision→done": []}
    threads: list[str] = []
    async with IncidentRuntime.open(d) as runtime:
        for _ in range(n):
            thread = str(new_id())
            threads.append(thread)
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
        # Chỉ run do lần đo này tạo (thread_id đã biết): run khác chạy cùng lúc không lẫn vào chi phí/tỷ lệ rơi về mẫu.
        runs = (await session.scalars(select(AgentRun).where(AgentRun.thread_id.in_(threads)))).all()
        llm_steps = (
            await session.scalars(
                select(AgentStep.fallback_used).where(
                    AgentStep.run_id.in_([r.id for r in runs]), AgentStep.model_profile.is_not(None)
                )
            )
        ).all()
    cost = sum((r.cost_usd for r in runs), Decimal(0))
    fallback_rate = sum(llm_steps) / len(llm_steps) if llm_steps else 1.0
    has_key = bool(d.settings.anthropic_api_key)  # cùng phép thử với LlmRouter.from_settings: khóa RỖNG = không có khóa
    report: dict[str, Any] = {
        "model": d.router.fast_model,
        "llm_mode": "live" if has_key and fallback_rate < 1 else "fallback",
        "n": n,
        "turns": {
            name: {
                "p50_s": round(statistics.median(values), 4),
                "p95_s": round(percentile(values, 0.95), 4),
                "max_s": round(max(values), 4),
            }
            for name, values in turns.items()
            if values
        },
        "fallback_rate": round(fallback_rate, 4),
        "cost_usd_avg": float(round(cost / n, 6)),
        "measured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": host_description(),
    }
    print(f"n={n} · model={report['model']} · có khóa API={has_key} · chế độ LLM={report['llm_mode']}")
    for name, stats in report["turns"].items():
        print(f"  {name:<24} p50 {stats['p50_s']:.3f}s · p95 {stats['p95_s']:.3f}s · max {stats['max_s']:.3f}s")
    print(f"  tỷ lệ rơi về mẫu: {report['fallback_rate']:.0%} · chi phí trung bình/sự cố: {cost / n:.6f} USD")
    if report["llm_mode"] == "fallback":
        print("  ⚠ không có lời gọi LLM thật: số đo chỉ là điều phối, KHÔNG phải số của model.")
    if json_path is not None:
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        await asyncio.to_thread(json_path.write_text, text, encoding="utf-8")
        print(f"  báo cáo: {json_path}")
    return report


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


def _positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("phải ≥ 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hoicon.agents.spike")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo").add_argument("--family", help="tên gia đình dev để gửi tin thật qua kênh Zalo")
    bench_cmd = sub.add_parser("bench")
    bench_cmd.add_argument("--n", type=_positive, default=20)
    bench_cmd.add_argument(
        "--model", help="model của hồ sơ fast (phải có trong llm_router.MODELS); mặc định theo cấu hình"
    )
    bench_cmd.add_argument("--json", type=Path, help="ghi báo cáo theo docs/schemas/bench_report.v1.json")
    sub.add_parser("crash").add_argument("--thread", required=True)
    sub.add_parser("recover")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    coro = {
        "demo": lambda: demo(args.family),
        "bench": lambda: bench(args.n, args.model, args.json),
        "crash": lambda: crash(args.thread),
        "recover": recover,
    }[args.cmd]()
    # psycopg async không chạy trên ProactorEventLoop (mặc định của Windows).
    asyncio.run(coro, loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)


if __name__ == "__main__":
    main()
