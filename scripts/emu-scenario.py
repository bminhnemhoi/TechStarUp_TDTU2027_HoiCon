"""Kịch bản mô phỏng trên máy ảo Android (docs/EMULATOR.md §5, skill android-emulator-test).

    python scripts/emu-scenario.py --scenario smoke_call            # chỉ kiểm tra mô phỏng cuộc gọi
    python scripts/emu-scenario.py --scenario fake_police --runs 10 # cuộc gọi lạ → demobank → SafePause, đo độ trễ

Chỉ dùng thư viện chuẩn + adb. Máy ảo phải đang chạy (bash scripts/emu-start.sh hc-api36 --headless).
Số điện thoại lấy từ data/fixtures/phones.json (HƯ CẤU). Không in/lưu dump layout/logcat thô (có số gọi đến).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK = Path("D:/Android/Sdk")
ADB = str(SDK / "platform-tools" / "adb.exe")
ACLI = str(SDK / "cmdline-tools" / "latest" / "bin" / "android.exe")
SENTINEL = "vn.hoicon.sentinel"
DEMOBANK = "vn.hoicon.demobank"
PHONES = json.loads(
    (ROOT / "data" / "fixtures" / "phones.json").read_text(encoding="utf-8")
)


def adb(*args: str, check: bool = True) -> str:
    res = subprocess.run(
        [ADB, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args[:3])}… lỗi: {res.stderr.strip()[:200]}")
    return res.stdout.replace("\r", "")


def call_state() -> int:
    m = re.search(r"mCallState=(\d)", adb("shell", "dumpsys", "telephony.registry"))
    return int(m.group(1)) if m else -1


def installed(pkg: str) -> bool:
    return f"package:{pkg}" in adb("shell", "pm", "list", "packages", pkg)


def wait_for(pred, timeout_s: float, step_s: float = 0.2) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(step_s)
    return False


def smoke_call() -> bool:
    number = PHONES["unknown_caller"]
    adb("emu", "gsm", "call", number)
    ringing = wait_for(lambda: call_state() == 1, 5)
    adb("emu", "gsm", "cancel", number)
    idle = wait_for(lambda: call_state() == 0, 5)
    print(
        f"smoke_call: đổ chuông={'đạt' if ringing else 'TRƯỢT'} · kết thúc={'đạt' if idle else 'TRƯỢT'}"
    )
    return ringing and idle


def timing_marks() -> dict[str, int]:
    """Mốc HC_TIMING do app ghi: 'HC_TIMING: <mốc> <ms đơn điệu>'."""
    marks: dict[str, int] = {}
    for line in adb("logcat", "-d", "-s", "HC_TIMING:I").splitlines():
        m = re.search(r"HC_TIMING\s*:\s*(\w+)\s+(\d+)", line)
        if m:
            marks[m.group(1)] = int(m.group(2))
    return marks


def pause_visible() -> bool:
    # Ghi ra file rồi đọc UTF-8: stdout của android.exe trên console Windows làm vỡ dấu tiếng Việt.
    # File tạm bị xóa ngay (cây UI có thể chứa số gọi đến trong thông báo hệ thống).
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "layout.json"
        subprocess.run(
            [ACLI, "layout", "--flat", f"--output={out}"],
            capture_output=True,
            timeout=60,
            check=False,
        )
        return out.exists() and "Hỏi con" in out.read_text(
            encoding="utf-8", errors="replace"
        )


def fake_police_once() -> int | None:
    number = PHONES["flagged_caller"]
    adb("logcat", "-c")
    adb("emu", "gsm", "call", number)
    wait_for(lambda: call_state() == 1, 5)
    adb("emu", "gsm", "accept", number)
    time.sleep(2)
    adb(
        "shell", "monkey", "-p", DEMOBANK, "-c", "android.intent.category.LAUNCHER", "1"
    )
    shown = wait_for(pause_visible, 6, step_s=0.5)
    marks = timing_marks()
    adb("emu", "gsm", "cancel", number)
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    if not shown or "app_foreground" not in marks or "pause_shown" not in marks:
        print(f"  lần chạy TRƯỢT: hiện SafePause={shown}, mốc={sorted(marks)}")
        return None
    return marks["pause_shown"] - marks["app_foreground"]


def fake_police(runs: int) -> bool:
    missing = [p for p in (SENTINEL, DEMOBANK) if not installed(p)]
    if missing:
        print(
            f"fake_police: chưa áp dụng — thiếu app {', '.join(missing)} (spike P1-S1)."
        )
        return True
    latencies = [lat for _ in range(runs) if (lat := fake_police_once()) is not None]
    ok = len(latencies) == runs
    if latencies:
        p95 = sorted(latencies)[max(0, int(round(0.95 * len(latencies))) - 1)]
        print(
            f"fake_police: {len(latencies)}/{runs} lần hiện SafePause · p50={statistics.median(latencies):.0f} ms"
            f" · p95={p95} ms · ngưỡng ≤ 3000 ms ⇒ {'ĐẠT' if ok and p95 <= 3000 else 'TRƯỢT'}"
        )
        ok = ok and p95 <= 3000
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--scenario", choices=["smoke_call", "fake_police"], default="smoke_call"
    )
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--avd", help="chỉ để ghi báo cáo; máy ảo phải đang chạy")
    args = ap.parse_args()

    if "emulator-" not in adb("devices"):
        print(
            "Không thấy máy ảo. Chạy: bash scripts/emu-start.sh hc-api36 --headless",
            file=sys.stderr,
        )
        return 2
    sdk = adb("shell", "getprop", "ro.build.version.sdk").strip()
    print(f"Máy ảo API {sdk}{f' ({args.avd})' if args.avd else ''}")
    ok = smoke_call() if args.scenario == "smoke_call" else fake_police(args.runs)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
