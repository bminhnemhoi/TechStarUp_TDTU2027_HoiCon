"""Kịch bản mô phỏng trên máy ảo Android (docs/EMULATOR.md §5, skill android-emulator-test).

    python scripts/emu-scenario.py --scenario smoke_call            # chỉ kiểm tra mô phỏng cuộc gọi
    python scripts/emu-scenario.py --scenario screen_only --runs 10 --prep kill  # H1: bắt cuộc gọi khi app bị kill
    python scripts/emu-scenario.py --scenario fake_police --runs 10 # cuộc gọi lạ → demobank → SafePause, đo độ trễ
    python scripts/emu-scenario.py --scenario bank_first --runs 5  # GAP: app ngân hàng mở sẵn trước cuộc gọi
    python scripts/emu-scenario.py --scenario booth --playlist all  # gian trưng bày: diễn từng mục danh sách phát của /booth

Chỉ dùng thư viện chuẩn + adb. Máy ảo phải đang chạy (bash scripts/emu-start.sh hc-api36 --headless).
Số điện thoại lấy từ data/fixtures/phones.json (HƯ CẤU). Không in/lưu dump layout/logcat thô (có số gọi đến).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# SDK: biến môi trường trước, rồi mặc định theo hệ điều hành (Windows D:/Android, Linux ~/Android).
SDK = Path(
    os.environ.get("ANDROID_HOME")
    or os.environ.get("ANDROID_SDK_ROOT")
    or ("D:/Android/Sdk" if os.name == "nt" else str(Path.home() / "Android" / "Sdk"))
)
EXE = ".exe" if os.name == "nt" else ""
ADB = str(SDK / "platform-tools" / f"adb{EXE}")
ACLI = str(SDK / "cmdline-tools" / "latest" / "bin" / f"android{EXE}")
SENTINEL = "vn.hoicon.sentinel"
DEMOBANK = os.environ.get("HC_DEMOBANK_PACKAGE", "vn.hoicon.demobank")  # đổi để thử R5 bằng bản demobank mang tên gói điều khiển từ xa
PAUSE_WAIT_S = 30
PHONES = json.loads((ROOT / "data" / "fixtures" / "phones.json").read_text(encoding="utf-8"))


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


def ensure_idle() -> bool:
    """Trước mỗi lần chạy: không còn cuộc gọi nào treo từ lần trước (máy ảo chậm có thể chưa dọn xong)."""
    for number in PHONES.values():
        if isinstance(number, str) and number.isdigit():
            adb("emu", "gsm", "cancel", number, check=False)
    return wait_for(lambda: call_state() == 0, 20, step_s=0.5)


def flush_modem() -> None:
    """Modem giả lập đôi khi không báo kết thúc cho cuộc gọi ĐÃ NHẤC MÁY rồi `gsm cancel`: điện thoại vẫn OFFHOOK
    và cuộc gọi kế tiếp bị nuốt (Telecom không thấy). Một cuộc gọi đổ chuông rồi hủy (số hư cấu khác) xả trạng thái đó.
    Gọi TRƯỚC prepare() để không làm ấm tiến trình của lần đo nguội."""
    number = PHONES["drill_fake_police"]
    adb("emu", "gsm", "call", number)
    wait_for(lambda: call_state() == 1, 5, step_s=0.3)
    adb("emu", "gsm", "cancel", number)
    wait_for(lambda: call_state() == 0, 10, step_s=0.3)
    time.sleep(1)


def clear_logcat() -> None:
    # logd trên API 29 đôi khi từ chối xóa ("failed to clear the 'main' log") ⇒ thử lại, không dừng cả lô.
    for _ in range(3):
        if subprocess.run([ADB, "logcat", "-c"], capture_output=True, timeout=60, check=False).returncode == 0:
            return
        time.sleep(1)


def ring(number: str) -> bool:
    """Gọi giả và chờ đổ chuông; False = lỗi môi trường (modem giả), không phải lỗi app."""
    if not ensure_idle():
        print("  cảnh báo: máy ảo vẫn còn cuộc gọi treo")
    clear_logcat()
    reply = adb("emu", "gsm", "call", number, check=False).replace("\r", " ").replace("\n", " ").strip()
    rang = wait_for(lambda: call_state() == 1, 15, step_s=0.3)
    if not rang:
        # Chẩn đoán (không in số gọi): trả lời của console modem, danh sách cuộc gọi của modem giả, trạng thái modem/vai trò.
        listing = adb("emu", "gsm", "list", check=False).replace("\r", " ").replace("\n", " ").strip()
        reply, listing = (re.sub(r"\d{5,}", "<số>", t) for t in (reply, listing))  # không in số gọi
        print(
            "  cuộc gọi giả KHÔNG đổ chuông (lỗi môi trường) — bỏ qua lần này"
            f" · console: {reply[:60]!r} · gsm list: {listing[:60]!r} · call_state={call_state()}"
            f" · modem IN_SERVICE={radio_ready()} · vai trò do Lính gác giữ={role_held()}"
        )
    return rang


def smoke_call() -> bool:
    number = PHONES["unknown_caller"]
    adb("emu", "gsm", "call", number)
    ringing = wait_for(lambda: call_state() == 1, 5)
    adb("emu", "gsm", "cancel", number)
    idle = wait_for(lambda: call_state() == 0, 5)
    print(f"smoke_call: đổ chuông={'đạt' if ringing else 'TRƯỢT'} · kết thúc={'đạt' if idle else 'TRƯỢT'}")
    return ringing and idle


def timing_marks() -> dict[str, int]:
    """Mốc HC_TIMING do app ghi: 'HC_TIMING: <mốc> <epoch ms>' (giờ máy — cùng gốc với timestamp UsageEvents)."""
    marks: dict[str, int] = {}
    for line in adb("logcat", "-d", "-s", "HC_TIMING:I").splitlines():
        m = re.search(r"HC_TIMING\s*:\s*(\w+)\s+(\d+)", line)
        if m:
            marks[m.group(1)] = int(m.group(2))
    return marks


def has_mark(*names: str) -> bool:
    marks = timing_marks()
    return any(n in marks for n in names)


E7_MARKERS = ("khoan chuyển tiền đã", "gọi cho con", "hỏi con")


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
        # E7 nhận ra bằng tiêu đề "khoan chuyển tiền đã" (cả hai bản giao diện) hoặc nút chính: "Gọi cho con" (bản View
        # của spec 001) / "Hỏi con" (bản Compose đang phát hành) ⇒ so khớp không phân biệt hoa thường.
        if not out.exists():
            return False
        tree = out.read_text(encoding="utf-8", errors="replace").lower()
        return any(marker in tree for marker in E7_MARKERS)


def prepare(prep: str) -> None:
    """H1: đưa Lính gác về trạng thái 'không chạy' trước cuộc gọi.

    force-stop: dừng hẳn (kể cả cửa sổ rủi ro của lần trước) — giống người dùng/OEM "buộc dừng".
    kill: force-stop, mở app, về Home rồi `am kill` — tiến trình nền bị hệ thống thu hồi (kiểu LMK).
    """
    if prep == "none":
        return
    adb("shell", "am", "force-stop", SENTINEL)
    if prep == "kill":
        adb(
            "shell",
            "monkey",
            "-p",
            SENTINEL,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )
        time.sleep(2)
        adb("shell", "input", "keyevent", "KEYCODE_HOME")
        time.sleep(1)
        adb("shell", "am", "kill", SENTINEL)
    time.sleep(0.5)
    if adb("shell", "pidof", SENTINEL, check=False).strip():
        print(f"  cảnh báo: tiến trình vẫn sống sau prep={prep}")


def radio_ready() -> bool:
    """SIM đã nạp và mạng thoại ở trạng thái IN_SERVICE. Ngay sau khởi động nguội (`--no-snapshot-load`) máy ảo báo
    sys.boot_completed trước khi modem giả đăng ký mạng; cuộc gọi giả lúc đó có thể đổ chuông (telephony.registry) mà Telecom
    không thấy ("Telecom không thấy cuộc gọi đến")."""
    sim = adb("shell", "getprop", "gsm.sim.state").strip()
    registry = adb("shell", "dumpsys", "telephony.registry")
    return sim.startswith(("LOADED", "READY")) and "mVoiceRegState=0(IN_SERVICE)" in registry


def role_held() -> bool:
    return SENTINEL in adb("shell", "cmd", "role", "get-role-holders", "--user", "0", "android.app.role.CALL_SCREENING")


def ensure_ready() -> None:
    """Chuẩn bị môi trường trước khi đo: chờ modem giả đăng ký mạng (tối đa 120 s) và bảo đảm Lính gác đang giữ vai trò
    sàng lọc cuộc gọi (vai trò có thể không còn sau `pm clear`/cài lại). Chỉ in cảnh báo, không đổi kết quả đo."""
    if not wait_for(radio_ready, 120, step_s=3):
        print("  cảnh báo: modem giả chưa IN_SERVICE sau 120 s — cuộc gọi giả có thể không tới Telecom (môi trường, không phải app)")
    if installed(SENTINEL) and not role_held():
        print("  vai trò CALL_SCREENING không do Lính gác giữ ⇒ cấp lại bằng `cmd role add-role-holder`")
        adb("shell", "cmd", "role", "add-role-holder", "--user", "0", "android.app.role.CALL_SCREENING", SENTINEL)


def screening_diagnosis() -> str:
    """Vì sao không có call_screened: Telecom không nhận cuộc gọi, hết hạn chờ (khởi động nguội), hay app im lặng."""
    log = adb("logcat", "-d", "-s", "Telecom:I", "TelecomFramework:I", "ActivityManager:I")
    started = re.search(rf"Start proc \d+:{re.escape(SENTINEL)}/", log) is not None
    if "IncomingCallFilterGraph" not in log:
        return (
            "Telecom không thấy cuộc gọi đến (lỗi modem giả lập)"
            f" · modem IN_SERVICE={radio_ready()} · vai trò do Lính gác giữ={role_held()}"
        )
    if "mCallScreeningPackageName='null'" in log:
        return "Telecom hết hạn chờ sàng lọc" + (" (đã khởi tiến trình, khởi động nguội quá chậm)" if started else "")
    if "SCREENING_COMPLETED" in log:
        return "Telecom đã sàng lọc xong nhưng không có mốc của app"
    return "Telecom có cuộc gọi nhưng chưa tới bước sàng lọc của app"


def percentile(values: list[int], q: float) -> int:
    """Nearest-rank (n=10 ⇒ p95 = giá trị lớn nhất)."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def screen_only_once(prep: str) -> bool | None:
    """H1 + H3: cuộc gọi số lạ có tới onScreenCall không, cửa sổ rủi ro (FGS) có mở được không."""
    number = PHONES["unknown_caller"]
    prepare(prep)
    if not ring(number):
        return None
    screened = wait_for(lambda: has_mark("call_screened"), 6, step_s=0.3)
    wait_for(
        lambda: has_mark("window_opened", "window_opened_bg", "window_failed"),
        3,
        step_s=0.3,
    )
    marks = timing_marks()
    adb("emu", "gsm", "cancel", number)
    wait_for(lambda: call_state() == 0, 5)
    window = next(
        (m for m in ("window_opened", "window_opened_bg", "window_failed") if m in marks),
        "không có",
    )
    denied = " · fgs_denied" if "fgs_denied" in marks else ""
    why = "" if screened else f" · {screening_diagnosis()}"
    print(f"  call_screened={'có' if screened else 'KHÔNG'} · cửa sổ={window}{denied}{why}")
    return screened


