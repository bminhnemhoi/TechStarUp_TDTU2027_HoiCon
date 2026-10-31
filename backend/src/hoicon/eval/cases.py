"""Suite eval + chuyển kịch bản `data/scenarios/*.yaml` thành `RiskEvent` tất định (spec 030, FR-002/FR-003).

Bảng ánh xạ theo ADR-001 + `RiskEngine` v0.1.0-s1 (Android `:rules`):
- R0: số tin cậy ⇒ không sự cố. Không mở app tài chính/app ngoài Play ⇒ không sự cố.
- R1: số lạ/gắn cờ + app ngân hàng/ví/chứng khoán trong cửa sổ cuộc gọi ⇒ `high`;
  `critical` khi số gắn cờ hoặc gọi > 5 phút.
- R2: app ngoài Play sau cuộc gọi lạ ⇒ `critical` (máy CHƯA cài R2 — báo cáo ghi chú).
Tất định: `RiskEvent.id` = UUID5 theo ca, `occurred_at` cố định, h1 từ số HƯ CẤU trong `data/fixtures/phones.json`.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from hoicon.domain.events import RiskEvent
from hoicon.domain.risk import RiskLevel

ROOT = Path(__file__).resolve().parents[4]
EVAL_DIR = ROOT / "backend" / "eval"
SCENARIOS_DIR = ROOT / "data" / "scenarios"
PHONES = ROOT / "data" / "fixtures" / "phones.json"
SMOKE_SUITE = EVAL_DIR / "suites" / "smoke.v1.json"
SUITES = ("smoke", "full", "injection")
# Thư mục cassette theo suite, tra theo thứ tự: full dùng cassette sinh ở `full/` rồi cassette viết tay của smoke (036).
CASSETTE_DIRS = {"smoke": ("smoke",), "full": ("full", "smoke"), "injection": ("full", "smoke")}

OCCURRED_AT = datetime(2026, 10, 15, 9, 0, tzinfo=UTC)
# Thời lượng đại diện cho từng khoảng (giây); `in_call=false` ⇒ cuộc gọi vừa kết thúc cách đây 60 s (trong cửa sổ R1).
DURATION_S = {"lt_1m": 30, "1_5m": 180, "5_15m": 600, "gt_15m": 1200}
SINCE_END_S = 60
FINANCE_APPS = ("bank", "wallet", "securities")
# Tên gói app hư cấu (Android bỏ qua ở backend; dùng để kiểm bộ kiểm không để lộ tên gói, ADR-006).
DEMO_PACKAGES = {
    "bank": "vn.hoicon.demobank",
    "wallet": "vn.hoicon.demowallet",
    "securities": "vn.hoicon.demosecurities",
    "sideloaded": "vn.hoicon.sideloaded.demo",
}
# Câu hỏi của `ask_elder` ⇒ khóa trả lời trong kịch bản.
QUESTION_KEY = {
    "q_caller_authority": "claims_authority",
    "q_asked_transfer": "asks_transfer",
    "q_know_caller": "knows_caller",
}
FLAGGED_H1_KEY, UNKNOWN_KEY = "flagged_caller", "unknown_caller"
# h1 của `flagged_caller` nằm trong danh sách đe dọa demo (data/threat_seed.demo.json) — cùng giá trị `spike.DEMO_H1`.
_E164_PREFIX = "hoicon:v1:"


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    region: str
    channel: str
    is_benign: bool
    injection: bool
    draft: bool
    elder_note: str | None
    elder_answers: dict[str, str]
    signals: dict[str, Any]
    expected: dict[str, Any]


CASE_ID = re.compile(r"[a-z0-9]+(_[a-z0-9]+)*_[0-9]{3}")  # đúng mẫu id của scenario.v1.json


def _checked(case_id: str) -> str:
    """Id đi từ tệp suite vào đường dẫn tệp ⇒ chỉ nhận đúng mẫu hợp đồng (không `..`, không `/`)."""
    if not CASE_ID.fullmatch(case_id):
        raise ValueError(f"id ca không đúng mẫu hợp đồng: {case_id!r}")
    return case_id


def load_case(case_id: str) -> Case:
    case_id = _checked(case_id)
    raw = yaml.safe_load((SCENARIOS_DIR / f"{case_id}.yaml").read_text(encoding="utf-8"))
    return Case(
        id=raw["id"],
        category=raw["category"],
        region=raw["region"],
        channel=raw["channel"],
        is_benign=raw["is_benign"],
        injection=bool(raw.get("injection", False)),
        draft=bool(raw["draft"]),
        elder_note=(raw.get("elder_note") or "").strip() or None,
        elder_answers=dict(raw["elder_answers"]),
        signals=dict(raw["device_signals"]),
        expected=dict(raw["expected"]),
    )


def suite_document(name: str) -> dict[str, Any]:
    """Tệp suite thô. `injection` không có tệp riêng: là các ca `injection: true` của `full` (spec 036, FR-001)."""
    file = "full" if name == "injection" else name
    return json.loads((EVAL_DIR / "suites" / f"{file}.v1.json").read_text(encoding="utf-8"))


def load_suite(name: str = "smoke") -> list[Case]:
    cases = [load_case(case_id) for case_id in suite_document(name)["cases"]]
    return [c for c in cases if c.injection] if name == "injection" else cases


def find_cassette(case_id: str, suite: str) -> Path:
    """Cassette của ca theo thứ tự thư mục của suite; không có ⇒ FileNotFoundError nêu id."""
    case_id = _checked(case_id)
    for directory in CASSETTE_DIRS[suite]:
        path = EVAL_DIR / "cassettes" / directory / f"{case_id}.json"
        if path.is_file():
            return path
    raise FileNotFoundError(case_id)


def plan_trigger(signals: dict[str, Any]) -> tuple[str, RiskLevel] | None:
    """(rule_id, mức sàn) của luật trên máy, hoặc None nếu không có sự cố."""
    if signals["caller_flag"] == "trusted":
        return None
    app = signals["app_category"]
    if app == "sideloaded":
        return "R2", RiskLevel.CRITICAL
    if app not in FINANCE_APPS:
        return None
    long_call = signals["duration_bucket"] in ("5_15m", "gt_15m")
    return "R1", RiskLevel.CRITICAL if signals["caller_flag"] == "flagged" or long_call else RiskLevel.HIGH


def _phone(key: str) -> str:
    return json.loads(PHONES.read_text(encoding="utf-8"))[key]


def _h1(national_number: str) -> tuple[str, str]:
    """(h1, last3) của số quốc nội VN (0xxxxxxxxx ⇒ +84xxxxxxxxx), đúng quy ước ADR-006."""
    e164 = "+84" + national_number[1:]
    return hashlib.sha256((_E164_PREFIX + e164).encode()).hexdigest(), e164[-3:]


def build_event(case: Case) -> RiskEvent | None:
    trigger = plan_trigger(case.signals)
    if trigger is None:
        return None
    rule_id, floor = trigger
    flagged = case.signals["caller_flag"] == "flagged"
    h1, last3 = _h1(_phone(FLAGGED_H1_KEY if flagged else UNKNOWN_KEY))
    in_call = bool(case.signals["in_call"])
    call: dict[str, Any] = {
        "direction": "incoming",
        "active": in_call,
        "duration_s": DURATION_S[case.signals["duration_bucket"]],
    }
    if not in_call:
        call["since_end_s"] = SINCE_END_S
    app = case.signals["app_category"]
    return RiskEvent.model_validate(
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"hoicon:eval:{case.id}")),
            "schema_version": 1,
            "type": "sideload_detected" if rule_id == "R2" else "banking_app_foreground",
            "occurred_at": OCCURRED_AT.isoformat(),
            "rule_id": rule_id,
            "rule_floor": floor.value,
            "is_drill": False,
            "caller": {"h1": h1, "last3": last3, "in_contacts": False, "flagged": flagged},
            "call": call,
            "app": {"category": app, "package": DEMO_PACKAGES[app]},
        }
    )


def _phone_spellings(national: str) -> list[str]:
    """Các cách một số quốc nội có thể lọt vào dữ liệu: quốc nội, E.164, bỏ dấu +, có dấu cách/chấm/gạch."""
    spaced = f"{national[:3]} {national[3:6]} {national[6:]}"
    return [
        national,
        "+84" + national[1:],
        "84" + national[1:],
        spaced,
        spaced.replace(" ", "."),
        spaced.replace(" ", "-"),
    ]


def case_secrets(case: Case) -> list[str]:
    """Chuỗi bí mật đã biết của ca (số điện thoại thô, h1, tên gói app, lời kể): bộ kiểm `leak_pii` tìm chúng trong tin,
    nội dung gửi LLM, `agent_steps` và checkpoint. Chỉ dữ liệu hư cấu (luật 8)."""
    event = build_event(case)
    secrets = [case.elder_note] if case.elder_note else []
    if event is not None:
        flagged = case.signals["caller_flag"] == "flagged"
        secrets += _phone_spellings(_phone(FLAGGED_H1_KEY if flagged else UNKNOWN_KEY))
        secrets += [event.caller.h1, event.app.package]
    return secrets


def elder_reply(case: Case, question_id: str, *, first: bool) -> dict[str, str]:
    """Giá trị `resume` cho `ask_elder`: trả lời theo câu hỏi (thiếu ⇒ `unsure`); lời kể kèm ở lần trả lời đầu."""
    reply = {"answer": case.elder_answers.get(QUESTION_KEY[question_id], "unsure")}
    if first and case.elder_note:
        reply["note"] = case.elder_note
    return reply


def incident_id(nonce: str, case_id: str) -> str:
    """Id sự cố/thread của eval: tiền tố `eval-` + nonce của lượt (`agent_runs.thread_id` và khóa job là UNIQUE)."""
    return f"eval-{nonce}-{case_id}"
