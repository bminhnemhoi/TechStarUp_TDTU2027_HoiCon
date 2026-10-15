"""Xử lý job `zalo_update` (spec 002): ghép người giám hộ bằng `/start <mã>` và nhận phản hồi 1/2/3.

Đầu vào là payload do webhook xếp (đã thu gọn: băm/mã hóa định danh, văn bản đã phân loại — xem `api/webhooks.py`);
module này không bao giờ thấy chữ thô hay Zalo ID thô. Mỗi cập nhật tạo đúng MỘT câu trả lời, khóa theo
`zalo:{bot_id}:{message_id}` (cùng khóa chống trùng với job) nên giao lại nhiều lần vẫn chỉ trả lời một lần.

Chống lạm dụng (review bảo mật 15/10): dò mã 6 số bị chặn theo từng Zalo (10 lần/15 phút) và theo cả bot (100 lần/15
phút); người nhắn linh tinh chỉ nhận tối đa `QUIET_AFTER` câu hướng dẫn mỗi giờ (không đốt hạn mức 3.000 tin/tháng).
"""

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.agents import texts
from hoicon.channels.guardian import ChannelDeps, Outgoing, deliver
from hoicon.db.models import AgentRun, Job, Member, MessageOut, PairingCode

if TYPE_CHECKING:
    from hoicon.agents.runtime import IncidentRuntime

logger = logging.getLogger(__name__)

RANKS = (1, 2)
ATTEMPT_WINDOW = timedelta(minutes=15)  # bằng hạn của mã ghép
MAX_START_ATTEMPTS = 10  # mỗi Zalo trong ATTEMPT_WINDOW
MAX_BOT_START_ATTEMPTS = 100  # cả bot trong ATTEMPT_WINDOW (bot gói Basic chỉ có ≤ 50 người dùng)
CHATTER_WINDOW = timedelta(hours=1)
QUIET_AFTER = 10  # sau ngần ấy tin trong CHATTER_WINDOW, câu hướng dẫn/trả lời "không có gì" không được gửi nữa
# Tin lặp lại được hoặc giá trị thấp, dễ bị lạm dụng để đốt hạn mức: im lặng sau QUIET_AFTER tin/giờ. Chỉ `ack_*`
# (xác nhận quyết định, tối đa một lần mỗi sự cố) mới được coi là khẩn khi áp ngưỡng giữ tin.
QUIET_TEMPLATES = frozenset(
    {
        "pairing_help",
        "pairing_already",
        "reply_help",
        "reply_no_incident",
        "detail_pending",
        "detail_resend",
        "incident_closed",
    }
)
# Phần định danh/mã trong job `zalo_update` chỉ cần tới lúc xử lý xong; xóa khỏi payload sau khi thành công (FR-010).
SCRUBBED_KEYS = ("chat_enc", "code_hash")


async def _count_updates(
    session: AsyncSession, window: timedelta, *, user_hmac: str | None = None, bot_id: str | None = None,
    kind: str | None = None,
) -> int:  # fmt: skip
    """Số job `zalo_update` đã xếp trong `window` (chỉ mục ix_jobs_kind_created); job này cũng được tính."""
    query = select(func.count()).select_from(Job).where(Job.kind == "zalo_update", Job.created_at > func.now() - window)
    if user_hmac is not None:
        query = query.where(Job.payload["user_hmac"].astext == user_hmac)
    if bot_id is not None:
        query = query.where(Job.payload["bot_id"].astext == bot_id)
    if kind is not None:
        query = query.where(Job.payload["kind"].astext == kind)
    return await session.scalar(query) or 0


async def _find_member(deps: ChannelDeps, bot_id: str, user_hmac: str) -> Member | None:
    async with deps.sessions() as session:
        query = select(Member).where(
            Member.zalo_bot_id == bot_id, Member.zalo_user_hmac == user_hmac, Member.role == "guardian"
        )
        return (await session.scalars(query)).one_or_none()


