"""Vòng đời `IncidentRuntime` + worker job trong tiến trình API (ADR-002, spec 024 P2-09).

- Runtime mở LƯỜI (`ensure_runtime`, có khóa): API vẫn khởi động được khi Postgres chưa sẵn sàng (`/healthz` sống,
  `/readyz` báo lỗi) thay vì chết ở lifespan.
- Worker là một task nền: chờ tới khi mở được runtime (thử lại có giãn cách) rồi chạy `run_worker` — job `start_graph`,
  bộ hẹn giờ T1/T2/T3, `notify_guardian`, `push_fcm`. Tắt bằng `HOICON_RUN_WORKER=false` khi chạy worker riêng.
"""

import asyncio
import contextlib
import logging
from contextlib import AsyncExitStack

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.config import Settings, get_settings
from hoicon.db.session import get_sessionmaker

logger = logging.getLogger(__name__)

_runtime: IncidentRuntime | None = None
_stack: AsyncExitStack | None = None
_lock = asyncio.Lock()
RETRY_MAX_S = 30
SHUTDOWN_WAIT_S = 10


def get_default_deps(settings: Settings | None = None) -> Deps:
    s = settings or get_settings()
    sessions = get_sessionmaker()
    return Deps(router=LlmRouter.from_settings(sessions=sessions, settings=s), sessions=sessions, settings=s)


async def ensure_runtime() -> IncidentRuntime:
    """Runtime dùng chung của tiến trình; mở lần đầu khi cần. Lỗi kết nối ⇒ ném ra, lần gọi sau thử lại."""
    global _runtime, _stack
    async with _lock:
        if _runtime is None:
            stack = AsyncExitStack()
            try:
                runtime = await stack.enter_async_context(IncidentRuntime.open(get_default_deps()))
            except BaseException:
                await stack.aclose()
                raise
            _runtime, _stack = runtime, stack
            logger.info("IncidentRuntime đã mở")
        return _runtime


async def close_runtime() -> None:
    global _runtime, _stack
    async with _lock:
        stack, _runtime, _stack = _stack, None, None
    if stack is not None:
        await stack.aclose()
        logger.info("IncidentRuntime đã đóng")


def get_runtime() -> IncidentRuntime | None:
    return _runtime


def set_runtime(runtime: IncidentRuntime | None) -> None:
    """Test: dùng runtime do test tự mở (test tự đóng nó)."""
    global _runtime
    _runtime = runtime


async def _worker_loop(stop: asyncio.Event) -> None:
    from hoicon.jobs.worker import incident_handlers, run_worker  # worker kéo theo kênh Zalo: chỉ nạp khi chạy

    delay = 1.0
    while not stop.is_set():
        try:
            runtime = await ensure_runtime()
            break
        except Exception as exc:  # DB chưa lên: chờ rồi thử lại, không làm chết API
            logger.warning("worker: chưa mở được runtime (%s), thử lại sau %.0f s", type(exc).__name__, delay)
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), delay)
            delay = min(delay * 2, RETRY_MAX_S)
    else:
        return
    try:
        handlers = incident_handlers(runtime)
    except Exception as exc:  # cấu hình sai (vd. Zalo mock ngoài dev): kêu to, `/readyz` cũng báo 503 — không chết im
        logger.error("worker: KHÔNG chạy được, cấu hình kênh gửi sai (%s): %s", type(exc).__name__, exc)
        return
    await run_worker(get_sessionmaker(), handlers, stop)


@contextlib.asynccontextmanager
async def background_worker(enabled: bool):
    """Lifespan: chạy worker nền khi `enabled`; thoát ⇒ dừng worker rồi đóng runtime."""
    stop = asyncio.Event()
    task = asyncio.create_task(_worker_loop(stop)) if enabled else None
    try:
        yield
    finally:
        stop.set()
        if task is not None:
            # Job đang chạy dở được chờ tối đa SHUTDOWN_WAIT_S; quá hạn (vd. kẹt chờ pool khi DB chết) ⇒ hủy: job đó
            # được lấy lại sau STALE_LOCK (handler idempotent), không treo việc tắt API.
            done, _ = await asyncio.wait({task}, timeout=SHUTDOWN_WAIT_S)
            if not done:
                task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await task
        await close_runtime()
