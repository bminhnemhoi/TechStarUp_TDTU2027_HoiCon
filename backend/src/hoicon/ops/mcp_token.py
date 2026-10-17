"""Sinh token Bearer cho `/mcp/threat` (spec 003, FR-008):

    uv run --directory backend python -m hoicon.ops.mcp_token new --client claude-team

In token MỘT lần (hiển thị cho người dùng, không lưu ở đâu) và một dòng cấu hình chỉ chứa SHA-256 của token để
người dùng TỰ dán vào `backend/.env` — lệnh này không đọc, không ghi `.env` hay tệp nào. Thu hồi: xóa client khỏi
dòng cấu hình và khởi động lại API. Nhiều client: gộp các cặp `"tên":"hash"` vào cùng một đối tượng JSON.
"""

import argparse
import hashlib
import json
import re
import secrets
import sys

_NAME = re.compile(r"^[a-z0-9_-]{1,32}$")


def _client(value: str) -> str:
    if not _NAME.match(value):
        raise argparse.ArgumentTypeError("tên client gồm a-z, 0-9, '-', '_' (1–32 ký tự)")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new", help="sinh token mới cho một client").add_argument("--client", required=True, type=_client)
    args = parser.parse_args(argv)
    token = secrets.token_urlsafe(32)  # 32 byte ngẫu nhiên
    digest = hashlib.sha256(token.encode()).hexdigest()
    print("Gửi token này cho client NGAY — sẽ không hiển thị lại và máy chủ không lưu nó:")
    print(f"TOKEN: {token}")
    print(
        "Dán dòng sau vào backend/.env (chỉ chứa hash; client khác thì gộp vào cùng đối tượng), rồi khởi động lại API:"
    )
    print(f"HOICON_MCP_THREAT_CLIENTS={json.dumps({args.client: digest})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
