"""Báo cáo quyền riêng tư cuối (spec 037 FR-006): dữ liệu ↔ mục đích ↔ hạn lưu, số điện thoại thô, văn bản đồng ý,
PII trong kho.

    uv run --directory backend python -m hoicon.ops.privacy_report [--json] [--no-db] [--strict-db]

Thoát 0 khi: (a) MỌI bảng của model có dòng trong `DATA_MAP` (bảng mới mà quên ánh xạ ⇒ thoát 1), (b) `backend/src` và
`apps/web/src` không có số điện thoại ngoài dải hư cấu, (c) `consent_texts` khớp mã. Chỉ ĐẾM và in
đường dẫn:dòng, KHÔNG bao giờ in số, tên hay nội dung dòng dữ liệu. Hạn lưu của các loại có trong `RETENTION`
lấy thẳng từ đó (không chép tay)."""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import text

from hoicon.db.models import Base
from hoicon.db.session import get_sessionmaker
from hoicon.ops import consent_texts
from hoicon.services.retention_service import RETENTION

ROOT = Path(__file__).resolve().parents[4]
# Số di động Việt Nam; không khớp khi nằm giữa dãy chữ/số/gạch (URL, id) để khỏi báo nhầm.
PHONE = re.compile(r"(?<![\w.-])(?:\+84|0)(?:3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])\d{7}(?!\d)")
SPACED_DIGITS = re.compile(r"(?<=\d)[ .](?=\d)")
FICTIONAL = re.compile(r"^(?:\+84|0)900000\d{3}$")  # dải hư cấu 0900000xxx (CLAUDE.md luật 2)
SOURCE_ROOTS = (
    "backend/src",
    "apps/web/src",
    *(f"apps/android/{m}/src/main" for m in ("app", "rules", "demobank", "latency", "voicelab")),
)
FIXTURE_ROOTS = ("backend/tests", "data", "docs/schemas")
# Fixture CỐ Ý chứa số trông như thật để kiểm tra việc TỪ CHỐI PII (hợp đồng "invalid"): không tính là rò rỉ.
NEGATIVE_FIXTURES = (
    "docs/schemas/fixtures/risk_event.v1.invalid.json",
    "backend/tests/integration/test_api_events.py",  # bảng ca từ chối số điện thoại trong phiên bản/gói
)
SCANNED = {".py", ".ts", ".tsx", ".json", ".md", ".yaml", ".yml", ".sql", ".kt", ".html", ".css", ".js", ".mjs"}
SQL_PHONE = r"(^|[^A-Za-z0-9._-])(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}([^0-9]|$)"

