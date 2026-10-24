"""Xóa dữ liệu của một gia đình theo yêu cầu (spec 034 FR-003, plan D1, US-20.2). KHÔNG gọi LLM.

Xóa = xóa dữ liệu nghiệp vụ + ẨN DANH danh tính, GIỮ sổ đồng ý. `consents` → `families`/`members` là RESTRICT và
luật (Nghị định 356/2025) đòi giữ bằng chứng đồng ý, nên dòng `families`/`members` còn lại làm tombstone: bí danh, HMAC
Zalo và bản mã định danh bị làm rỗng, `deleted_at` được đặt. `consents` chỉ còn mục đích, đồng ý hay không, băm văn bản
và thời điểm. `data_requests` giữ lại làm vết.

Thứ tự (mỗi bước lũy đẳng, chạy lại không lỗi):
1. thu hồi mọi thiết bị TRƯỚC, để máy không gửi thêm dữ liệu trong lúc đang xóa;
2. xóa checkpoint đồ thị của từng sự cố (`adelete_thread`, kết nối riêng nên ngoài giao dịch);
3. một giao dịch xóa dữ liệu nghiệp vụ;
4. ẩn danh `members`, `families`;
5. đánh `data_requests.done`.

Thêm bảng mới có `family_id`/`incident_id` mà quên cập nhật ở đây ⇒ `tests/integration/test_purge_family.py` đỏ.
Không log nội dung hay định danh; chỉ log số dòng theo loại.
"""

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.db.ids import new_id
from hoicon.db.models import (
    ActionToken,
    AgentRun,
    DataRequest,
    Device,
    Drill,
    Family,
    Incident,
    Job,
    Member,
    MessageOut,
    PairingCode,
    RiskEventRecord,
    TrustedContact,
    Verification,
)
from hoicon.jobs.queue import enqueue

logger = logging.getLogger(__name__)

TOMBSTONE = "[đã xóa]"
DeleteThread = Callable[[str], Awaitable[None]]


class FamilyNotFoundError(Exception):
    """Không có gia đình này."""


async def request_delete(sessions: async_sessionmaker, family_id: UUID, via: str) -> DataRequest:
    """Ghi nhận yêu cầu xóa và xếp job `purge_family` (lũy đẳng: đã có yêu cầu đang chờ thì trả lại chính nó)."""
    return (await request_delete_detailed(sessions, family_id, via))[0]


async def request_delete_detailed(
    sessions: async_sessionmaker,
    family_id: UUID,
    via: str,
    *,
    notice: dict[str, Any] | None = None,
    purge_delay_s: float = 0.0,
) -> tuple[DataRequest, bool]:
    """Như `request_delete` nhưng trả thêm `created` (False = trả lại yêu cầu đang chờ). `notice`: payload job
    `notify_guardian` xếp CÙNG giao dịch và chạy TRƯỚC `purge_family` (job này hoãn `purge_delay_s` giây để tin kịp đi
    trước khi purge xóa kênh Zalo)."""
    async with sessions.begin() as session:
        if await session.get(Family, family_id) is None:
            raise FamilyNotFoundError
        pending = await session.scalar(
            select(DataRequest)
            .where(DataRequest.family_id == family_id, DataRequest.status == "pending")
            .order_by(DataRequest.requested_at)
            .limit(1)
        )
        if pending is not None:
            return pending, False
        request = DataRequest(id=new_id(), family_id=family_id, kind="delete", requested_via=via)
        session.add(request)
        await session.flush()
        if notice is not None:
            key = f"data_request:{request.id}:msg:deleted"
            await enqueue(session, "notify_guardian", {**notice, "job_key": key}, key=key)
        await enqueue(
            session,
            "purge_family",
            {"request_id": str(request.id), "family_id": str(family_id)},
            delay_s=purge_delay_s,
            key=f"purge:{request.id}",
        )
        logger.info("purge: đã ghi nhận yêu cầu %s", request.id)
        return request, True


