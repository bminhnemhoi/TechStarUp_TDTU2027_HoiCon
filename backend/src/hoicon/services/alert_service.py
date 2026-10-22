"""`AlertService` — Kích hoạt cảnh báo khẩn cấp tới người giám hộ (spec 023, P2-07, Gate M1).

Nguyên tắc:
1. Fast Alert không phụ thuộc LLM (hoạt động kể cả khi mất mạng ngoài hay LLM hết hạn mức).
2. Xếp job `notify_guardian` cùng giao dịch với lô sự kiện; tin mở đầu công khai AI (Luật 6), nhãn [DIỄN TẬP] (Luật 8).
3. Token `/a/[token]` KHÔNG sinh ở đây: job chỉ mang chỗ trống `ACTION_LINK_SLOT`, bên gửi (`send_to_guardian`) sinh
   token ngay lúc gửi và chỉ lưu SHA-256 ⇒ token thô không bao giờ nằm trong `jobs.payload` hay bất kỳ bảng nào.
4. Idempotent theo `incident.id` (khóa job `{incident}:msg:fast_alert`, trùng khóa với node `fast_alert` của đồ thị).
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from hoicon.agents.texts import ACTION_LINK_SLOT, guardian_fast_alert_with_link
from hoicon.db.ids import new_id
from hoicon.db.models import Incident, Job, Member, RiskEventRecord
from hoicon.domain.events import RiskEvent

logger = logging.getLogger(__name__)


class AlertService:
    @staticmethod
    async def trigger_guardian_fast_alert(
        session: AsyncSession, *, incident: Incident, event: RiskEvent | None = None, sim: bool = False
    ) -> bool:
        """Xếp cảnh báo giai đoạn 1 cho người giám hộ hạng đầu. True nếu vừa xếp; False nếu đã xếp trước đó hoặc gia
        đình chưa có người giám hộ. Không commit: người gọi sở hữu giao dịch."""
        guardian = await session.scalar(
            select(Member)
            .where(Member.family_id == incident.family_id, Member.role == "guardian")
            .order_by(Member.guardian_rank.asc().nullslast())
            .limit(1)
        )
        if guardian is None:
            logger.warning("fast_alert: gia đình của sự cố %s chưa có người giám hộ", incident.id)
            return False

        protected = await session.get(Member, incident.member_id)
        alias = (protected.alias if protected else None) or "Bố/Mẹ"
        app_category, last3 = "bank", None
        if event is not None:
            app_category = (event.app.category if event.app else None) or app_category
            last3 = event.caller.last3 if event.caller else None
        elif incident.opened_by_event_id is not None:
            opened_by = await session.get(RiskEventRecord, incident.opened_by_event_id)
            if opened_by is not None:
                app_category = opened_by.app_category or app_category
                last3 = opened_by.caller_last3

        payload: dict[str, Any] = {
            "template": "fast_alert",
            "family_id": str(incident.family_id),
            "guardian_rank": guardian.guardian_rank or 1,
            "incident_id": str(incident.id),
            "text": guardian_fast_alert_with_link(alias, last3, app_category, incident.is_drill, ACTION_LINK_SLOT),
            "action_link": True,
            "is_demo": incident.is_demo,
            "is_drill": incident.is_drill,
        }
        if sim:  # spec 033 FR-004: tin của sự cố mô phỏng không bao giờ ra khỏi máy chủ
            payload["sim"] = True
        inserted = await session.scalar(
            insert(Job)
            .values(
                id=new_id(), kind="notify_guardian", payload=payload, idempotency_key=f"{incident.id}:msg:fast_alert"
            )
            .on_conflict_do_nothing(index_elements=[Job.idempotency_key])
            .returning(Job.id)
        )
        if inserted is not None:
            logger.info("fast_alert: đã xếp cảnh báo cho sự cố %s", incident.id)
        return inserted is not None