async def _pair(deps: ChannelDeps, payload: dict[str, Any]) -> tuple[str, Member | None, UUID | None]:
    """⇒ (mẫu trả lời, người giám hộ nếu đã/vừa ghép, gia đình). Một giao dịch: mã dùng-một-lần được khóa dòng
    (`FOR UPDATE`) nên hai người cùng gửi một mã chỉ một người được ghép; mã chỉ bị tiêu thụ khi ghép thành công."""
    async with deps.sessions.begin() as session:
        existing = (
            await session.scalars(
                select(Member).where(
                    Member.zalo_bot_id == payload["bot_id"], Member.zalo_user_hmac == payload["user_hmac"]
                )
            )
        ).one_or_none()
        family_of_existing = existing.family_id if existing else None
        fallback = ("pairing_already" if existing else "pairing_help", existing, family_of_existing)
        if payload["kind"] != "start":
            return fallback
        # Chống dò mã 6 số: giới hạn số lần thử theo từng Zalo và theo cả bot; quá giới hạn ⇒ không xét mã, trả cùng câu
        # hướng dẫn chung (đếm chính các job `zalo_update` loại start, kể cả job này).
        per_user = await _count_updates(session, ATTEMPT_WINDOW, user_hmac=payload["user_hmac"], kind="start")
        per_bot = await _count_updates(session, ATTEMPT_WINDOW, bot_id=payload["bot_id"], kind="start")
        if per_user > MAX_START_ATTEMPTS or per_bot > MAX_BOT_START_ATTEMPTS:
            logger.warning("zalo ghép đôi: quá nhiều lần thử mã trong %s (theo Zalo hoặc theo bot)", ATTEMPT_WINDOW)
            return fallback
        code = (
            await session.scalars(
                select(PairingCode)
                .where(
                    PairingCode.code_hash == payload["code_hash"],
                    PairingCode.used_at.is_(None),
                    PairingCode.expires_at > func.now(),
                )
                .with_for_update()
            )
        ).one_or_none()
        if code is None:  # sai, hết hạn hay đã dùng: cùng một câu để không lộ mã có tồn tại hay không
            return fallback
        if existing is not None:
            if existing.family_id != code.family_id:
                # Không chuyển Zalo sang gia đình khác và KHÔNG báo "mã hợp lệ của gia đình khác" (người đã ghép có thể
                # dùng câu trả lời để dò mã của gia đình khác): trả lời như mã không dùng được; mã không bị tiêu thụ.
                logger.info("zalo ghép đôi: Zalo đã thuộc một gia đình khác, giữ nguyên")
                return fallback
            code.used_at = func.now()
            return "pairing_already", existing, existing.family_id
        taken = set(
            await session.scalars(
                select(Member.guardian_rank).where(Member.family_id == code.family_id, Member.role == "guardian")
            )
        )
        free = next((rank for rank in RANKS if rank not in taken), None)
        if free is None:  # đủ người giám hộ: cũng trả lời như mã không dùng được (không xác nhận mã hợp lệ)
            logger.info("zalo ghép đôi: gia đình đã đủ người giám hộ, không thêm")
            return fallback
        member = Member(
            family_id=code.family_id,
            role="guardian",
            guardian_rank=free,
            zalo_bot_id=payload["bot_id"],
            zalo_user_hmac=payload["user_hmac"],
            zalo_hmac_kid=payload["hmac_kid"],
            zalo_chat_enc=payload["chat_enc"],
        )
        session.add(member)
        code.used_at = func.now()
        await session.flush()
        return "pairing_confirmed", member, code.family_id


async def _reply(
    deps: ChannelDeps,
    payload: dict[str, Any],
    template: str,
    text: str,
    attempt: int,
    *,
    member: Member | None = None,
    family_id: UUID | None = None,
    incident_id: UUID | None = None,
    is_drill: bool = False,
) -> str | None:
    """Trả lời đúng cuộc trò chuyện vừa nhắn tới (`chat_enc` trong payload); tin gắn sự cố được coi là khẩn.
    Tin giá trị thấp (`QUIET_TEMPLATES`) bị bỏ khi người này đã nhắn quá nhiều trong giờ qua."""
    if template in QUIET_TEMPLATES:
        async with deps.sessions() as session:
            recent = await _count_updates(session, CHATTER_WINDOW, user_hmac=payload["user_hmac"])
        if recent > QUIET_AFTER:
            logger.info("zalo: bỏ qua câu trả lời %s vì người này nhắn quá nhiều", template)
            return None
    out = Outgoing(
        job_key=f"zalo:{payload['bot_id']}:{payload['message_id']}",
        bot_id=payload["bot_id"],
        template_id=template,
        text=text,
        chat_enc=payload["chat_enc"],
        urgent=template.startswith("ack_"),
        family_id=family_id,
        member_id=member.id if member else None,
        incident_id=incident_id,
        chat_context=payload["user_hmac"],
        is_drill=is_drill,
    )
    return await deliver(deps, out, attempt)


