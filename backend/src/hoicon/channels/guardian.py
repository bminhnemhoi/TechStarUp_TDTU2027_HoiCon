"""Gửi tin Zalo cho người giám hộ (spec 002, ADR-003/010): MỘT cổng `deliver` cho mọi tin đi.

Cổng này đảm bảo, theo thứ tự:
1. gửi đúng một lần: dòng `messages_out` có `job_key` unique, tạo TRƯỚC khi gọi Zalo; dòng đã xong thì bỏ qua;
2. luật 6: tin không mở đầu bằng câu công khai AI bị từ chối (`failed`), không bao giờ ra khỏi máy chủ;
3. hạn mức theo bot/tháng: ≥ ngưỡng giữ ⇒ tin không khẩn `held_quota`; hết hạn mức ⇒ `fallback_required`; tin gắn với sự
   cố (`urgent`) bỏ qua ngưỡng giữ nhưng vẫn đếm;
4. Zalo ID chỉ được giải mã ngay lúc gọi API; lỗi chỉ mang mã trạng thái; không log nội dung tin hay định danh.

Trạng thái `messages_out.status`: queued (đang thử, thử lại được) · sent · held_quota · failed (bị cấm gửi) ·
fallback_required (kênh dự phòng xử lý — spec 023). Còn rủi ro gửi lặp hiếm: Zalo đã nhận nhưng ta mất kết nối trước khi
ghi `sent` (ADR-010).
"""

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.agents.texts import ACTION_LINK_SLOT, AI_DISCLOSURE, DRILL_LABEL
from hoicon.channels.zalo import ZaloClient, ZaloError
from hoicon.config import Settings
from hoicon.db.ids import new_id
from hoicon.db.models import Family, Member, MessageOut
from hoicon.domain.pii import decrypt_chat_id
from hoicon.jobs.queue import MAX_ATTEMPTS
from hoicon.services.action_token_service import ActionTokenService

logger = logging.getLogger(__name__)

VN_TZ = timezone(timedelta(hours=7))  # Việt Nam không có giờ mùa hè
TERMINAL = frozenset({"sent", "held_quota", "failed", "fallback_required"})


@dataclass(frozen=True)
class ChannelDeps:
    sessions: async_sessionmaker
    client: ZaloClient
    settings: Settings


@dataclass(frozen=True)
class Outgoing:
    job_key: str
    bot_id: str
    template_id: str
    text: str
    chat_enc: str | None  # `members.zalo_chat_enc` (hoặc bản mã hóa của người chưa ghép); None ⇒ không có người nhận
    urgent: bool  # tin gắn với sự cố: bỏ qua ngưỡng giữ tin
    family_id: UUID | None = None
    member_id: UUID | None = None
    incident_id: UUID | None = None
    block: str | None = None  # lý do cấm gửi ⇒ ghi `failed`, không gọi Zalo
    chat_context: str | None = (
        None  # HMAC của người nhận: bản mã `chat_enc` chỉ giải được dưới danh nghĩa đúng người này
    )
    is_drill: bool = False  # diễn tập ⇒ tin PHẢI có nhãn [DIỄN TẬP] (luật 8)


def quota_month(now: datetime | None = None) -> str:
    """Tháng hạn mức "YYYY-MM" theo giờ Việt Nam."""
    return (now or datetime.now(UTC)).astimezone(VN_TZ).strftime("%Y-%m")


def parse_uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _threshold(limit: int, pct: int) -> int:
    return math.ceil(limit * pct / 100)


async def _set(deps: ChannelDeps, row_id: UUID, status: str, error: str | None = None) -> str:
    values: dict[str, Any] = {"status": status, "error": error}
    if status == "sent":
        values["sent_at"] = func.now()
    async with deps.sessions.begin() as session:
        await session.execute(update(MessageOut).where(MessageOut.id == row_id).values(**values))
    return status


