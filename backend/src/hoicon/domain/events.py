"""RiskEvent v1 — hợp đồng `docs/schemas/risk_event.v1.json` (test `tests/contract/test_risk_event_model.py` giữ enum
khớp schema). Chỉ siêu dữ liệu: số gọi đến chỉ có h1 + 3 số cuối (ADR-006), không có nội dung cuộc gọi."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hoicon.domain.risk import RiskLevel

EventType = Literal[
    "call_started",
    "call_ended",
    "flagged_number_call",
    "risk_window_opened",
    "risk_window_closed",
    "banking_app_foreground",
    "sideload_detected",
    "safe_pause_shown",
    "safe_pause_continued",
    "safe_pause_cancelled",
    "ask_child_pressed",
]
RuleId = Literal["R0", "R1", "R2", "R4"]
AppCategory = Literal["bank", "wallet", "securities", "sideloaded", "other"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Caller(_Strict):
    h1: str = Field(pattern=r"^[0-9a-f]{64}$")
    last3: str = Field(pattern=r"^[0-9]{3}$")
    in_contacts: bool
    trusted: bool = False
    flagged: bool = False


class Call(_Strict):
    direction: Literal["incoming", "outgoing"] | None = None
    active: bool | None = None
    duration_s: int | None = Field(default=None, ge=0)
    since_end_s: int | None = Field(default=None, ge=0)


class App(_Strict):
    category: AppCategory
    package: str | None = Field(default=None, max_length=128)


class RiskEvent(BaseModel):
    """Phần của RiskEvent mà đồ thị dùng; các trường khác của schema (timing, device…) được bỏ qua ở đây."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: uuid.UUID
    schema_version: Literal[1]
    type: EventType
    occurred_at: datetime
    rule_id: RuleId | None = None
    rule_floor: RiskLevel
    is_drill: bool
    caller: Caller | None = None
    call: Call | None = None
    app: App | None = None