def screen_only(runs: int, prep: str) -> bool:
    results = [r for _ in range(runs) if (r := screen_only_once(prep)) is not None]
    caught = sum(results)
    print(f"screen_only (prep={prep}): bắt {caught}/{len(results)} cuộc gọi số lạ đã đổ chuông (chạy {runs} lần)")
    return caught == len(results) == runs


def fake_police_once(prep: str, caller: str = "flagged_caller") -> dict[str, int | bool] | None:
    number = PHONES[caller]
    flush_modem()
    prepare(prep)
    if not ring(number):
        return None
    adb("emu", "gsm", "accept", number)
    wait_for(lambda: call_state() == 2, 15)
    time.sleep(2)
    adb("shell", "monkey", "-p", DEMOBANK, "-c", "android.intent.category.LAUNCHER", "1")
    # Chờ bằng logcat (rẻ); `android layout` nặng nên chỉ chạy SAU khi đã có mốc, không làm méo độ trễ.
    # Chờ tới PAUSE_WAIT_S vì máy ảo có thể rất chậm khi RAM host thấp; độ trễ lấy từ mốc, không từ thời gian chờ.
    wait_for(lambda: has_mark("pause_shown"), PAUSE_WAIT_S, step_s=0.3)
    time.sleep(0.5)
    marks = timing_marks()
    visible = pause_visible()
    adb("emu", "gsm", "cancel", number)
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    # Dọn trạng thái trước lần sau: cuộc gọi kết thúc hẳn, SafePause cũ đã đóng (mốc pause_left).
    wait_for(lambda: call_state() == 0, 15)
    if "pause_resumed" in marks:
        wait_for(lambda: has_mark("pause_left"), 15, step_s=0.5)
    time.sleep(2)
    if "app_foreground" not in marks or "pause_shown" not in marks:
        why = "" if "call_screened" in marks else f" · {screening_diagnosis()}"
        print(f"  lần chạy TRƯỢT: hiện SafePause={visible}, mốc={sorted(marks)}{why}")
        return None
    run: dict[str, int | bool] = {
        "detect": marks.get("risk_detected", marks["pause_shown"]) - marks["app_foreground"],
        "pause": marks["pause_shown"] - marks["app_foreground"],
        "visible": visible,
    }
    if "risk_detected" in marks:
        run["open"] = marks["pause_shown"] - marks["risk_detected"]  # H5: startActivity → frame đầu
    if "tts_started" in marks:
        run["speech"] = marks["tts_started"] - marks["app_foreground"]
    tts_note = " · tts_unavailable" if "tts_unavailable" in marks else ""
    tts_note += " · watchdog dự phòng đã bật" if "pause_fallback" in marks else ""
    print(
        f"  phát hiện {run['detect']} ms · mở {run.get('open', '—')} ms · SafePause {run['pause']} ms"
        f" · câu nói đầu {run.get('speech', '—')} ms"
        f" · cây UI {'có' if visible else 'KHÔNG'} màn E7{tts_note}"
    )
    return run


