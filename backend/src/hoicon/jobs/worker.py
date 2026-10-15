"""Worker job: một task nền trong cùng tiến trình ở dev (ADR-002), tách tiến trình riêng ở prod bằng cùng mã."""

import asyncio
import contextlib
import logging
import os
import socket
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents.runtime import IncidentRuntime
from hoicon.channels.guardian import ChannelDeps, send_to_guardian
from hoicon.channels.updates import handle_update, scrub_update_job
from hoicon.channels.zalo import build_zalo_client
from hoicon.config import get_settings
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import ATTEMPT_KEY, MAX_ATTEMPTS, Handler, run_once

logger = logging.getLogger(__name__)


def incident_handlers(runtime: IncidentRuntime, channel: ChannelDeps | None = None) -> dict[str, Handler]:
    """`channel` mặc định: client theo `HOICON_ZALO_MODE` (mặc định mock; `live` thiếu token ⇒ lỗi khi khởi động)."""
    settings = get_settings()
    channel = channel or ChannelDeps(get_sessionmaker(), build_zalo_client(settings), settings)

    async def graph_resume(payload: dict[str, Any]) -> None:
        await runtime.resume(payload["thread_id"], payload["value"], expect=payload.get("expect"))

    async def notify_guardian(payload: dict[str, Any]) -> None:
        await send_to_guardian(channel, payload, attempt=payload.get(ATTEMPT_KEY, 1))

    async def zalo_update(payload: dict[str, Any]) -> None:
        attempt = payload.get(ATTEMPT_KEY, 1)
        try:
            await handle_update(channel, runtime, payload, attempt=attempt)
        except Exception:
            if attempt >= MAX_ATTEMPTS:  # lần thử cuối cũng lỗi: job sẽ dừng hẳn, đừng để bản mã định danh nằm lại
                await scrub_update_job(channel.sessions, payload)
            raise
        await scrub_update_job(channel.sessions, payload)  # xong rồi: bản mã định danh không nằm lại trong `jobs`

    return {"graph_resume": graph_resume, "notify_guardian": notify_guardian, "zalo_update": zalo_update}


async def run_worker(
    sessions: async_sessionmaker, handlers: dict[str, Handler], stop: asyncio.Event, poll_s: float = 0.5
) -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    while not stop.is_set():
        if await run_once(sessions, handlers, worker_id):
            continue  # còn việc: lấy tiếp ngay
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), poll_s)
