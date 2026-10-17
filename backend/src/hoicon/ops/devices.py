"""Lệnh vận hành thiết bị (spec 034 FR-007, mục #9 của 020):

    uv run --directory backend python -m hoicon.ops.devices revoke --device <id> [--confirm]

Thu hồi một máy bị mất hoặc bán lại: đặt `devices.revoked_at`. `get_current_device` kiểm cột này ở MỌI yêu cầu nên
token cũ bị từ chối ngay (401), không chờ hết hạn. Lũy đẳng. Ngoài dev/test/ci cần `--confirm`. Chỉ in id và kết quả.
"""

import argparse
import asyncio
import sys
from uuid import UUID

from sqlalchemy import func, update

from hoicon.config import get_settings
from hoicon.db.models import Device
from hoicon.db.session import get_sessionmaker


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("cần một UUID") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    revoke = sub.add_parser("revoke", help="thu hồi một thiết bị")
    revoke.add_argument("--device", required=True, type=_uuid)
    revoke.add_argument("--confirm", action="store_true", help="bắt buộc ngoài dev/test/ci")
    return parser


async def revoke(device_id: UUID) -> str:
    """⇒ "revoked" (vừa thu hồi), "already" (đã thu hồi từ trước), "missing" (không có thiết bị này)."""
    async with get_sessionmaker().begin() as session:
        done = await session.execute(
            update(Device).where(Device.id == device_id, Device.revoked_at.is_(None)).values(revoked_at=func.now())
        )
        if done.rowcount:
            return "revoked"
        exists = await session.get(Device, device_id)
        return "already" if exists is not None else "missing"


async def execute(args: argparse.Namespace) -> int:
    if not get_settings().is_dev_env and not args.confirm:
        print("Từ chối: ngoài dev/test/ci lệnh này cần thêm --confirm.")
        return 2
    outcome = await revoke(args.device)
    messages = {
        "revoked": f"Đã thu hồi thiết bị {args.device}. Token cũ bị từ chối từ yêu cầu kế tiếp.",
        "already": f"Thiết bị {args.device} đã được thu hồi từ trước.",
        "missing": f"Không thấy thiết bị {args.device}.",
    }
    print(messages[outcome])
    return 2 if outcome == "missing" else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(execute(args), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
