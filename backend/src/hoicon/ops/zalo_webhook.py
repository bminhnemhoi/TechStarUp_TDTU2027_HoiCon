"""Đặt / xem / xóa webhook của bot Zalo — chỉ in Đạt/Lỗi, KHÔNG BAO GIỜ in token, khóa hay URL (ADR-003: token nằm
trên đường dẫn URL nên không ai dựng lệnh curl bằng tay):

    uv run --directory backend python -m hoicon.ops.zalo_webhook set --url https://<tên-đường-hầm>.trycloudflare.com
    uv run --directory backend python -m hoicon.ops.zalo_webhook info
    uv run --directory backend python -m hoicon.ops.zalo_webhook delete

`set` nhận địa chỉ gốc của đường hầm (tự nối `/webhooks/zalo/<bot_id>`) hoặc URL đầy đủ; bắt buộc HTTPS và là địa chỉ
công khai (Zalo từ chối localhost/IP nội bộ). Token đọc từ HOICON_ZALO_BOT_TOKEN, khóa xác thực webhook từ
HOICON_ZALO_WEBHOOK_SECRET. Zalo tự gọi thử URL ngay khi đặt và vẫn lưu URL kể cả khi thử thất bại ⇒ kết quả thử khác
`webhook.ok` được báo là Lỗi.
"""

import argparse
import asyncio
import ipaddress
import re
import sys
from datetime import UTC, datetime
from urllib.parse import urlsplit, urlunsplit

from hoicon.channels.zalo import LiveZaloClient, ZaloError
from hoicon.config import Settings, get_settings

_OUTCOME = re.compile(r"[a-z0-9_.]{1,40}")  # chỉ in mã kết quả có dạng đã biết (webhook.ok, webhook.http.403…)


def normalize_url(raw: str, bot_id: str) -> str:
    """⇒ URL webhook đầy đủ hoặc ValueError (thông điệp không chứa URL người dùng nhập)."""
    try:
        parts = urlsplit(raw.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        raise ValueError("URL không hợp lệ") from None
    if parts.scheme != "https" or not host:
        raise ValueError("URL phải bắt đầu bằng https://")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("URL không được chứa tài khoản, tham số hay đoạn #")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None  # là tên miền, không phải IP
    is_internal_name = address is None and (host == "localhost" or host.endswith(".localhost") or "." not in host)
    if is_internal_name or (address is not None and not address.is_global):
        raise ValueError("Zalo chỉ nhận URL công khai trên Internet (không phải localhost/IP/tên nội bộ)")
    expected = f"/webhooks/zalo/{bot_id}"
    path = parts.path.rstrip("/") or expected
    if path != expected:
        raise ValueError(f"đường dẫn phải là {expected} (hoặc bỏ trống để tự nối)")
    netloc = host if port is None else f"{host}:{port}"
    return urlunsplit(("https", netloc, path, "", ""))


def _outcome(value: object) -> str:
    return value if isinstance(value, str) and _OUTCOME.fullmatch(value) else "không rõ"


def _updated(result: dict[str, object]) -> str:
    stamp = result.get("updated_at")
    if isinstance(stamp, int) and stamp > 0:
        try:
            return datetime.fromtimestamp(stamp / 1000, UTC).strftime("%d/%m/%Y %H:%M UTC")
        except (OverflowError, OSError, ValueError):
            pass
    return "không rõ giờ"


async def run(argv: list[str], settings: Settings, client: LiveZaloClient | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    set_cmd = commands.add_parser("set", help="đặt webhook")
    set_cmd.add_argument("--url", required=True, help="địa chỉ gốc của đường hầm hoặc URL webhook đầy đủ (https)")
    commands.add_parser("info", help="xem đã đặt webhook chưa")
    commands.add_parser("delete", help="xóa webhook")
    args = parser.parse_args(argv)

    if settings.zalo_bot_token is None or not settings.zalo_bot_token.get_secret_value():
        print("Thiếu HOICON_ZALO_BOT_TOKEN (docs/setup/ACCOUNTS.md).")
        return 1
    url = shared = ""
    if args.command == "set":
        try:
            url = normalize_url(args.url, settings.zalo_bot_id)
        except ValueError as exc:
            print(f"Lỗi: {exc}.")
            return 2
        configured = settings.zalo_webhook_secret
        if configured is None or not configured.get_secret_value():
            print("Thiếu HOICON_ZALO_WEBHOOK_SECRET (chạy: python -m hoicon.ops.init_env).")
            return 1
        shared = configured.get_secret_value()
        if not 8 <= len(shared) <= 256:
            print("Lỗi: HOICON_ZALO_WEBHOOK_SECRET cần 8–256 ký tự.")
            return 1

    try:
        live = client or LiveZaloClient(settings.zalo_bot_token)
        if args.command == "set":
            result = await live.set_webhook(url, shared)
            verification = result.get("verification")
            checked = verification if isinstance(verification, dict) else {}
            if checked.get("ok") is False:
                print(f"Lỗi: Zalo đã lưu webhook nhưng gọi thử thất bại ({_outcome(checked.get('outcome'))}).")
                return 1
            outcome = _outcome(checked.get("outcome")) if checked else "Zalo chưa báo kết quả gọi thử"
            print(f"Đạt: đã đặt webhook; kết quả Zalo gọi thử: {outcome}.")
        elif args.command == "info":
            result = await live.get_webhook_info()
            if result.get("url"):
                print(f"Đạt: đã đặt webhook (cập nhật lần cuối {_updated(result)}).")
            else:
                print("Đạt: chưa đặt webhook.")
        else:
            await live.delete_webhook()
            print("Đạt: đã xóa webhook.")
    except ZaloError as exc:
        print("Lỗi: không kết nối được Zalo (lỗi mạng)." if exc.status is None else f"Lỗi (HTTP {exc.status}).")
        return 1
    except RuntimeError as exc:  # token sai định dạng: thông điệp của LiveZaloClient không chứa token
        print(f"Lỗi: {exc}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(
        run(sys.argv[1:] if argv is None else argv, get_settings()), loop_factory=asyncio.SelectorEventLoop
    )


if __name__ == "__main__":
    sys.exit(main())