async def handle_update(
    deps: ChannelDeps, runtime: "IncidentRuntime | None", payload: dict[str, Any], attempt: int = 1
) -> str | None:
    """Handler của job `zalo_update`. Trả trạng thái tin trả lời (None nếu không trả lời)."""
    kind = payload["kind"]
    if kind in ("start", "start_no_code"):
        template, member, family_id = await _pair(deps, payload)
        text = getattr(texts, template)()
        return await _reply(deps, payload, template, text, attempt, member=member, family_id=family_id)

    member = await _find_member(deps, payload["bot_id"], payload["user_hmac"])
    if member is None:  # chưa ghép: không ai ngoài người đã ghép được chạm vào sự cố
        return await _reply(deps, payload, "pairing_help", texts.pairing_help(), attempt)
    if kind == "choice" and runtime is not None:
        return await _answer(deps, runtime, payload, member, attempt)
    return await _reply(
        deps, payload, "reply_help", texts.reply_help(), attempt, member=member, family_id=member.family_id
    )


async def scrub_update_job(sessions: async_sessionmaker, payload: dict[str, Any]) -> None:
    """Xong việc ⇒ xóa `chat_enc`/`code_hash` khỏi payload job (giữ `user_hmac`, `kind`, `bot_id` cho việc giới hạn tần
    suất): bản mã định danh không nằm lại trong `jobs` suốt hạn lưu của job."""
    scrubbed = Job.payload
    for key in SCRUBBED_KEYS:
        scrubbed = scrubbed.op("-", return_type=JSONB)(key)
    key = f"zalo:{payload['bot_id']}:{payload['message_id']}"
    async with sessions.begin() as session:
        await session.execute(update(Job).where(Job.idempotency_key == key).values(payload=scrubbed))


async def _job_payload(deps: ChannelDeps, key: str) -> dict[str, Any] | None:
    async with deps.sessions() as session:
        return await session.scalar(select(Job.payload).where(Job.idempotency_key == key))


async def _is_drill(deps: ChannelDeps, incident: str) -> bool:
    """Nhãn diễn tập theo CHÍNH SỰ CỐ (`agent_runs.is_drill`), không theo tin gần nhất (tin trả lời không có job)."""
    async with deps.sessions() as session:
        is_drill = await session.scalar(select(AgentRun.is_drill).where(AgentRun.thread_id == incident))
    if is_drill is None:  # không thấy lần chạy: coi như thật nhưng để lại dấu vết (sai nhãn diễn tập là lỗi luật 8)
        logger.warning("zalo: không thấy agent_runs của sự cố để xác định nhãn diễn tập")
    return bool(is_drill)


async def _answer(
    deps: ChannelDeps, runtime: "IncidentRuntime", payload: dict[str, Any], member: Member, attempt: int
) -> str | None:
    """Phản hồi 1/2/3 áp vào sự cố của tin cảnh báo GẦN NHẤT đã gửi tới chính người này (ADR-010): 1 ⇒ an toàn,
    2 ⇒ nghi lừa đảo (resume `await_guardian`), 3 ⇒ gửi lại chi tiết, không đổi trạng thái chờ."""
    async with deps.sessions() as session:
        last = (
            await session.scalars(
                select(MessageOut)
                .where(
                    MessageOut.member_id == member.id,
                    MessageOut.status == "sent",
                    MessageOut.incident_id.is_not(None),
                )
                .order_by(MessageOut.sent_at.desc())
                .limit(1)
            )
        ).one_or_none()
    reply: dict[str, Any] = {"member": member, "family_id": member.family_id}
    if last is None:
        return await _reply(deps, payload, "reply_no_incident", texts.reply_no_incident(), attempt, **reply)

    incident_id = last.incident_id
    incident = str(incident_id)
    is_drill = await _is_drill(deps, incident)
    reply.update(incident_id=incident_id, is_drill=is_drill)
    choice = payload["choice"]

    if choice == "3":
        detail = await _job_payload(deps, f"{incident}:msg:detail")
        if detail is None:  # chi tiết chỉ có sau khi hỏi xong người cao tuổi
            return await _reply(deps, payload, "detail_pending", texts.detail_pending(is_drill), attempt, **reply)
        return await _reply(deps, payload, "detail_resend", detail["text"], attempt, **reply)

    decision = "safe" if choice == "1" else "scam"
    if await runtime.resume(incident, {"decision": decision}, expect="await_guardian") is None:
        text = texts.reply_incident_closed(is_drill)  # đồ thị không còn chờ: đến muộn hoặc đã có quyết định
        return await _reply(deps, payload, "incident_closed", text, attempt, **reply)
    return await _reply(deps, payload, f"ack_{decision}", texts.guardian_ack(decision, is_drill), attempt, **reply)
