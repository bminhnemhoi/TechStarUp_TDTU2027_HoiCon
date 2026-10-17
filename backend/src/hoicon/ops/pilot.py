"""Lệnh vận hành thí điểm (spec 029 FR-004, plan D2/D4):

    uv run --directory backend python -m hoicon.ops.pilot enroll --family <id> --confirm-adult
    uv run --directory backend python -m hoicon.ops.pilot report [--days 7] [--json]
    uv run --directory backend python -m hoicon.ops.pilot gate-m2 [--days 7] [--crash-free 99.5 --crash-source "..."]
                                                                 [--real-devices 1] [--no-high-findings]

`enroll` đặt `families.plan = 'pilot'`; BẮT BUỘC `--confirm-adult` (luật 8: thí điểm chỉ người ≥ 18 tuổi; không lưu
ngày sinh) và từ chối gia đình demo (dữ liệu `is_demo` không trộn với thí điểm). `report` tính độ phủ heartbeat = số
khung 15 phút có heartbeat ÷ số khung kỳ vọng, theo từng thiết bị, từ `max(created_at, đầu kỳ)` tới
`min(revoked_at, nay)` (thiết bị ghép giữa kỳ hoặc đã thu hồi có mẫu số riêng). `gate-m2` in ĐẠT/TRƯỢT từng chỉ tiêu;
chỉ tiêu do người nhập (crash-free từ Play vitals, số máy thật, kết quả 034) được đánh dấu NHẬP TAY; thiếu số thì
KHÔNG tính là đạt.

Không in PII: gia đình chỉ có bí danh gia đình, thiết bị chỉ có 8 ký tự đầu của id; không tên thành viên, HMAC hay số.
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.db.models import Device, DeviceHeartbeat, Family, Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services.heartbeat_service import CORE_PERMISSIONS, SLOT_SECONDS

PILOT = "pilot"
MAX_DAYS = 90
MIN_FAMILIES = 5  # Gate M2
MIN_COVERAGE = 0.90
MIN_CRASH_FREE = 99.0
OK, FAIL, MISSING = "ĐẠT", "TRƯỢT", "CHƯA CÓ SỐ"


class EnrollError(Exception):
    """Từ chối ghi danh (thông điệp hiển thị cho người vận hành, không chứa dữ liệu cá nhân)."""


async def enroll(sessions: async_sessionmaker, family_id: UUID, *, confirm_adult: bool) -> str:
    """⇒ "enrolled" hoặc "already" (lũy đẳng)."""
    if not confirm_adult:
        raise EnrollError("Từ chối: cần --confirm-adult (xác nhận người cao tuổi từ 18 tuổi trở lên).")
    async with sessions.begin() as session:
        family = await session.get(Family, family_id)
        if family is None or family.deleted_at is not None:
            raise EnrollError("Từ chối: không thấy gia đình này.")
        if family.is_demo:
            raise EnrollError("Từ chối: gia đình demo không được ghi danh thí điểm.")
        if family.plan == PILOT:
            return "already"
        await session.execute(update(Family).where(Family.id == family_id).values(plan=PILOT))
        return "enrolled"


def _ceil_slot(moment: datetime) -> int:
    return -(-int(moment.timestamp()) // SLOT_SECONDS)


def _floor_slot(moment: datetime) -> int:
    return int(moment.timestamp()) // SLOT_SECONDS


def _at(slot_index: int) -> datetime:
    return datetime.fromtimestamp(slot_index * SLOT_SECONDS, tz=UTC)


async def _device_report(session: Any, device: Device, since: datetime, now: datetime) -> dict[str, Any]:
    first = _ceil_slot(max(device.created_at, since))
    last = _floor_slot(min(device.revoked_at or now, now))  # khung kỳ vọng: [first, last)
    expected = max(0, last - first)
    seen = protected = 0
    if expected:
        seen, protected = (
            await session.execute(
                select(func.count(), func.count().filter(DeviceHeartbeat.protected)).where(
                    DeviceHeartbeat.device_id == device.id,
                    DeviceHeartbeat.slot >= _at(first),
                    DeviceHeartbeat.slot < _at(last),
                )
            )
        ).one()
    state = device.permission_state or {}
    off = sorted({name for name in (*state, *CORE_PERMISSIONS) if state.get(name) is not True})
    return {
        "device": str(device.id)[:8],
        "coverage": round(seen / expected, 4) if expected else None,
        "protected_ratio": round(protected / seen, 4) if seen else None,
        "last_heartbeat_at": device.last_heartbeat_at.isoformat(),
        "app_version": device.app_version,
        "revoked": device.revoked_at is not None,
        "permissions_off": off,
        "slots_expected": expected,
        "slots_seen": seen,
    }


async def build_report(sessions: async_sessionmaker, days: int, *, now: datetime | None = None) -> dict[str, Any]:
    """Báo cáo khớp `docs/schemas/pilot_report.v1.json`."""
    moment = now or datetime.now(UTC)
    since = moment - timedelta(days=days)
    families: list[dict[str, Any]] = []
    async with sessions() as session:
        rows = (
            await session.scalars(
                select(Family)
                .where(Family.plan == PILOT, Family.is_demo.is_(False), Family.deleted_at.is_(None))
                .order_by(Family.created_at, Family.id)
            )
        ).all()
        for family in rows:
            devices = (
                await session.scalars(
                    select(Device)
                    .where(Device.family_id == family.id, (Device.revoked_at.is_(None)) | (Device.revoked_at >= since))
                    .order_by(Device.created_at, Device.id)
                )
            ).all()
            incidents, false_alarms = (  # sự cố THẬT: không diễn tập, không demo
                await session.execute(
                    select(func.count(), func.count().filter(Incident.state == "resolved_false_alarm")).where(
                        Incident.family_id == family.id,
                        Incident.opened_at >= since,
                        Incident.is_drill.is_(False),
                        Incident.is_demo.is_(False),
                    )
                )
            ).one()
            families.append(
                {
                    "alias": family.display_name,
                    "incidents": incidents,
                    "false_alarms": false_alarms,
                    "devices": [await _device_report(session, d, since, moment) for d in devices],
                }
            )
    return {"generated_at": moment.isoformat(), "days": days, "families": families}


def pooled_coverage(report: dict[str, Any]) -> tuple[float | None, float | None]:
    """⇒ (độ phủ gộp mọi thiết bị, độ phủ thấp nhất của một thiết bị); None nếu chưa có khung kỳ vọng nào."""
    devices = [d for f in report["families"] for d in f["devices"] if d["slots_expected"]]
    expected = sum(d["slots_expected"] for d in devices)
    if not expected:
        return None, None
    return sum(d["slots_seen"] for d in devices) / expected, min(d["coverage"] for d in devices)


@dataclass(frozen=True)
class Criterion:
    name: str
    status: str
    detail: str
    manual: bool  # True = số do người nhập, không tự đo


def evaluate_gate(
    report: dict[str, Any],
    *,
    crash_free: float | None,
    crash_source: str | None,
    real_devices: int | None,
    no_high_findings: bool,
) -> list[Criterion]:
    families = len(report["families"])
    pooled, worst = pooled_coverage(report)
    if pooled is None:
        coverage = Criterion("Độ phủ heartbeat ≥ 90%", MISSING, "chưa có khung kỳ vọng nào (chưa có thiết bị)", False)
    else:
        verdict = OK if pooled >= MIN_COVERAGE else FAIL
        detail = f"gộp {pooled:.1%}; thiết bị thấp nhất {worst:.1%}; {report['days']} ngày"
        coverage = Criterion("Độ phủ heartbeat ≥ 90%", verdict, detail, False)
    if crash_free is None or not crash_source:
        crash = Criterion("Crash-free ≥ 99%", MISSING, "cần --crash-free và --crash-source (Play vitals, n=…)", True)
    else:
        verdict = OK if crash_free >= MIN_CRASH_FREE else FAIL
        crash = Criterion("Crash-free ≥ 99%", verdict, f"{crash_free:g}% · nguồn: {crash_source}", True)
    if real_devices is None:
        real = Criterion("≥ 1 máy thật", MISSING, "cần --real-devices <số>", True)
    else:
        real = Criterion("≥ 1 máy thật", OK if real_devices >= 1 else FAIL, f"{real_devices} máy", True)
    high = Criterion(
        "Không còn finding High (034)",
        OK if no_high_findings else MISSING,
        "người vận hành xác nhận từ báo cáo review" if no_high_findings else "cần --no-high-findings sau khi đối chiếu",
        True,
    )
    enrolled = Criterion(
        f"≥ {MIN_FAMILIES} gia đình ghi danh thí điểm",
        OK if families >= MIN_FAMILIES else FAIL,
        f"{families} gia đình",
        False,
    )
    return [enrolled, real, coverage, crash, high]


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("cần một UUID") from None


def _days(value: str) -> int:
    number = int(value)
    if not 1 <= number <= MAX_DAYS:
        raise argparse.ArgumentTypeError(f"cần từ 1 đến {MAX_DAYS}")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    enroll_p = sub.add_parser("enroll", help="ghi danh một gia đình vào thí điểm (plan=pilot)")
    enroll_p.add_argument("--family", required=True, type=_uuid)
    enroll_p.add_argument("--confirm-adult", action="store_true", help="xác nhận người cao tuổi từ 18 tuổi (bắt buộc)")
    report_p = sub.add_parser("report", help="độ phủ heartbeat, quyền tắt, sự cố/báo nhầm theo gia đình")
    report_p.add_argument("--days", type=_days, default=7)
    report_p.add_argument("--json", action="store_true", help="in JSON khớp pilot_report.v1")
    gate = sub.add_parser("gate-m2", help="đánh giá các chỉ tiêu Gate M2")
    gate.add_argument("--days", type=_days, default=7)
    gate.add_argument("--crash-free", type=float, help="% từ Play vitals (NHẬP TAY)")
    gate.add_argument("--crash-source", help='nguồn và cỡ mẫu, ví dụ "Play vitals, n=212"')
    gate.add_argument("--real-devices", type=int, help="số máy thật đang thí điểm (NHẬP TAY)")
    gate.add_argument(
        "--no-high-findings", action="store_true", help="đã đối chiếu: 034 không còn finding High (NHẬP TAY)"
    )
    return parser


def _percent(value: float | None) -> str:
    return "-" if value is None else f"{value:.0%}"


def render(report: dict[str, Any]) -> str:
    lines = [f"Báo cáo thí điểm {report['days']} ngày · {len(report['families'])} gia đình"]
    for family in report["families"]:
        lines.append(f"- {family['alias']}: {family['incidents']} sự cố, {family['false_alarms']} báo nhầm")
        for d in family["devices"]:
            off = ", ".join(d["permissions_off"]) or "không"
            state = " (đã thu hồi)" if d["revoked"] else ""
            lines.append(
                f"    máy {d['device']}{state}: độ phủ {_percent(d['coverage'])}"
                f" ({d['slots_seen']}/{d['slots_expected']} khung), bảo vệ đủ {_percent(d['protected_ratio'])},"
                f" bản {d['app_version']}, quyền tắt: {off}"
            )
    return "\n".join(lines)


async def execute(args: argparse.Namespace) -> int:
    sessions = get_sessionmaker()
    if args.command == "enroll":
        try:
            result = await enroll(sessions, args.family, confirm_adult=args.confirm_adult)
        except EnrollError as exc:
            print(exc)
            return 2
        print("Đã ghi danh thí điểm." if result == "enrolled" else "Gia đình này đã ghi danh từ trước.")
        return 0
    report = await build_report(sessions, args.days)
    if args.command == "report":
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render(report))
        return 0
    criteria = evaluate_gate(
        report,
        crash_free=args.crash_free,
        crash_source=args.crash_source,
        real_devices=args.real_devices,
        no_high_findings=args.no_high_findings,
    )
    print(f"Gate M2 · {args.days} ngày")
    for c in criteria:
        print(f"  [{c.status}] {c.name}: {c.detail}" + ("  (NHẬP TAY)" if c.manual else ""))
    passed = all(c.status == OK for c in criteria)
    print("KẾT LUẬN: " + ("ĐẠT" if passed else "CHƯA ĐẠT"))
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(execute(args), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
