#!/usr/bin/env python3
"""Quay tư liệu video demo (docs/demo/VIDEO-3MIN.md) trên máy ảo đang chạy: một cú quay liền, mỗi cảnh một tệp mp4.

    bash scripts/emu-start.sh hc-api36 --headless          # máy ảo đã ghép đôi + đồng ý (E3), :demobank đã cài
    python3 scripts/emu-demo-record.py [--out ~/hoicon-evidence/video]

Cảnh: s1 cuộc gọi lạ · s2 mở ứng dụng ngân hàng → dừng an toàn · s3 HỏiCon hỏi bác một câu (E8, tự kéo từ máy chủ, không cần FCM) · s4 trở lại dừng an toàn, bác bấm "Hỏi con" · s5 bàn phím gọi trống.
Dùng `adb shell screenrecord` (1080x2400, chữ 100%), số gọi đến là số HƯ CẤU (data/fixtures/phones.json). Máy ảo KHÔNG có âm thanh:
lời đọc của HỏiCon không nằm trong video (cần quay máy thật hoặc thu riêng). Ghi/in ra giờ UTC từng cảnh để đối chiếu với nhật ký máy chủ.
Cảnh Zalo (mô phỏng) và trang /a/[token] do Playwright quay, không thuộc tệp này. Không lưu tệp vào repo: chỉ ngoài repo."""

import argparse
import json
import os
import subprocess
import sys
import time

ADB = os.environ.get("ADB") or os.path.expanduser("~/Android/Sdk/platform-tools/adb")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUMBER = json.load(open(os.path.join(ROOT, "data/fixtures/phones.json"), encoding="utf-8"))["flagged_caller"]  # HƯ CẤU
# Tọa độ cố định (1080x2400, chữ 100%): tìm nút theo chữ "Hỏi con" trúng cả đoạn chữ phía trên, nên không dùng.
HOI_CON_BUTTON = ("540", "1734")  # nút "Hỏi con" ghim ở đáy SafePause
E8_YES = ("540", "1783")  # nút "CÓ" của câu hỏi E8


def adb(*args):
    return subprocess.run([ADB, *args], capture_output=True, text=True).stdout


def scene(out, name, secs, actions):
    device = f"/sdcard/{name}.mp4"
    proc = subprocess.Popen([ADB, "shell", "screenrecord", "--bit-rate", "8000000", "--time-limit", str(secs), device])
    started = time.time()
    stamp = time.strftime("%H:%M:%S", time.gmtime())
    time.sleep(1.0)
    actions()
    while time.time() - started < secs - 0.5:
        time.sleep(0.2)
    proc.wait()
    time.sleep(1)
    subprocess.run([ADB, "pull", device, os.path.join(out, f"{name}.mp4")], capture_output=True)
    adb("shell", "rm", device)
    print(f"{name}: {secs}s, bắt đầu {stamp} UTC, {os.path.getsize(os.path.join(out, name + '.mp4')) // 1024} KB")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=os.path.expanduser("~/hoicon-evidence/video"))
    out = parser.parse_args().out
    os.makedirs(out, exist_ok=True)
    adb("shell", "settings", "put", "system", "font_scale", "1.0")
    adb("shell", "input", "keyevent", "KEYCODE_HOME")
    time.sleep(1)

    def call():
        adb("emu", "gsm", "call", NUMBER)
        time.sleep(5)
        adb("emu", "gsm", "accept", NUMBER)
        time.sleep(4)

    def bank():
        adb("shell", "monkey", "-p", "vn.hoicon.demobank", "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(5)

    def question():
        time.sleep(5)  # câu hỏi của máy chủ tới sau vài giây; bác trả lời "CÓ"
        adb("shell", "input", "tap", *E8_YES)
        time.sleep(3)

    def ask_child():
        time.sleep(3)
        adb("shell", "input", "tap", *HOI_CON_BUTTON)
        time.sleep(5)

    scene(out, "s1_cuoc_goi_la", 14, call)
    scene(out, "s2_mo_ung_dung_ngan_hang", 9, bank)
    scene(out, "s3_cau_hoi_cua_hoicon", 10, question)
    scene(out, "s4_hoi_con", 11, ask_child)
    scene(out, "s5_ban_phim_goi", 8, lambda: time.sleep(6))
    adb("emu", "gsm", "cancel", NUMBER)
    adb("shell", "input", "keyevent", "KEYCODE_HOME")


if __name__ == "__main__":
    sys.exit(main())
