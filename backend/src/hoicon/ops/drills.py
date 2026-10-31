"""Lệnh vận hành diễn tập cho đội thí điểm (spec 028 FR-007, PILOT-PROTOCOL):

    uv run --directory backend python -m hoicon.ops.drills schedule \
        --family <id> --at <ISO|now> --minutes 30 --script <id>
    uv run --directory backend python -m hoicon.ops.drills list --family <id>
    uv run --directory backend python -m hoicon.ops.drills cancel --family <id> --drill <id>

Dùng chung `DrillService.schedule`, nên giữ đủ luật: người cao tuổi đã đồng ý `drills`, tối đa 2 bài/tháng/gia đình,
khung 30 phút–4 giờ ở tương lai, kịch bản đã duyệt (bản không phải dev). Ngoài dev/test/ci, lệnh ghi cần `--confirm`.
Chỉ in id, trạng thái, mốc giờ và id kịch bản: không xưng hô, không tên, không số điện thoại.
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from hoicon.config import DEV_ENVS, get_settings
from hoicon.db.models import Drill, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services.drill_service import (
    MAX_WINDOW,
    MIN_WINDOW,
    DrillNotFound,
    DrillRefused,
    DrillService,
    InvalidDrillTransition,
)

REFUSALS = {
    "script_unknown": "kịch bản không tồn tại trong data/drills",
    "script_not_approved": "kịch bản chưa được Minh duyệt (bản không phải dev chỉ chạy bài đã duyệt)",
    "window_invalid": "khung giờ không hợp lệ (cần múi giờ, kết thúc sau bắt đầu)",
    "window_past": "khung giờ đã qua",
    "window_too_short": "khung giờ ngắn hơn 30 phút",
    "window_too_long": "khung giờ dài hơn 4 giờ",
    "member_not_found": "không thấy người cao tuổi này trong gia đình",
    "consent_missing": "người cao tuổi chưa đồng ý (hoặc đã rút) mục đích drills",
    "window_overlaps": "trùng khung giờ với một bài khác của người này",
    "monthly_limit": "gia đình đã đủ 2 bài trong tháng",
}


def _needs_confirm(args: argparse.Namespace) -> bool:
    return get_settings().env not in DEV_ENVS and not args.confirm


def _moment(value: str) -> datetime:
    if value == "now":
        return datetime.now(UTC)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "--at là 'now' hoặc thời điểm ISO có múi giờ, ví dụ 2026-10-20T09:00:00+07:00"
        ) from None
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--at cần múi giờ, ví dụ +07:00")
    return parsed


def _minutes(value: str) -> int:
    try:
        minutes = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--minutes là số nguyên") from None
    if not MIN_WINDOW <= timedelta(minutes=minutes) <= MAX_WINDOW:
        raise argparse.ArgumentTypeError("--minutes trong khoảng 30–240")
    return minutes


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("cần một UUID") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    schedule = sub.add_parser("schedule", help="đặt lịch một bài cho người cao tuổi")
    schedule.add_argument("--family", required=True, type=_uuid)
    schedule.add_argument("--member", type=_uuid, help="người cao tuổi; bỏ qua nếu gia đình chỉ có một người")
    schedule.add_argument("--at", required=True, type=_moment, help="'now' hoặc thời điểm ISO có múi giờ")
    schedule.add_argument("--minutes", required=True, type=_minutes, help="độ dài khung giờ, 30–240")
    schedule.add_argument("--script", required=True, help="id kịch bản trong data/drills")
    schedule.add_argument("--confirm", action="store_true", help="bắt buộc ngoài dev/test/ci")
    listing = sub.add_parser("list", help="liệt kê các bài của gia đình")
    listing.add_argument("--family", required=True, type=_uuid)
    cancel = sub.add_parser("cancel", help="hủy một bài chưa bắt đầu")
    cancel.add_argument("--family", required=True, type=_uuid)
    cancel.add_argument("--drill", required=True, type=_uuid)
    cancel.add_argument("--confirm", action="store_true", help="bắt buộc ngoài dev/test/ci")
    return parser


def _line(drill: Drill) -> str:
    return (
        f"{drill.id} · {drill.status} · {drill.window_start.isoformat()} → {drill.window_end.isoformat()}"
        f" · {drill.script_id}"
    )


async def execute(args: argparse.Namespace) -> int:
    sessions = get_sessionmaker()
    if args.command == "list":
        async with sessions() as session:
            drills = await DrillService.list_for_family(session, args.family)
        for drill in drills:
            print(_line(drill))
        print(f"Tổng: {len(drills)} bài")
        return 0
    if _needs_confirm(args):
        print("Từ chối: ngoài dev/test/ci lệnh ghi cần thêm --confirm.")
        return 2
    try:
        async with sessions.begin() as session:
            if args.command == "cancel":
                drill = await DrillService.cancel(session, family_id=args.family, drill_id=args.drill)
                print(f"Đã hủy: {_line(drill)}")
                return 0
            member_id = args.member or await _only_elder(session, args.family)
            if member_id is None:
                print("Từ chối: gia đình không có đúng một người cao tuổi — chỉ rõ bằng --member.")
                return 2
            drill = await DrillService.schedule(
                session,
                family_id=args.family,
                member_id=member_id,
                window_start=args.at,
                window_end=args.at + timedelta(minutes=args.minutes),
                script_id=args.script,
                by="ops",
            )
            print(f"Đã đặt lịch: {_line(drill)}")
            return 0
    except DrillRefused as refused:
        print(f"Từ chối ({refused.code}): {REFUSALS.get(refused.code, refused.code)}")
        return 2
    except DrillNotFound:
        print("Từ chối: không thấy bài này trong gia đình.")
        return 2
    except InvalidDrillTransition as exc:
        print(f"Từ chối: {exc}")
        return 2


async def _only_elder(session, family_id: UUID) -> UUID | None:
    ids = list(
        await session.scalars(select(Member.id).where(Member.family_id == family_id, Member.role == "protected"))
    )
    return ids[0] if len(ids) == 1 else None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(execute(args), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