async def purge_family(
    sessions: async_sessionmaker,
    delete_thread: DeleteThread,
    family_id: UUID,
    *,
    request_id: UUID | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Thi hành xóa; ⇒ số dòng theo loại. Lỗi ⇒ đánh yêu cầu `failed` (mã lỗi ngắn) rồi ném lại để job thử lại."""
    moment = now or datetime.now(UTC)
    try:
        report = await _purge(sessions, delete_thread, family_id, moment)
    except Exception as exc:
        if request_id is not None:
            async with sessions.begin() as session:
                await session.execute(
                    update(DataRequest)
                    .where(DataRequest.id == request_id, DataRequest.status != "done")
                    .values(status="failed", error_code=type(exc).__name__[:32], completed_at=None)
                )
        raise
    if request_id is not None:
        async with sessions.begin() as session:
            await session.execute(
                update(DataRequest)
                .where(DataRequest.id == request_id)
                .values(status="done", error_code=None, completed_at=moment)
            )
    logger.info("purge: xong, %s", ", ".join(f"{k}={v}" for k, v in report.items()))
    return report


async def _purge(
    sessions: async_sessionmaker, delete_thread: DeleteThread, family_id: UUID, now: datetime
) -> dict[str, int]:
    report: dict[str, int] = {}
    # 1) thu hồi thiết bị (giữ dòng tới bước 3 để token cũ cũng bị từ chối trong lúc xóa)
    async with sessions.begin() as session:
        revoked = await session.execute(
            update(Device).where(Device.family_id == family_id, Device.revoked_at.is_(None)).values(revoked_at=now)
        )
        report["devices_revoked"] = revoked.rowcount
        if await session.get(Family, family_id) is None:
            raise FamilyNotFoundError
        # Đóng cửa trước: token người giám hộ cũng hết hiệu lực ngay, không ghi thêm dữ liệu mới trong lúc xóa.
        await session.execute(update(Member).where(Member.family_id == family_id).values(deleted_at=now))
        await session.execute(update(Family).where(Family.id == family_id).values(deleted_at=now))
    # 2) checkpoint đồ thị của từng sự cố
    async with sessions() as session:
        incident_ids = list(await session.scalars(select(Incident.id).where(Incident.family_id == family_id)))
        thread_ids = [
            str(i) for i in incident_ids
        ]  # đồ thị thật khóa theo `thread_id` (= id sự cố); `incident_id` có thể NULL
        run_threads = list(
            await session.scalars(
                select(AgentRun.thread_id).where(
                    or_(AgentRun.incident_id.in_(incident_ids), AgentRun.thread_id.in_(thread_ids))
                )
            )
        )
    threads = {str(i) for i in incident_ids} | set(run_threads)
    for thread in threads:
        await delete_thread(thread)
    report["checkpoints"] = len(incident_ids)
    # 3) xóa dữ liệu nghiệp vụ trong MỘT giao dịch
    async with sessions.begin() as session:
        member_ids = list(await session.scalars(select(Member.id).where(Member.family_id == family_id)))
        drill_ids = list(await session.scalars(select(Drill.id).where(Drill.family_id == family_id)))
        owners = [str(i) for i in (*incident_ids, *drill_ids)]
        zalo_users = list(
            await session.scalars(
                select(Member.zalo_user_hmac).where(Member.family_id == family_id, Member.zalo_user_hmac.is_not(None))
            )
        )
        job_match = [Job.payload["family_id"].astext == str(family_id)]
        if zalo_users:  # job `zalo_update` còn sót mang bản mã định danh của người giám hộ (thường đã được làm sạch)
            job_match.append(Job.payload["user_hmac"].astext.in_(zalo_users))
        job_match += [Job.idempotency_key.startswith(f"{owner}:", autoescape=True) for owner in owners]
        report["jobs"] = (
            await session.execute(delete(Job).where(Job.kind != "purge_family", or_(*job_match)))
        ).rowcount
        report["messages_out"] = (
            await session.execute(
                update(MessageOut)  # giữ dòng (bộ đếm hạn mức Zalo đếm trên đây), chỉ cắt mọi liên kết tới gia đình
                .where(
                    or_(
                        MessageOut.family_id == family_id,
                        MessageOut.incident_id.in_(incident_ids),
                        MessageOut.member_id.in_(member_ids),
                    )
                )
                .values(family_id=None, incident_id=None, member_id=None, job_key=None)
            )
        ).rowcount
        report["action_tokens"] = (
            await session.execute(
                delete(ActionToken).where(
                    or_(ActionToken.member_id.in_(member_ids), ActionToken.incident_id.in_(incident_ids))
                )
            )
        ).rowcount
        report["agent_runs"] = (
            await session.execute(
                delete(AgentRun).where(or_(AgentRun.incident_id.in_(incident_ids), AgentRun.thread_id.in_(thread_ids)))
            )
        ).rowcount  # CASCADE sang agent_steps
        report["risk_events"] = (
            await session.execute(delete(RiskEventRecord).where(RiskEventRecord.family_id == family_id))
        ).rowcount
        report["verifications"] = (
            await session.execute(delete(Verification).where(Verification.family_id == family_id))
        ).rowcount
        report["incidents"] = (
            await session.execute(delete(Incident).where(Incident.family_id == family_id))
        ).rowcount  # CASCADE: nhật ký chuyển
        report["drills"] = (await session.execute(delete(Drill).where(Drill.family_id == family_id))).rowcount
        report["trusted_contacts"] = (
            await session.execute(delete(TrustedContact).where(TrustedContact.family_id == family_id))
        ).rowcount
        report["pairing_codes"] = (
            await session.execute(delete(PairingCode).where(PairingCode.family_id == family_id))
        ).rowcount
        report["devices"] = (await session.execute(delete(Device).where(Device.family_id == family_id))).rowcount
        # 4) ẩn danh tombstone. `consents` KHÔNG đụng tới.
        anonymized: dict[str, Any] = {
            "alias": TOMBSTONE,
            "address_form": None,
            "zalo_bot_id": None,
            "zalo_user_hmac": None,
            "zalo_hmac_kid": None,
            "zalo_chat_enc": None,
            "deleted_at": now,
        }
        await session.execute(update(Member).where(Member.family_id == family_id).values(**anonymized))
        await session.execute(
            update(Family).where(Family.id == family_id).values(display_name=TOMBSTONE, deleted_at=now)
        )
    # Job `graph_resume` đang chạy dở lúc bước 2 có thể đã ghi lại checkpoint: quét lần nữa khi job đã bị xóa hết.
    for thread in threads:
        await delete_thread(thread)
    return report