def ordered_marks() -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for line in adb("logcat", "-d", "-s", "HC_TIMING:I").splitlines():
        m = re.search(r"HC_TIMING\s*:\s*(\w+)\s+(\d+)", line)
        if m:
            out.append((m.group(1), int(m.group(2))))
    return out


def transitions(marks: list[tuple[str, int]], prefix: str) -> dict[int, int]:
    """Chuỗi chuyển 1 (đổ chuông) → 2 (nhấc máy) → 0 (kết thúc) theo thứ tự; bỏ mốc trạng thái ban đầu trước chuông."""
    found: dict[int, int] = {}
    expected = [1, 2, 0]
    for name, ts in marks:
        if expected and name == f"{prefix}{expected[0]}":
            found[expected.pop(0)] = ts
    return found


def call_state_once() -> dict[str, int]:
    """H2: đổ chuông → nhấc máy → kết thúc; so tel_state_<n> (TelephonyCallback) với audio_mode_<n> (AudioManager)."""
    number = PHONES["unknown_caller"]
    if not ring(number):
        return {}

    def complete(state: int) -> bool:
        marks = ordered_marks()
        return all(state in transitions(marks, p) for p in ("tel_state_", "audio_mode_"))

    wait_for(lambda: complete(1), 15, step_s=0.3)
    time.sleep(3)
    adb("emu", "gsm", "accept", number)
    wait_for(lambda: complete(2), 15, step_s=0.3)
    time.sleep(3)
    adb("emu", "gsm", "cancel", number)
    wait_for(lambda: complete(0), 20, step_s=0.3)
    marks = ordered_marks()
    tel, audio = transitions(marks, "tel_state_"), transitions(marks, "audio_mode_")
    deltas: dict[str, int] = {}
    for state, label in ((1, "đổ chuông"), (2, "nhấc máy"), (0, "kết thúc")):
        if state in tel and state in audio:
            deltas[label] = audio[state] - tel[state]
    print(f"  audio_mode − tel_state (ms): {deltas or 'thiếu mốc'}")
    return deltas