# Mỗi bảng: (mục đích, khóa trong RETENTION hoặc mô tả hạn lưu cố định, dữ liệu cá nhân trong bảng).
DATA_MAP: dict[str, tuple[str, str, str]] = {
    "action_tokens": ("liên kết hành động dùng một lần cho người giám hộ", "action_tokens", "chỉ SHA-256 của token"),
    "agent_runs": ("trace lượt chạy tác tử", "theo sự cố (CASCADE)", "không có PII"),
    "agent_steps": ("trace từng bước (đã che)", "agent_steps_content", "nội dung đã che PII; số đo giữ lại"),
    "case_files": ("hồ sơ vụ việc cho người giám hộ", "theo sự cố (CASCADE)", "tóm tắt đã che, 3 số cuối, bí danh"),
    "consents": ("sổ đồng ý chỉ ghi thêm", "không xóa (bằng chứng, Nghị định 356/2025)", "không có PII"),
    "data_requests": ("vết yêu cầu xóa dữ liệu", "giữ (vết pháp lý)", "không có văn bản tự do"),
    "device_heartbeats": ("đo độ phủ bảo vệ", "device_heartbeats", "không có PII"),
    "devices": ("thiết bị đã ghép đôi", "đến khi xóa gia đình (ẩn danh)", "băm bí mật thiết bị, nhãn đã che"),
    "drills": ("bài diễn tập nhận biết lừa đảo", "drills", "không có PII (kịch bản hư cấu)"),
    "families": ("gia đình", "đến khi xóa gia đình (ẩn danh)", "tên hiển thị do người dùng đặt"),
    "incident_transitions": ("nhật ký chuyển trạng thái sự cố", "theo sự cố (CASCADE)", "không có PII"),
    "incidents": ("sự cố đang/đã xử lý", "incidents", "không có PII (mức, trạng thái, id)"),
    "jobs": ("hàng đợi job (gồm toàn văn tin gửi người giám hộ)", "jobs", "văn bản đã che; không số/tên thô"),
    "members": ("thành viên gia đình", "đến khi xóa gia đình (ẩn danh)", "bí danh, HMAC Zalo, chat id mã hóa"),
    "messages_out": ("đếm hạn mức Zalo theo tháng", "giữ dòng, không có cột văn bản", "id kênh (không số điện thoại)"),
    "pairing_codes": ("mã ghép đôi dùng một lần", "15 phút / dùng một lần", "chỉ HMAC của mã"),
    "revoked_sessions": (
        "thu hồi phiên web người giám hộ đã đăng xuất",
        "tới khi token hết hạn (≤ 7 ngày)",
        "chỉ mã phiên ngẫu nhiên, không PII",
    ),
    "risk_events": ("sự kiện rủi ro từ thiết bị", "risk_events", "HMAC + 3 số cuối của số gọi, không số thô"),
    "threat_indicators": ("danh sách số/đường dẫn lừa đảo", "theo phiên bản danh sách", "chỉ HMAC + 3 số cuối"),
    "trusted_contacts": ("liên hệ tin cậy (không cảnh báo)", "đến khi xóa gia đình (ẩn danh)", "chỉ HMAC + 3 số cuối"),
    "verifications": ("kết quả tra cứu số/đường dẫn", "verifications", "chỉ HMAC + 3 số cuối"),
}


def _retention(value: str) -> str:
    if value in RETENTION:
        days = RETENTION[value].days
        return f"{days} ngày"
    return value


def inventory() -> tuple[list[dict[str, str]], list[str]]:
    """⇒ (các dòng bảng dữ liệu, tên bảng của model mà DATA_MAP chưa có / DATA_MAP có mà model không còn)."""
    tables = sorted(Base.metadata.tables)
    rows = [
        {"table": t, "purpose": DATA_MAP[t][0], "retention": _retention(DATA_MAP[t][1]), "personal": DATA_MAP[t][2]}
        for t in tables
        if t in DATA_MAP
    ]
    problems = [f"{t}: bảng chưa có trong DATA_MAP" for t in tables if t not in DATA_MAP]
    problems += [f"{t}: có trong DATA_MAP nhưng không còn trong model" for t in sorted(DATA_MAP) if t not in tables]
    return rows, problems


def scan_phones(roots: tuple[str, ...] = SOURCE_ROOTS, base: Path = ROOT) -> list[str]:
    """Số điện thoại NGOÀI dải hư cấu trong mã nguồn: trả `đường-dẫn:dòng` (không bao giờ trả số)."""
    hits: list[str] = []
    for root in roots:
        if not (base / root).is_dir():
            hits.append(f"{root}: không tìm thấy thư mục, chưa quét được")  # thiếu cây nguồn ⇒ không được báo sạch giả
            continue
        for path in sorted((base / root).rglob("*")):
            if (
                not path.is_file()
                or path.suffix not in SCANNED
                or "node_modules" in path.parts
                or ".next" in path.parts
            ):
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                line = SPACED_DIGITS.sub("", line)  # số viết cách bằng dấu cách hoặc dấu chấm vẫn là số điện thoại
                if any(not FICTIONAL.match(m.group(0)) for m in PHONE.finditer(line)):
                    hits.append(f"{path.relative_to(base)}:{number}")
    return hits


