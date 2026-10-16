"""Kênh đẩy câu hỏi E8 tới app Lính gác qua FCM (spec 024, P2-08, ADR-009).

- Data message chỉ mang mã: `incident_id`, `question_id`, `is_drill`. Không số điện thoại, không nội dung câu hỏi: app
  kéo câu hỏi (đã có câu công khai AI) bằng `GET /v1/incidents/{id}/pending-question` với token thiết bị của mình.
- CHƯA có Firebase (tài khoản P0-08) ⇒ chỉ có chế độ mock: ghi nhận tin trong bộ nhớ (có trần) để test/demo. Gửi thật
  là việc của spec sau, khi có khóa dịch vụ và bảng token FCM của thiết bị.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.jobs.queue import enqueue

logger = logging.getLogger(__name__)
MOCK_KEEP = 100  # worker chạy lâu: chỉ giữ chừng này tin mock gần nhất


@dataclass(frozen=True)
class FcmMessage:
    incident_id: str
    question_id: str
    is_drill: bool
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MockFcmClient:
    def __init__(self) -> None:
        self.sent: deque[FcmMessage] = deque(maxlen=MOCK_KEEP)

    async def send_elder_question(self, *, incident_id: str, question_id: str, is_drill: bool) -> None:
        self.sent.append(FcmMessage(incident_id=incident_id, question_id=question_id, is_drill=is_drill))
        logger.info("fcm [MOCK]: câu hỏi E8 incident=%s question=%s drill=%s", incident_id, question_id, is_drill)


_client = MockFcmClient()


def get_fcm_client() -> MockFcmClient:
    return _client


async def notify_elder_fcm(
    sessions: async_sessionmaker, *, incident_id: UUID | str, question_id: str, is_drill: bool
) -> None:
    """Xếp job `push_fcm`. Khóa theo sự cố + câu hỏi ⇒ node `ask_elder` chạy lại không đẩy trùng."""
    payload = {"incident_id": str(incident_id), "question_id": question_id, "is_drill": is_drill}
    await enqueue(sessions, "push_fcm", payload, key=f"{incident_id}:fcm:ask_elder:{question_id}")
