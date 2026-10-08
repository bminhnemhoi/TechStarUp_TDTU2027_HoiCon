"""Kiểm tra khóa dịch vụ trong backend/.env có dùng được không — chỉ in Đạt/Thiếu/Lỗi, KHÔNG BAO GIỜ in khóa.

    uv run --directory backend python -m hoicon.ops.check_keys

Mỗi phép thử là một lời gọi chỉ-đọc, miễn phí (liệt kê model / getMe). Xem docs/setup/ACCOUNTS.md.
Nguyên tắc chống lộ khóa (review bảo mật 08/10):
- kiểm tra ký tự của khóa TRƯỚC khi gọi mạng (khoảng trắng/xuống dòng làm urllib ném lỗi chứa nguyên khóa);
- mọi exception chỉ được in tên lớp, không bao giờ str(exc);
- không theo redirect (urllib chuyển tiếp header chứa khóa sang host khác).
"""

import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from pydantic import SecretStr

from hoicon.config import Settings, get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]
TIMEOUT_S = 10
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # 3xx ⇒ HTTPError, không gửi khóa tới host khác


_OPENER = urllib.request.build_opener(_NoRedirect)


def _get(url: str, headers: dict[str, str]) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 — URL https cố định
    try:
        with _OPENER.open(req, timeout=TIMEOUT_S) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def malformed(value: str) -> bool:
    """Khóa hợp lệ của mọi dịch vụ ở đây là ASCII in được, không khoảng trắng."""
    return not value or any(c.isspace() or not c.isascii() or not c.isprintable() for c in value)


def check_anthropic(key: SecretStr) -> str:
    status, _ = _get(
        "https://api.anthropic.com/v1/models?limit=1",
        {"x-api-key": key.get_secret_value(), "anthropic-version": "2023-06-01"},
    )
    return "Đạt" if status == 200 else f"Lỗi HTTP {status}"


def check_gemini(key: SecretStr) -> str:
    # Khóa đi trong header, không nằm trên URL (tránh lọt vào log proxy).
    status, _ = _get(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1",
        {"x-goog-api-key": key.get_secret_value()},
    )
    return "Đạt" if status == 200 else f"Lỗi HTTP {status}"


def check_zalo(token: SecretStr) -> str:
    # Zalo Bot API đặt token trên đường dẫn URL (thiết kế của nền tảng) — URL không bao giờ được in/log.
    status, body = _get(f"https://bot-api.zaloplatforms.com/bot{token.get_secret_value()}/getMe", {})
    return "Đạt" if status == 200 and body.get("ok") else f"Lỗi HTTP {status}"


def check_webhook_secret(value: SecretStr) -> str:
    n = len(value.get_secret_value())
    return "Đạt" if 8 <= n <= 256 else "Lỗi: cần 8–256 ký tự"


def check_pepper(value: SecretStr) -> str:
    return "Đạt" if HEX64.match(value.get_secret_value()) else "Lỗi: cần chuỗi hex 64 ký tự (chạy init_env)"


def run(settings: Settings) -> list[tuple[str, str]]:
    checks: list[tuple[str, SecretStr | None, Callable[[SecretStr], str]]] = [
        ("Anthropic API", settings.anthropic_api_key, check_anthropic),
        ("Gemini API", settings.gemini_api_key, check_gemini),
        ("Zalo Bot token", settings.zalo_bot_token, check_zalo),
        ("Zalo webhook secret (8–256)", settings.zalo_webhook_secret, check_webhook_secret),
        ("Pepper băm số điện thoại", settings.phone_pepper_1, check_pepper),
    ]
    results: list[tuple[str, str]] = []
    for name, value, check in checks:
        if value is None or not value.get_secret_value():
            results.append((name, "Thiếu"))
        elif malformed(value.get_secret_value()):
            results.append((name, "Lỗi: có khoảng trắng/xuống dòng/ký tự lạ — dán lại"))
        else:
            try:
                results.append((name, check(value)))
            except Exception as exc:  # chỉ tên lớp: thông điệp của urllib/http.client có thể chứa khóa
                results.append((name, f"Lỗi ({type(exc).__name__})"))
    firebase = REPO_ROOT / "apps" / "android" / "app" / "google-services.json"
    results.append(("Firebase google-services.json", "Có" if firebase.exists() else "Thiếu"))
    return results


def main() -> int:
    results = run(get_settings())
    width = max(len(name) for name, _ in results)
    for name, outcome in results:
        print(f"  {name.ljust(width)}  {outcome}")
    return 0 if all(o in ("Đạt", "Có") for _, o in results) else 1


if __name__ == "__main__":
    sys.exit(main())
