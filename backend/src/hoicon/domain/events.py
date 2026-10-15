"""RiskEvent v1 — hợp đồng `docs/schemas/risk_event.v1.json` (test `tests/contract/test_risk_event_model.py` giữ enum
khớp schema). Chỉ siêu dữ liệu: số gọi đến chỉ có h1 + 3 số cuối (ADR-006), không có nội dung cuộc gọi."""

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, model_validator

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


MAX_DURATION_S = 86_400  # 1 ngày; cột là INTEGER nên phải có cận trên, nếu không số lớn ⇒ DataError ⇒ 500 cả lô
MAX_TIMING_MS = 3_600_000  # 1 giờ
MAX_DIGITS = 8  # tổng chữ số của cả chuỗi: đủ cho "rules-2026.12.01", không đủ cho số điện thoại (≥ 9) hay CCCD (12)
_BUILD_DATE = re.compile(r"[-+]20\d{6}")  # ngoại lệ duy nhất: hậu tố ngày build "-20261016" (không tính vào tổng)


def _digits(value: str) -> int:
    return sum(ch.isdigit() for ch in value)  # tính cả chữ số Unicode


def _package_ok(value: str) -> str:
    """Chuỗi tự do (gói app) không được chứa nhiều chữ số: lưới an toàn khi app lỗi/bị chiếm gửi số điện thoại."""
    if _digits(value) > MAX_DIGITS:
        raise ValueError("giá trị không hợp lệ")
    return value


def _version_ok(value: str) -> str:
    """Tổng chữ số ≤ 8 (không tính hậu tố ngày build): số điện thoại chia đôi qua hai phần cũng không lọt."""
    counted = _BUILD_DATE.sub("", value, count=1)
    if _digits(counted) > MAX_DIGITS:
        raise ValueError("giá trị không hợp lệ")
    return value


PackageName = Annotated[
    str,
    Field(max_length=128, pattern=r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$"),
    AfterValidator(_package_ok),
]
# "0.1.0", "r1", "rules-2026.12.01", "0.1.0-20261016": số đầu ≤ 4 chữ số nên mã OTP/số điện thoại trần không lọt vào;
# mã ngắn kiểu "123.456" thì không phân biệt được với một phiên bản (giới hạn đã biết).
VersionName = Annotated[
    str,
    Field(max_length=32, pattern=r"^[A-Za-z]{0,16}[-_]?\d{1,4}(?:\.\d{1,4}){0,3}(?:[-+][0-9A-Za-z.]{1,16})?$"),
    AfterValidator(_version_ok),
]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Caller(_Strict):
    h1: str = Field(pattern=r"^[0-9a-f]{64}$", repr=False)  # không bao giờ lộ qua repr/log
    last3: str = Field(pattern=r"^[0-9]{3}$")
    in_contacts: StrictBool
    trusted: StrictBool = False
    flagged: StrictBool = False


class Call(_Strict):
    direction: Literal["incoming", "outgoing"] | None = None
    active: StrictBool | None = None
    duration_s: int | None = Field(default=None, ge=0, le=MAX_DURATION_S)
    since_end_s: int | None = Field(default=None, ge=0, le=MAX_DURATION_S)


class App(_Strict):
    category: AppCategory
    package: PackageName | None = None


class RiskEvent(BaseModel):
    """Phần của RiskEvent mà đồ thị dùng; các trường khác của schema (timing, device…) được bỏ qua ở đây."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: uuid.UUID
    schema_version: Literal[1]
    type: EventType
    occurred_at: datetime
    rule_id: RuleId | None = None
    rule_floor: RiskLevel
    is_drill: StrictBool
    drill_id: uuid.UUID | None = None
    caller: Caller | None = None
    call: Call | None = None
    app: App | None = None


class Timing(_Strict):
    detect_ms: int | None = Field(default=None, ge=0, le=MAX_TIMING_MS)
    pause_ms: int | None = Field(default=None, ge=0, le=MAX_TIMING_MS)


class RiskEventIn(RiskEvent):
    """Sự kiện NHẬN từ thiết bị (`POST /v1/events`): khớp CHẶT `risk_event.v1.json` (`additionalProperties: false`) —
    trường lạ (kể cả số điện thoại thô) làm hỏng cả lô, không bị lẳng lặng bỏ qua."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    occurred_at: AwareDatetime  # schema `date-time` luôn có múi giờ
    timing: Timing | None = None
    app_version: VersionName
    rules_version: VersionName

    @model_validator(mode="after")
    def _drill_needs_id(self) -> "RiskEventIn":
        if self.is_drill and self.drill_id is None:
            raise ValueError("diễn tập cần drill_id")
        return self
