"""Kiểm tra tham số của scripts/voice-lab.sh (chạy trước mọi lệnh adb) — python3 -m unittest discover -s scripts/tests"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "voice-lab.sh"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(_SCRIPT), *args], capture_output=True, text=True, check=False, timeout=30)


class VoiceLabArgsTest(unittest.TestCase):
    def test_no_args_prints_usage(self) -> None:
        proc = _run()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("voice-lab.sh", proc.stderr)

    def test_rejects_bad_values_before_touching_adb(self) -> None:
        cases = [
            ("--avd", "../x", "--probe", "tts"),
            ("--avd", "hc api36", "--probe", "tts"),
            ("--avd", "hc-api36", "--probe", "mic"),
            ("--avd", "hc-api36", "--probe", "stt", "--set", "real"),
            ("--avd", "hc-api36", "--probe", "tts", "--runs", "1;rm"),
            ("--avd", "hc-api36", "--probe", "tts", "--nope"),
            # giọng người thật không được qua bộ nhận dạng mạng nếu chưa xác nhận
            ("--avd", "hc-api36", "--probe", "stt", "--set", "team", "--allow-network"),
        ]
        for args in cases:
            with self.subTest(args=args):
                proc = _run(*args)
                self.assertEqual(proc.returncode, 2, proc.stderr)


if __name__ == "__main__":
    unittest.main()
