"""Worker job: một task nền trong cùng tiến trình ở dev (ADR-002), tách tiến trình riêng ở prod bằng cùng mã."""

import asyncio
import contextlib
import logging
import os
import socket
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents.runtime import IncidentRuntime
from hoicon.channels.fcm import get_fcm_client
from hoicon.channels.guardian import ChannelDeps, send_to_guardian
from hoicon.channels.updates import handle_update, scrub_update_job
from hoicon.channels.zalo import build_zalo_client
from hoicon.config import get_settings
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import ATTEMPT_KEY, MAX_ATTEMPTS, Handler, run_once
from hoicon.services import purge_service, retention_service
from hoicon.services.drill_service import DrillService

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

    async def push_fcm(payload: dict[str, Any]) -> None:
        await get_fcm_client().send_elder_question(
            incident_id=payload["incident_id"], question_id=payload["question_id"], is_drill=payload["is_drill"]
        )

    async def start_graph(payload: dict[str, Any]) -> None:
        # Payload đã qua `IncidentRuntime.prepare` ở `POST /v1/events`: không h1, không tên gói (ADR-006).
        await runtime.start_prepared(
            payload["event"],
            payload["threat"],
            incident_id=payload["incident_id"],
            elder_alias=payload["elder_alias"],
            family_id=payload["family_id"],
            is_demo=payload["is_demo"],
            guardian_alerts=payload.get("guardian_alerts", True),  # job cũ chưa có khóa này
            sim=payload.get("sim", False),
        )

    async def drill_expire(payload: dict[str, Any]) -> None:
        # Spec 028: bộ hẹn giờ của một bài. Lũy đẳng: bài đã xong thì không có gì để làm; quét cả các bài quá hạn khác.
        async with get_sessionmaker().begin() as session:
            await DrillService.expire(session)

    async def retention(payload: dict[str, Any]) -> None:
        # Spec 034: hạn lưu hằng ngày. Checkpoint xóa qua bộ lưu của chính đồ thị đang chạy.
        await retention_service.run_retention(get_sessionmaker(), runtime.graph.checkpointer.adelete_thread)

    async def purge_family(payload: dict[str, Any]) -> None:
        # Spec 034: xóa dữ liệu gia đình theo yêu cầu. Lũy đẳng; lỗi ⇒ yêu cầu `failed` + job thử lại.
        await purge_service.purge_family(
            get_sessionmaker(),
            runtime.graph.checkpointer.adelete_thread,
            UUID(payload["family_id"]),
            request_id=UUID(payload["request_id"]),
        )

    return {
        "graph_resume": graph_resume,
        "notify_guardian": notify_guardian,
        "zalo_update": zalo_update,
        "push_fcm": push_fcm,
        "start_graph": start_graph,
        "drill_expire": drill_expire,
        "retention": retention,
        "purge_family": purge_family,
    }


async def _schedule_retention(
    sessions: async_sessionmaker, scheduled: str | None, retry_at: float
) -> tuple[str | None, float]:
    """Mỗi ngày (giờ Việt Nam) xếp MỘT job `retention` (khóa `retention:<ngày>` ⇒ nhiều worker, nhiều lần khởi động
    trong ngày vẫn chỉ một job). Lỗi (DB chập chờn) ⇒ thử lại sau 60 giây, không làm chết worker.
    ⇒ (ngày đã xếp, mốc thử lại)."""
    key = retention_service.retention_key(datetime.now(UTC))
    if key == scheduled or time.monotonic() < retry_at:
        return scheduled, retry_at
    try:
        await retention_service.schedule_daily(sessions)
    except Exception as exc:
        logger.warning("retention: chưa xếp được job hằng ngày (%s)", type(exc).__name__)
        return scheduled, time.monotonic() + 60
    return key, retry_at


async def run_worker(
    sessions: async_sessionmaker, handlers: dict[str, Handler], stop: asyncio.Event, poll_s: float = 0.5
) -> None:
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    scheduled: str | None = None
    retry_at = 0.0
    while not stop.is_set():
        if "retention" in handlers:
            scheduled, retry_at = await _schedule_retention(sessions, scheduled, retry_at)
        if await run_once(sessions, handlers, worker_id):
            continue  # còn việc: lấy tiếp ngay
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), poll_s)
