"""MCP server `threat` (gắn tại /mcp/threat): tra số điện thoại đã băm (h1) trong danh sách đe dọa của HỏiCon.

Chỉ nhận h1, không bao giờ nhận số thô. Đồ thị sự cố gọi thẳng `lookup_h1` (cùng tiến trình, ADR-002); MCP để tác tử
bên ngoài (Claude qua MCP connector, công cụ đội) dùng chung đúng một nguồn.

ponytail: danh sách nạp từ `data/threat_seed.demo.json` (chỉ số hư cấu); bảng `threat_indicators` + HMAC ở P2-11.
Trước khi mở ra Internet phải có xác thực + giới hạn tần suất: h1 không có muối nên tra được bằng cách thử hết số VN.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel

SEED = Path(__file__).resolve().parents[4] / "data" / "threat_seed.demo.json"
_H1 = re.compile(r"^[0-9a-f]{64}$")


class ThreatVerdict(BaseModel):
    verdict: Literal["flagged", "unknown"]
    source: str | None = None
    confidence: float = 0.0
    tactic: str | None = None
    list_version: str


@lru_cache
def _seed() -> dict[str, Any]:
    return json.loads(SEED.read_text(encoding="utf-8"))


def lookup_h1(h1: str) -> ThreatVerdict:
    if not _H1.match(h1):
        raise ValueError("h1 phải là SHA-256 hex chữ thường (64 ký tự) — không gửi số điện thoại thô")
    seed = _seed()
    hit = next((i for i in seed["indicators"] if i["h1"] == h1), None)
    if hit is None:
        return ThreatVerdict(verdict="unknown", list_version=seed["version"])
    return ThreatVerdict(
        verdict="flagged",
        source=hit["source"],
        confidence=hit["confidence"],
        tactic=hit.get("tactic"),
        list_version=seed["version"],
    )


mcp = MCPServer(
    "hoicon-threat",
    instructions="Tra cứu số điện thoại đã băm (h1 = SHA-256 của 'hoicon:v1:' + số E.164) trong danh sách lừa đảo của "
    "HỏiCon. Không bao giờ gửi số điện thoại thô.",
)


@mcp.tool()
def lookup_phone(h1: str) -> ThreatVerdict:
    """Tra một số điện thoại đã băm. Trả `flagged` (kèm nguồn, độ tin cậy, thủ đoạn) hoặc `unknown`."""
    return lookup_h1(h1)
