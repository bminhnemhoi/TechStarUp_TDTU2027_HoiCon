"""Tạo/bổ sung backend/.env và tự sinh bí mật cục bộ — KHÔNG in giá trị. Minh tự chạy (Claude không được ghi .env):

    uv run --directory backend python -m hoicon.ops.init_env
    uv run --directory backend python -m hoicon.ops.init_env --new-pepper   # CHỈ khi chấp nhận mất liên kết số đã băm

- Chưa có .env: tạo từ .env.example, sinh HOICON_PHONE_PEPPER_1 + HOICON_ZALO_WEBHOOK_SECRET, bỏ comment 3 khóa dán tay.
- Đã có .env: CHỈ NỐI THÊM biến còn thiếu (đọc bằng python-dotenv — cùng ngữ nghĩa với lúc chạy), không sửa dòng cũ.
  Thiếu pepper trong .env đã có ⇒ từ chối, trừ khi có --new-pepper: pepper mới làm mọi phone_hmac
  đã lưu thành mồ côi (ADR-006).
- Ghi atomic (.env.tmp → os.replace); POSIX chmod 600; Windows in lệnh icacls để Minh tự khóa quyền.
"""

import argparse
import os
import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND = Path(__file__).resolve().parents[3]
EXAMPLE = BACKEND / ".env.example"
TARGET = BACKEND / ".env"

PEPPER = "HOICON_PHONE_PEPPER_1"
GENERATED = {
    "HOICON_PHONE_PEPPER_KID": lambda: "1",
    PEPPER: lambda: secrets.token_hex(32),
    "HOICON_ZALO_WEBHOOK_SECRET": lambda: secrets.token_urlsafe(32),
}
MANUAL = ("HOICON_ANTHROPIC_API_KEY", "HOICON_GEMINI_API_KEY", "HOICON_ZALO_BOT_TOKEN")


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _fresh_text() -> str:
    """.env mới = .env.example, bỏ comment các dòng cần điền/sinh."""
    out: list[str] = []
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.lstrip("# ").split("=", 1)[0] if line.lstrip().startswith("#") else ""
        if stripped in GENERATED:
            out.append(f"{stripped}={GENERATED[stripped]()}")
        elif stripped in MANUAL:
            out.append(f"{stripped}=")
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--new-pepper", action="store_true", help="cho phép sinh pepper mới cho .env đã tồn tại")
    args = parser.parse_args(argv)

    if not TARGET.exists():
        _write_atomic(TARGET, _fresh_text())
        action, added = "Đã tạo", list(GENERATED)
    else:
        current = {k: v for k, v in dotenv_values(TARGET).items() if v}
        missing = [name for name in GENERATED if name not in current]
        if PEPPER in missing and not args.new_pepper:
            print(
                f"Từ chối: backend/.env đã có nhưng thiếu {PEPPER}. Nếu có bản sao lưu pepper"
                " (D:\\secrets) hãy dán lại; chỉ chạy lại với --new-pepper khi chấp nhận mọi số điện thoại"
                " đã băm trước đây không so khớp được nữa.",
                file=sys.stderr,
            )
            return 2
        text = TARGET.read_text(encoding="utf-8")
        if missing:
            appended = "".join(f"{name}={GENERATED[name]()}\n" for name in missing)
            text = text + ("" if text.endswith("\n") or not text else "\n") + "# Thêm bởi init_env\n" + appended
            _write_atomic(TARGET, text)
        action, added = "Đã cập nhật", missing

    values = dotenv_values(TARGET)
    still_manual = [n for n in MANUAL if not values.get(n)]
    print(f"{action} backend/.env — sinh mới: {', '.join(added) or 'không có'}")
    print(f"Còn phải dán tay: {', '.join(still_manual) or 'không có'} (docs/setup/ACCOUNTS.md)")
    if PEPPER in added:
        print(f"Sao lưu {PEPPER} sang D:\\secrets\\hoicon-pepper.txt — mất pepper là mất liên kết số đã băm (ADR-006).")
    if os.name == "nt":
        print('Khóa quyền file (khuyên làm): icacls backend\\.env /inheritance:r /grant:r "%USERNAME%:F"')
    print("Kiểm tra: uv run --directory backend python -m hoicon.ops.check_keys")
    return 0


if __name__ == "__main__":
    sys.exit(main())