async def deliver(deps: ChannelDeps, out: Outgoing, attempt: int = 1) -> str:
    """Gửi (hoặc quyết định không gửi) một tin; trả trạng thái cuối. Lỗi tạm thời ⇒ raise `ZaloError` để job thử lại."""
    month = quota_month()
    insert_stmt = (
        insert(MessageOut)
        .values(
            id=new_id(),
            family_id=out.family_id,
            incident_id=out.incident_id,
            member_id=out.member_id,
            channel="zalo",
            bot_id=out.bot_id,
            template_id=out.template_id,
            status="queued",
            quota_month=month,
            job_key=out.job_key,
        )
        .on_conflict_do_nothing(index_elements=[MessageOut.job_key])
        .returning(MessageOut.id)
    )
    async with deps.sessions.begin() as session:
        row_id = (await session.execute(insert_stmt)).scalar_one_or_none()
        if row_id is None:  # đã có dòng cho lần xếp này (thử lại / job chạy lại)
            row = (
                await session.execute(
                    select(MessageOut.id, MessageOut.status, MessageOut.quota_month).where(
                        MessageOut.job_key == out.job_key
                    )
                )
            ).one()
            if row.status in TERMINAL:
                return row.status
            row_id, month = row.id, row.quota_month

    if out.block:
        return await _set(deps, row_id, "failed", out.block)
    if not out.text.startswith(AI_DISCLOSURE):  # luật 6: cổng cuối cùng, kể cả khi nơi gọi quên
        logger.error("zalo: từ chối tin mẫu %s vì thiếu câu công khai AI", out.template_id)
        return await _set(deps, row_id, "failed", "no_ai_disclosure")
    if out.is_drill and DRILL_LABEL not in out.text:  # luật 8: không bao giờ báo diễn tập như sự cố thật
        logger.error("zalo: từ chối tin mẫu %s vì sự cố diễn tập thiếu nhãn", out.template_id)
        return await _set(deps, row_id, "failed", "no_drill_label")
    if out.chat_enc is None:
        return await _set(deps, row_id, "fallback_required", "no_recipient")

    settings = deps.settings
    async with deps.sessions() as session:
        used = await session.scalar(
            select(func.count())
            .select_from(MessageOut)
            .where(MessageOut.bot_id == out.bot_id, MessageOut.quota_month == month, MessageOut.status == "sent")
        )
    used = used or 0
    limit = settings.zalo_monthly_quota
    if not out.urgent and used >= _threshold(limit, settings.zalo_quota_hold_pct):
        logger.warning("zalo bot %s: giữ tin không khẩn %s (đã dùng %d/%d)", out.bot_id, out.template_id, used, limit)
        return await _set(deps, row_id, "held_quota", "over_hold_threshold")
    if used >= limit:
        logger.error("zalo bot %s: hết hạn mức tháng %s (%d/%d)", out.bot_id, month, used, limit)
        return await _set(deps, row_id, "fallback_required", "quota_exhausted")

    try:
        chat_id = decrypt_chat_id(out.chat_enc, out.chat_context or "")
    except (ValueError, RuntimeError) as exc:
        logger.error("zalo: không giải mã được định danh người nhận (%s)", type(exc).__name__)
        return await _set(deps, row_id, "fallback_required", "decrypt_failed")

    try:
        await deps.client.send_message(chat_id, out.text)
    except ValueError:
        return await _set(deps, row_id, "fallback_required", "invalid_text")
    except ZaloError as exc:
        code = f"zalo_{'net' if exc.status is None else exc.status}"
        if exc.retryable and attempt < MAX_ATTEMPTS:
            async with deps.sessions.begin() as session:
                await session.execute(update(MessageOut).where(MessageOut.id == row_id).values(error=code))
            raise  # hàng đợi thử lại sau 2^n giây; dòng vẫn `queued` nên lần sau không bị coi là đã xong
        return await _set(deps, row_id, "fallback_required", code)  # lỗi vĩnh viễn hoặc hết số lần thử (FR-008)

    # Tin "gửi" bằng mock KHÔNG tới người nhận: đánh dấu error="mock" để nhìn là biết (không âm thầm như đã gửi thật).
    await _set(deps, row_id, "sent", "mock" if getattr(deps.client, "simulated", False) else None)
    if used < _threshold(limit, settings.zalo_quota_warn_pct) <= used + 1:
        logger.warning(
            "zalo bot %s: đã dùng %d/%d tin tháng %s (≥ %d%% hạn mức)",
            out.bot_id,
            used + 1,
            limit,
            month,
            settings.zalo_quota_warn_pct,
        )
    return "sent"