async def count_pii_rows(sessions: Any) -> dict[str, int]:
    """Số dòng nghi chứa số điện thoại ngoài dải hư cấu trong kho (chỉ đếm)."""
    queries = {
        "jobs.payload": "select count(*) from jobs where payload::text ~ :re",
        "agent_steps.output": "select count(*) from agent_steps where output::text ~ :re",
        "agent_steps.input_redacted": "select count(*) from agent_steps where input_redacted::text ~ :re",
    }
    out: dict[str, int] = {}
    async with sessions() as session:
        for name, sql in queries.items():
            raw = await session.scalar(text(sql), {"re": SQL_PHONE})
            out[name] = int(raw or 0)
    return out


async def build_report(*, with_db: bool = True) -> dict[str, Any]:
    rows, table_problems = inventory()
    report: dict[str, Any] = {
        "tables": rows,
        "table_problems": table_problems,
        "raw_phone_hits": scan_phones(),
        "fixture_phone_hits": [h for h in scan_phones(FIXTURE_ROOTS) if h.split(":")[0] not in NEGATIVE_FIXTURES],
        "consent_text_problems": consent_texts.problems(),
        "pii_rows": None,
    }
    if with_db:
        try:
            report["pii_rows"] = await count_pii_rows(get_sessionmaker())
        except Exception as exc:  # không có DB: bỏ qua mục này, ghi rõ (không tính là sạch)
            report["pii_rows"] = f"không đọc được ({type(exc).__name__})"
    return report


def exit_code(report: dict[str, Any], *, strict_db: bool = False) -> int:
    bad = (
        report["table_problems"]
        or report["raw_phone_hits"]
        or report["fixture_phone_hits"]
        or report["consent_text_problems"]
    )
    if strict_db and isinstance(report["pii_rows"], dict) and any(report["pii_rows"].values()):
        bad = True
    return 1 if bad else 0


def render(report: dict[str, Any]) -> str:
    lines = ["Báo cáo quyền riêng tư", "", "Dữ liệu ↔ mục đích ↔ hạn lưu"]
    for r in report["tables"]:
        lines.append(f"- {r['table']}: {r['purpose']} · hạn: {r['retention']} · cá nhân: {r['personal']}")
    lines += ["", f"Bảng chưa ánh xạ: {len(report['table_problems'])}"]
    lines += [f"  ✕ {p}" for p in report["table_problems"]]
    hits = report["raw_phone_hits"]
    lines.append(f"Số điện thoại ngoài dải hư cấu trong mã nguồn: {len(hits)}")
    lines += [f"  ✕ {h}" for h in hits]
    fixtures = report["fixture_phone_hits"]
    lines.append(f"Số điện thoại ngoài dải hư cấu trong fixture (không tính fixture 'invalid' cố ý): {len(fixtures)}")
    lines += [f"  ✕ {h}" for h in fixtures]
    problems = report["consent_text_problems"]
    lines.append(f"Văn bản đồng ý ↔ mã: {'khớp' if not problems else str(len(problems)) + ' vấn đề'}")
    lines += [f"  ✕ {p}" for p in problems]
    pii = report["pii_rows"]
    lines.append(
        "Dòng nghi PII trong kho (chỉ đếm): " + (json.dumps(pii) if isinstance(pii, dict) else str(pii or "bỏ qua"))
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true", help="in JSON")
    parser.add_argument("--no-db", action="store_true", help="không đếm PII trong kho")
    parser.add_argument("--strict-db", action="store_true", help="dòng nghi PII trong kho > 0 ⇒ thoát 1")
    args = parser.parse_args(argv)
    report = asyncio.run(build_report(with_db=not args.no_db), loop_factory=asyncio.SelectorEventLoop)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
    return exit_code(report, strict_db=args.strict_db)


if __name__ == "__main__":
    sys.exit(main())
