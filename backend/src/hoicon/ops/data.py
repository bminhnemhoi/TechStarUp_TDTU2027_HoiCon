"""Lệnh vận hành dữ liệu (spec 034): hạn lưu và xóa dữ liệu gia đình theo yêu cầu.

    uv run --directory backend python -m hoicon.ops.data retention [--dry-run]
    uv run --directory backend python -m hoicon.ops.data request-delete --family <id> [--now] [--confirm]
    uv run --directory backend python -m hoicon.ops.data status --request <id>

`retention` chạy đúng việc của job hằng ngày (không đổi hạn lưu ở đây); `--dry-run` chỉ in số dòng sẽ bị đụng.
`request-delete` ghi `data_requests` và xếp job `purge_family` (worker thi hành); `--now` thi hành ngay trong lệnh
(máy dev không chạy worker). Ngoài dev/test/ci, `request-delete` cần `--confirm`. Chỉ in id, trạng thái và số dòng:
không tên, bí danh hay số điện thoại.
"""

import argparse
import asyncio
import sys
from uuid import UUID

from hoicon.agents.runtime import open_checkpointer
from hoicon.config import get_settings
from hoicon.db.models import DataRequest
from hoicon.db.session import get_sessionmaker
from hoicon.services import purge_service, retention_service


def _uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError("cần một UUID") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    retention = sub.add_parser("retention", help="áp hạn lưu dữ liệu (như job hằng ngày)")
    retention.add_argument("--dry-run", action="store_true", help="chỉ đếm, không xóa hay làm rỗng gì")
    delete = sub.add_parser("request-delete", help="ghi yêu cầu xóa dữ liệu một gia đình")
    delete.add_argument("--family", required=True, type=_uuid)
    delete.add_argument("--now", action="store_true", help="thi hành ngay thay vì chờ worker")
    delete.add_argument("--confirm", action="store_true", help="bắt buộc ngoài dev/test/ci")
    status = sub.add_parser("status", help="xem trạng thái một yêu cầu xóa")
    status.add_argument("--request", required=True, type=_uuid)
    return parser


def _line(request: DataRequest) -> str:
    done = request.completed_at.isoformat() if request.completed_at else "-"
    error = request.error_code or "-"
    asked = request.requested_at.isoformat()
    return f"{request.id} · {request.kind} · {request.status} · yêu cầu {asked} · xong {done} · lỗi {error}"


async def execute(args: argparse.Namespace) -> int:
    sessions = get_sessionmaker()
    if args.command == "status":
        async with sessions() as session:
            request = await session.get(DataRequest, args.request)
        if request is None:
            print("Không thấy yêu cầu này.")
            return 2
        print(_line(request))
        return 0
    if args.command == "retention":
        url = get_settings().database_url.get_secret_value()
        async with open_checkpointer(url) as saver:
            report = await retention_service.run_retention(sessions, saver.adelete_thread, dry_run=args.dry_run)
        print("Sẽ xử lý (dry-run):" if args.dry_run else "Đã xử lý:")
        for kind, count in report.items():
            print(f"  {kind}: {count}")
        return 0
    # request-delete
    if not get_settings().is_dev_env and not args.confirm:
        print("Từ chối: ngoài dev/test/ci lệnh này cần thêm --confirm.")
        return 2
    try:
        request = await purge_service.request_delete(sessions, args.family, "ops")
    except purge_service.FamilyNotFoundError:
        print("Từ chối: không thấy gia đình này.")
        return 2
    print(f"Đã ghi nhận: {_line(request)}")
    if args.now:
        url = get_settings().database_url.get_secret_value()
        async with open_checkpointer(url) as saver:
            report = await purge_service.purge_family(
                sessions, saver.adelete_thread, args.family, request_id=request.id
            )
        print("Đã thi hành: " + ", ".join(f"{k}={v}" for k, v in report.items()))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return asyncio.run(execute(args), loop_factory=asyncio.SelectorEventLoop)  # psycopg async cần SelectorEventLoop


if __name__ == "__main__":
    sys.exit(main())
