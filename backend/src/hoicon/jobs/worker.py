"""Worker job: một task nền trong cùng tiến trình ở dev (ADR-002), tách tiến trình riêng ở prod bằng cùng mã."""

import asyncio
import contextlib
import logging
import os
import socket
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents.runtime import IncidentRuntime
from hoicon.jobs.queue import Handler, run_once

logger = logging.getLogger(__name__)


def incident_handlers(runtime: IncidentRuntime) -> dict[str, Handler]:
    async def graph_resume(payload: dict[str, Any]) -> None:
        await runtime.resume(payload["thread_id"], payload["value"], expect=payload.get("expect"))

    async def notify_guardian(payload: dict[str, Any]) -> None:
        # ponytail: chưa gửi thật — Zalo qua bộ kiểm hạn mức `messages_out` ở P1-S3/P2-07. Không log nội dung tin.
        logger.info("notify_guardian template=%s rank=%s", payload["template"], payload["guardian_rank"])

    return {"graph_resume": graph_resume, "notify_guardian": notify_guardian}


async def run_worker(
    sessions: async_sessionmaker, handlers: dict[str, Handler], stop: asyncio.Event, poll_s: float = 0.5
) -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    while not stop.is_set():
        if await run_once(sessions, handlers, worker_id):
            continue  # còn việc: lấy tiếp ngay
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), poll_s)
