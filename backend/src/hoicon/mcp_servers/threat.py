"""MCP server `threat` (gắn tại /mcp/threat): tra số điện thoại đã băm (h1) trong danh sách đe dọa của HỏiCon.

Chỉ nhận h1, không bao giờ nhận số thô. Danh sách nằm trong bảng `threat_indicators` (spec 003): chỉ
`HMAC(pepper[kid], h1)`, không lưu h1 (ADR-006); nạp bằng `python -m hoicon.ops.threat_list load <tệp>`. Đồ thị
sự cố gọi thẳng `lookup_h1` (cùng tiến trình, ADR-002); MCP để tác tử bên ngoài (Claude qua MCP connector, công cụ
đội) dùng chung đúng một nguồn.

Xác thực Bearer + giới hạn tần suất của `/mcp/threat` nằm ở `mcp_servers/auth.py` (h1 không có muối nên ai gọi được
MCP cũng dò được danh sách bằng cách thử hết số VN).
"""

import re
from typing import Literal

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel
from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hoicon.db.models import ThreatIndicator
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import candidate_hmacs
from hoicon.mcp_servers import auth

_H1 = re.compile(r"[0-9a-f]{64}")  # dùng `fullmatch`: `$` của `re` cho lọt "\n" ở cuối
NO_LIST_VERSION = "none"


class ThreatVerdict(BaseModel):
    verdict: Literal["flagged", "unknown"]
    source: str | None = None
    confidence: float = 0.0
    tactic: str | None = None
    list_version: str
    is_demo: bool = False  # dòng demo (số hư cấu): kết luận của dịch vụ xác minh mang cờ này ra ngoài


async def lookup_h1(sessions: async_sessionmaker | AsyncSession, h1: str) -> ThreatVerdict:
    """Tra theo HMAC với mọi kid pepper đã cấu hình; dòng quá hạn ⇒ `unknown`. h1 sai định dạng ⇒ `ValueError`.
    Nhận một `AsyncSession` đang mở ⇒ tra trong chính giao dịch đó (không mượn thêm kết nối của pool)."""
    if not _H1.fullmatch(h1):
        raise ValueError("h1 phải là SHA-256 hex chữ thường (64 ký tự) — không gửi số điện thoại thô")
    keys = candidate_hmacs(h1)
    if isinstance(sessions, AsyncSession):
        return await _lookup(sessions, keys)
    async with sessions() as session:
        return await _lookup(session, keys)


async def _lookup(session: AsyncSession, keys: list[tuple[int, str]]) -> ThreatVerdict:
    hit = (
        await session.scalars(
            select(ThreatIndicator)
            .where(
                ThreatIndicator.kind == "phone",
                tuple_(ThreatIndicator.value_kid, ThreatIndicator.value_hmac).in_(keys),
                or_(ThreatIndicator.expires_at.is_(None), ThreatIndicator.expires_at > func.now()),
            )
            .order_by(ThreatIndicator.confidence.desc())
            .limit(1)
        )
    ).first()
    if hit is not None:
        return ThreatVerdict(
            verdict="flagged",
            source=hit.source,
            confidence=float(hit.confidence),
            tactic=hit.tactic,
            list_version=hit.list_version,
            is_demo=hit.is_demo,
        )
    latest = await session.scalar(select(func.max(ThreatIndicator.list_version)))
    return ThreatVerdict(verdict="unknown", list_version=latest or NO_LIST_VERSION)


mcp = MCPServer(
    "hoicon-threat",
    instructions="Tra cứu số điện thoại đã băm (h1 = SHA-256 của 'hoicon:v1:' + số E.164) trong danh sách lừa đảo của "
    "HỏiCon. Không bao giờ gửi số điện thoại thô.",
)


@mcp.tool()
async def lookup_phone(h1: str) -> ThreatVerdict:
    """Tra một số điện thoại đã băm. Trả `flagged` (kèm nguồn, độ tin cậy, thủ đoạn) hoặc `unknown`."""
    verdict = await lookup_h1(get_sessionmaker(), h1)
    auth.note(tool="lookup_phone", verdict=verdict.verdict)  # dòng log của guard: chỉ tên tool + kết luận, không h1
    return verdict
