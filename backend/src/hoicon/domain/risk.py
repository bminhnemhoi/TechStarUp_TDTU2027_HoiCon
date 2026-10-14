"""Mức rủi ro — giá trị khớp `rule_floor` trong docs/schemas/risk_event.v1.json và `RiskLevel` của :rules (Android).

Bất biến (CLAUDE.md luật 5, DATA-MODEL §4): mức của sự cố không bao giờ thấp hơn mức sàn do luật trên máy quyết định;
LLM chỉ được NÂNG.
"""

from enum import StrEnum


class RiskLevel(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return list(RiskLevel).index(self)


def raise_only(floor: RiskLevel, *proposed: RiskLevel | None) -> RiskLevel:
    """Mức cao nhất trong sàn và các đề xuất; đề xuất thấp hơn sàn bị bỏ qua (không bao giờ hạ)."""
    return max((floor, *(p for p in proposed if p is not None)), key=lambda level: level.rank)