async def _fill_action_link(deps: ChannelDeps, payload: dict[str, Any], member: Member | None, job_key: str) -> str:
    """Tin có `action_link` (spec 023): sinh token `/a/[token]` NGAY LÚC GỬI cho đúng người nhận, chỉ lưu SHA-256 ⇒
    token thô chỉ có trong tin đi, không nằm trong `jobs.payload`. Tin đã xong (job chạy lại) hoặc không có người nhận
    ⇒ không sinh token; mỗi lần thử lại sinh token mới (token cũ chưa ra ngoài thì vô hại, tự hết hạn sau 24 giờ)."""
    text: str = payload["text"]
    if not payload.get("action_link"):
        return text
    link = ""
    async with deps.sessions.begin() as session:
        done = await session.scalar(select(MessageOut.status).where(MessageOut.job_key == job_key))
        if member is not None and done not in TERMINAL:
            _, raw = await ActionTokenService.create_token(
                session, incident_id=UUID(payload["incident_id"]), member_id=member.id
            )
            link = f"{deps.settings.web_base_url.rstrip('/')}/a/{raw}"
    return text.replace(ACTION_LINK_SLOT, link)


async def send_to_guardian(deps: ChannelDeps, payload: dict[str, Any], attempt: int = 1) -> str | None:
    """Handler của job `notify_guardian`: tìm người giám hộ đúng hạng của gia đình sự cố rồi `deliver`.

    Trả None khi sự cố chưa gắn gia đình (hành vi cũ: chỉ log). Không log nội dung tin.
    """
    template = payload["template"]
    family_id = parse_uuid(payload.get("family_id"))
    if family_id is None:
        logger.info("notify_guardian template=%s: sự cố chưa gắn gia đình, không gửi", template)
        return None
    async with deps.sessions() as session:
        family = await session.get(Family, family_id)
        if family is None:
            logger.warning("notify_guardian template=%s: không thấy gia đình, không gửi", template)
            return None
        member = (
            await session.scalars(
                select(Member).where(
                    Member.family_id == family_id,
                    Member.role == "guardian",
                    Member.guardian_rank == payload["guardian_rank"],
                )
            )
        ).one_or_none()
    # Luật 8: sự cố demo chỉ tới gia đình demo và ngược lại; không bao giờ lẫn demo với thật.
    is_demo = bool(payload.get("is_demo"))
    block = None
    if is_demo and not family.is_demo:
        block = "demo_to_real_family"
    elif family.is_demo and not is_demo:
        block = "real_to_demo_family"
    job_key = f"{payload['incident_id']}:msg:{template}"
    out = Outgoing(
        job_key=job_key,
        bot_id=member.zalo_bot_id if member and member.zalo_bot_id else deps.settings.zalo_bot_id,
        template_id=template,
        text=await _fill_action_link(deps, payload, member, job_key),
        chat_enc=member.zalo_chat_enc if member else None,
        urgent=True,
        family_id=family.id,
        member_id=member.id if member else None,
        incident_id=parse_uuid(payload.get("incident_id")),
        block=block,
        chat_context=member.zalo_user_hmac if member else None,
        is_drill=bool(payload.get("is_drill")),
    )
    return await deliver(deps, out, attempt)
