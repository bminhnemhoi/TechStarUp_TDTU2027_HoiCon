"""Webhook Zalo Bot (FR-001/002/013, ADR-003): `POST /webhooks/zalo/{bot_id}`.

Làm đúng ba việc rồi trả lời ngay: kiểm secret (hằng thời gian), thu gọn cập nhật (băm/mã hóa định danh, phân loại văn
bản — job KHÔNG mang chữ thô hay Zalo ID thô), xếp job `zalo_update` với khóa chống trùng `zalo:{bot_id}:{message_id}`.
Zalo không gửi `update_id` (docs/spikes/P1-S3-zalo.md §1) nên dùng `message_id`.

`router` được gắn vào app chính; `app` là ứng dụng con CHỈ có route này (không /docs, /openapi.json, /mcp) để phơi qua
đường hầm dev:

    uv run --directory backend uvicorn hoicon.api.webhooks:app --port 18080 --loop asyncio:SelectorEventLoop
"""

import hmac
import json
import logging
from collections import Counter

from fastapi import APIRouter, FastAPI, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from hoicon.channels.inbound import build_job_payload, parse_update
from hoicon.config import get_settings
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import enqueue

logger = logging.getLogger(__name__)

SECRET_HEADER = "X-Bot-Api-Secret-Token"  # noqa: S105 — tên header, không phải mật khẩu
MAX_BODY = 64 * 1024
MIN_SECRET_LEN, MAX_SECRET_LEN = 8, 256
# Cập nhật không dùng được (ảnh, sticker, nhóm, tin của bot…): xác nhận 200 nhưng không xếp job; đếm để quan sát.
IGNORED: Counter[str] = Counter()

router = APIRouter(tags=["webhooks"])


async def _read_body(request: Request) -> bytes:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_BODY:
        raise HTTPException(status_code=413, detail="payload too large")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():  # có thể không có Content-Length (chunked): đếm khi đọc
        size += len(chunk)
        if size > MAX_BODY:
            raise HTTPException(status_code=413, detail="payload too large")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/webhooks/zalo/{bot_id}")
async def zalo_webhook(bot_id: str, request: Request) -> dict[str, bool]:
    settings = get_settings()
    secret = settings.zalo_webhook_secret
    if secret is None or not MIN_SECRET_LEN <= len(secret.get_secret_value()) <= MAX_SECRET_LEN:  # Zalo: 8–256 ký tự
        logger.error("zalo webhook: HOICON_ZALO_WEBHOOK_SECRET thiếu hoặc không dài 8–256 ký tự ⇒ từ chối mọi cập nhật")
        raise HTTPException(status_code=503, detail="webhook not configured")
    given = request.headers.get(SECRET_HEADER, "")
    if not hmac.compare_digest(given.encode(), secret.get_secret_value().encode()):
        logger.info(
            "zalo webhook: secret sai hoặc thiếu"
        )  # info, không warning: kẻ lạ gửi bao nhiêu cũng không ngập log
        raise HTTPException(status_code=401, detail="unauthorized")
    if bot_id != settings.zalo_bot_id:  # sau xác thực: không lộ bot nào tồn tại cho người chưa có secret
        raise HTTPException(status_code=404, detail="unknown bot")

    try:
        body = json.loads(await _read_body(request))
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid json") from None

    parsed = parse_update(body)
    if parsed is None:
        IGNORED["unusable"] += 1
        logger.info("zalo webhook: bỏ qua cập nhật không dùng được (tổng %d)", IGNORED["unusable"])
        return {"ok": True}

    try:
        payload = build_job_payload(bot_id, parsed)
    except (RuntimeError, ValueError) as exc:  # thiếu khóa/pepper hoặc cấu hình sai: lỗi của ta, để Zalo gửi lại sau
        logger.error("zalo webhook: không thu gọn được cập nhật (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="service misconfigured") from None

    try:
        await enqueue(get_sessionmaker(), "zalo_update", payload, key=f"zalo:{bot_id}:{parsed.message_id}")
    except (SQLAlchemyError, OSError) as exc:  # DB lỗi ⇒ KHÔNG trả 200 (sẽ mất cập nhật); Zalo gửi lại
        logger.error("zalo webhook: không xếp được job (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="try again") from None
    return {"ok": True}


app = FastAPI(title="HỏiCon webhook", docs_url=None, redoc_url=None, openapi_url=None)
app.include_router(router)
