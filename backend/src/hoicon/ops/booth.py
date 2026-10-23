"""Đặt lại gian trưng bày giữa hai khách (spec 050 FR-005b).

    uv run --directory backend python -m hoicon.ops.booth reset --confirm-demo

Xóa MỌI lượt mô phỏng (thiết bị nhãn `sim:`) của gia đình `is_demo`: sự cố (kéo theo chuyển trạng thái, hồ sơ, token),
`agent_runs` + bước, job, checkpoint LangGraph, và các thiết bị mô phỏng. KHÔNG đụng gia đình
thật, sự cố demo thường (thiết bị không phải `sim:`), đồng ý, hay chính gia đình demo.
Lũy đẳng; in số đã xóa và thời gian. Cờ `--confirm-demo` luôn bắt buộc.
"""

import argparse
import asyncio
import sys
import time
from typing import Any

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents.runtime import open_checkpointer
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, Device, Family, Incident, Job
from hoicon.db.session import get_sessionmaker
from hoicon.services.sim_service import SIM_LABEL_PREFIX

CHUNK = 200


def _chunks(items: list[str]) -> list[list[str]]:
    return [items[i : i + CHUNK] for i in range(0, len(items), CHUNK)]


async def reset_sim(sessions: async_sessionmaker, database_url: str | None = None) -> dict[str, Any]:
    """⇒ {"incidents": n, "devices": m, "seconds": s}. Chỉ xóa dữ liệu mô phỏng của gia đình demo.

    Chọn và xóa trong CÙNG một giao dịch (khóa dòng) để lượt tạo giữa chừng không bị bỏ sót hay mồ côi; chỉ xóa sự cố
    `is_demo` của thiết bị `sim:` thuộc gia đình `is_demo`; chỉ xóa thiết bị khi không còn sự cố nào gắn với nó.
    Checkpoint
    LangGraph xóa SAU khi dữ liệu đã xóa (checkpoint mồ côi vô hại; ngược lại thì sự cố còn mà checkpoint mất)."""
    started = time.monotonic()
    demo_sim_device = (Device.label.startswith(SIM_LABEL_PREFIX)) & Device.family_id.in_(
        select(Family.id).where(Family.is_demo.is_(True))
    )
    async with sessions.begin() as session:
        incidents = [
            str(i)
            for i in await session.scalars(
                select(Incident.id)
                .join(Device, Device.id == Incident.device_id)
                .where(demo_sim_device, Incident.is_demo.is_(True))
                .with_for_update(of=Incident)
            )
        ]
        for batch in _chunks(incidents):
            await session.execute(
                delete(Job).where(or_(*[Job.idempotency_key.startswith(f"{i}:", autoescape=True) for i in batch]))
            )
            await session.execute(delete(AgentRun).where(AgentRun.thread_id.in_(batch)))
            await session.execute(delete(Incident).where(Incident.id.in_(batch)))
        in_use = select(Incident.device_id).where(Incident.device_id.is_not(None))
        devices = (await session.execute(delete(Device).where(demo_sim_device, Device.id.not_in(in_use)))).rowcount or 0
    if incidents:
        async with open_checkpointer(database_url or get_settings().database_url.get_secret_value()) as saver:
            for thread in incidents:
                await saver.adelete_thread(thread)
    return {"incidents": len(incidents), "devices": devices, "seconds": round(time.monotonic() - started, 2)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    reset = sub.add_parser("reset", help="xóa mọi lượt mô phỏng của gia đình demo")
    reset.add_argument(
        "--confirm-demo", action="store_true", required=True, help="xác nhận chỉ xóa dữ liệu mô phỏng của gia đình demo"
    )
    return parser


async def execute(args: argparse.Namespace) -> int:
    settings = get_settings()
    if not (settings.is_dev_env or settings.sim_enabled):
        print("Từ chối: chỉ chạy ở môi trường dev hoặc khi HOICON_SIM_ENABLED=true (dữ liệu mô phỏng chỉ có ở đó).")
        return 2
    print("Lưu ý: dừng màn hình /booth trước khi đặt lại nếu đang chạy.")
    done = await reset_sim(get_sessionmaker())
    print(f"Đã đặt lại gian: {done['incidents']} lượt mô phỏng, {done['devices']} thiết bị, {done['seconds']} giây.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(execute(args), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