def call_state_scenario(runs: int) -> bool:
    results = [call_state_once() for _ in range(runs)]
    complete = sum(1 for r in results if len(r) == 3)
    print(f"call_state: {complete}/{runs} lần có đủ 3 cặp mốc (audio mode đổi trễ hơn telephony bao nhiêu ms)")
    return complete == runs


def bank_first_once() -> int | None:
    """GAP: app ngân hàng mở SẴN trước cuộc gọi, nghe máy mà không rời app (không có ACTIVITY_RESUMED mới).

    Độ trễ = pause_shown − lúc cuộc gọi nối (mốc tel_state_2 / audio_mode_2 đầu tiên)."""
    number = PHONES["unknown_caller"]
    flush_modem()
    # Trạng thái sạch: cửa sổ rủi ro của lần trước (còn mở 10 phút sau cuộc gọi) sẽ bắt R1 ngay khi mở app ngân hàng
    # TRƯỚC cuộc gọi ⇒ không còn kiểm được GAP. Bản debug cho phép run-as xóa trạng thái.
    adb("shell", "am", "force-stop", SENTINEL)
    adb("shell", "run-as", SENTINEL, "rm", "-f", "shared_prefs/risk_window.xml", check=False)
    adb("shell", "monkey", "-p", DEMOBANK, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(3)
    if not ring(number):
        return None
    time.sleep(2)
    adb("emu", "gsm", "accept", number)
    wait_for(lambda: has_mark("pause_shown"), PAUSE_WAIT_S, step_s=0.3)
    time.sleep(0.5)
    first: dict[str, int] = {}
    for name, ts in ordered_marks():
        first.setdefault(name, ts)
    visible = pause_visible()
    adb("emu", "gsm", "cancel", number)
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    wait_for(lambda: call_state() == 0, 15)
    if "pause_resumed" in first:
        wait_for(lambda: has_mark("pause_left"), 15, step_s=0.5)
    time.sleep(2)
    connected = first.get("tel_state_2") or first.get("audio_mode_2")
    via_gap = "app_in_front_on_connect" in first and "app_foreground" not in first
    if not connected or "pause_shown" not in first:
        print(f"  lần chạy TRƯỢT: hiện E7={visible}, mốc={sorted(first)}")
        return None
    latency = first["pause_shown"] - connected
    print(
        f"  nối máy → E7 {latency} ms · qua GAP={'có' if via_gap else 'KHÔNG'} · cây UI {'có' if visible else 'KHÔNG'}"
    )
    return latency if via_gap and visible else None


def bank_first(runs: int) -> bool:
    results = [r for _ in range(runs) if (r := bank_first_once()) is not None]
    if results:
        print(
            f"bank_first: {len(results)}/{runs} lần E7 hiện qua GAP · p50={statistics.median(results):.0f}"
            f" · p95={percentile(results, 0.95)} ms (tính từ lúc nối máy)"
        )
    return len(results) == runs


def launch_baseline(runs: int) -> bool:
    """Đối chứng môi trường: thời gian mở app Compose tầm thường (:demobank) bằng `am start -W`, nguội và ấm."""
    component = f"{DEMOBANK}/.MainActivity"
    cold: list[int] = []
    warm: list[int] = []
    for _ in range(runs):
        for bucket, stop in ((cold, True), (warm, False)):
            if stop:
                adb("shell", "am", "force-stop", DEMOBANK)
            adb("shell", "input", "keyevent", "KEYCODE_HOME")
            time.sleep(2)
            out = adb("shell", "am", "start", "-W", "-n", component)
            # TotalTime vắng khi LaunchState=UNKNOWN (hệ thống quá chậm) ⇒ dùng WaitTime (gồm cả thời gian chờ).
            m = re.search(r"TotalTime:\s*(\d+)", out) or re.search(r"WaitTime:\s*(\d+)", out)
            if m:
                bucket.append(int(m.group(1)))
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    for name, values in (("nguội", cold), ("ấm", warm)):
        if values:
            print(
                f"launch_baseline {name}: n={len(values)} · p50={statistics.median(values):.0f}"
                f" · p95={percentile(values, 0.95)} ms"
            )
    return bool(cold and warm)


def fake_police(runs: int, prep: str) -> bool:
    missing = [p for p in (SENTINEL, DEMOBANK) if not installed(p)]
    if missing:
        print(f"fake_police: chưa áp dụng — thiếu app {', '.join(missing)} (spike P1-S1).")
        return True
    results = [r for _ in range(runs) if (r := fake_police_once(prep)) is not None]
    ok = len(results) == runs and all(r["visible"] for r in results)
    if results:
        pause = [int(r["pause"]) for r in results]
        detect = [int(r["detect"]) for r in results]
        opened = [int(r["open"]) for r in results if "open" in r]
        p95 = percentile(pause, 0.95)
        if opened:
            print(
                f"  mở SafePause (risk_detected → frame đầu): p50={statistics.median(opened):.0f}"
                f" p95={percentile(opened, 0.95)} ms"
            )
        print(
            f"fake_police (prep={prep}): {len(results)}/{runs} lần hiện SafePause"
            f" · phát hiện p50={statistics.median(detect):.0f} p95={percentile(detect, 0.95)} ms"
            f" · SafePause p50={statistics.median(pause):.0f} p95={p95} ms"
            f" · ngưỡng ≤ 3000 ms ⇒ {'ĐẠT' if ok and p95 <= 3000 else 'TRƯỢT'}"
        )
        ok = ok and p95 <= 3000
    return ok


@dataclasses.dataclass(frozen=True)
class BoothScene:
    """Cảnh máy ảo của một mục danh sách phát `/booth` (apps/web/src/lib/booth.ts): ai gọi, và E7 có phải hiện không."""

    caller: str  # khóa trong data/fixtures/phones.json (số HƯ CẤU)
    expect_pause: bool


# Khóa = `scenarioId` trong PLAYLIST của booth.ts (test_emu_scenario_booth.py giữ hai bên khớp nhau).
BOOTH_SCENES = {
    "fake_police_safe_account_002": BoothScene("flagged_caller", True),
    "fake_bank_card_locked_002": BoothScene("flagged_caller", True),
    "benign_family_son_rent_002": BoothScene("trusted_child", False),  # con gọi rồi mở app ngân hàng: HỏiCon không được báo nhầm
}


def booth_plan(name: str) -> list[str]:
    """`all` = cả danh sách theo thứ tự diễn; hoặc đúng một scenarioId."""
    if name == "all":
        return list(BOOTH_SCENES)
    if name not in BOOTH_SCENES:
        raise ValueError(f"không có cảnh '{name}' (có: {', '.join(BOOTH_SCENES)}, all)")
    return [name]


def add_contact(number: str) -> None:
    """Lưu số (HƯ CẤU) vào danh bạ MÁY ẢO: Telecom không đưa cuộc gọi từ liên hệ đã lưu cho CallScreeningService (luật R0)."""
    uri = "content://com.android.contacts"
    adb("shell", "content", "insert", "--uri", f"{uri}/raw_contacts", "--bind", "account_type:n:", "--bind", "account_name:n:", check=False)
    ids = [int(i) for i in re.findall(r"_id=(\d+)", adb("shell", "content", "query", "--uri", f"{uri}/raw_contacts", "--projection", "_id", check=False))]
    if not ids:
        print("  cảnh báo: không thêm được liên hệ vào danh bạ máy ảo")
        return
    rid = max(ids)
    for mime, value in (("vnd.android.cursor.item/phone_v2", number), ("vnd.android.cursor.item/name", "Con (thử)")):
        adb("shell", "content", "insert", "--uri", f"{uri}/data", "--bind", f"raw_contact_id:i:{rid}",
            "--bind", f"mimetype:s:{mime}", "--bind", f"data1:s:{value}", check=False)


def clear_contacts() -> None:
    adb("shell", "content", "delete", "--uri", "content://com.android.contacts/raw_contacts", check=False)


def benign_once(caller: str) -> bool | None:
    """Cuộc gọi hợp lệ + mở app ngân hàng: True = E7 KHÔNG hiện (đúng), False = báo nhầm, None = lỗi môi trường."""
    number = PHONES[caller]
    flush_modem()
    # Cửa sổ rủi ro của lượt trước còn mở 10 phút sau cuộc gọi: giữ nguyên thì mở app ngân hàng sẽ báo vì lượt TRƯỚC, không phải vì cuộc gọi này.
    adb("shell", "am", "force-stop", SENTINEL)
    adb("shell", "run-as", SENTINEL, "rm", "-f", "shared_prefs/risk_window.xml", check=False)
    prepare("none")
    add_contact(number)
    if not ring(number):
        clear_contacts()
        return None
    adb("emu", "gsm", "accept", number)
    wait_for(lambda: call_state() == 2, 15)
    time.sleep(2)
    adb("shell", "monkey", "-p", DEMOBANK, "-c", "android.intent.category.LAUNCHER", "1")
    time.sleep(PAUSE_WAIT_S / 3)  # đủ lâu để một cảnh báo (nếu có) kịp hiện
    shown = has_mark("pause_shown") or pause_visible()
    adb("emu", "gsm", "cancel", number)
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    wait_for(lambda: call_state() == 0, 15)
    clear_contacts()
    time.sleep(2)
    print(f"  cuộc gọi hợp lệ: E7 {'HIỆN (báo nhầm)' if shown else 'không hiện (đúng)'}")
    return not shown


def booth(name: str, runs: int) -> bool:
    missing = [p for p in (SENTINEL, DEMOBANK) if not installed(p)]
    if missing:
        print(f"booth: thiếu app {', '.join(missing)}", file=sys.stderr)
        return False
    ok = True
    for scenario_id in booth_plan(name):
        scene = BOOTH_SCENES[scenario_id]
        print(f"== {scenario_id} (gọi {scene.caller}, {'cần' if scene.expect_pause else 'không được'} hiện E7) ==")
        if scene.expect_pause:
            results = [r for _ in range(runs) if (r := fake_police_once("none", scene.caller)) is not None]
            good = len(results) == runs and all(r["visible"] and int(r["pause"]) <= 3000 for r in results)
        else:
            results = [r for _ in range(runs) if (r := benign_once(scene.caller)) is not None]
            good = len(results) == runs and all(results)
        print(f"  {scenario_id}: {len(results)}/{runs} lần hợp lệ ⇒ {'ĐẠT' if good else 'TRƯỢT'}")
        ok = ok and good
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--scenario",
        choices=[
            "smoke_call",
            "screen_only",
            "fake_police",
            "bank_first",
            "launch_baseline",
            "call_state",
            "booth",
        ],
        default="smoke_call",
    )
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument(
        "--prep",
        choices=["none", "kill", "force-stop"],
        default="none",
        help="trạng thái app trước mỗi cuộc gọi (H1)",
    )
    ap.add_argument("--playlist", default="all", help="scenario=booth: một scenarioId của danh sách phát /booth, hoặc 'all'")
    ap.add_argument("--avd", help="chỉ để ghi báo cáo; máy ảo phải đang chạy")
    args = ap.parse_args()
    if args.scenario == "booth":
        try:
            booth_plan(args.playlist)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 2

    if "emulator-" not in adb("devices"):
        print(
            "Không thấy máy ảo. Chạy: bash scripts/emu-start.sh hc-api36 --headless",
            file=sys.stderr,
        )
        return 2
    # Bộ đệm logcat mặc định của máy ảo (2 MiB) có thể xoay vòng mất mốc trong một lần chạy dài.
    adb("logcat", "-G", "16M", check=False)
    ensure_ready()
    sdk = adb("shell", "getprop", "ro.build.version.sdk").strip()
    print(f"Máy ảo API {sdk}{f' ({args.avd})' if args.avd else ''}")
    if args.scenario == "smoke_call":
        ok = smoke_call()
    elif args.scenario == "screen_only":
        ok = screen_only(args.runs, args.prep)
    elif args.scenario == "bank_first":
        ok = bank_first(args.runs)
    elif args.scenario == "launch_baseline":
        ok = launch_baseline(args.runs)
    elif args.scenario == "call_state":
        ok = call_state_scenario(args.runs)
    elif args.scenario == "booth":
        ok = booth(args.playlist, args.runs)
    else:
        ok = fake_police(args.runs, args.prep)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
