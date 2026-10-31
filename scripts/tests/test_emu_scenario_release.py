"""Đo E7 ≤ 3 s trên bản release/demo (spec 010 T031): bản này không có mốc HC_TIMING nên đo bằng Activity đang hiện — python3 -m unittest scripts/tests/test_emu_scenario_release.py"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("emu_scenario_rel", _ROOT / "scripts" / "emu-scenario.py")
emu = importlib.util.module_from_spec(_SPEC)
sys.modules["emu_scenario_rel"] = emu
_SPEC.loader.exec_module(emu)  # type: ignore[union-attr]

_PAUSE = "  ResumedActivity: ActivityRecord{1a2b u0 vn.hoicon.sentinel.demo/vn.hoicon.sentinel.pause.SafePauseActivity t9}"
_BANK = "  ResumedActivity: ActivityRecord{1a2b u0 vn.hoicon.demobank/.MainActivity t8}"


class ResumedPauseTest(unittest.TestCase):
    def test_recognises_the_safe_pause_of_the_given_package_only(self) -> None:
        self.assertTrue(emu.resumed_is_pause(_PAUSE, "vn.hoicon.sentinel.demo"))
        self.assertFalse(emu.resumed_is_pause(_PAUSE, "vn.hoicon.sentinel"))  # bản debug không được tính cho bản demo
        self.assertFalse(emu.resumed_is_pause(_BANK, "vn.hoicon.sentinel.demo"))
        self.assertFalse(emu.resumed_is_pause("", "vn.hoicon.sentinel.demo"))

    def test_summary_keeps_the_cold_first_run_apart_from_the_pooled_p95(self) -> None:
        text = emu.pause_release_summary([3500, 900, 1000, 1100, 800])
        self.assertIn("lượt đầu 3500 ms", text)
        self.assertIn("p95 gộp 3500 ms", text)
        self.assertIn("TRƯỢT", text)  # lượt nguội > 3000 ms không bị bỏ khỏi ngưỡng
        self.assertIn("ĐẠT", emu.pause_release_summary([900, 1000]))


if __name__ == "__main__":
    unittest.main()


class RoleHolderTest(unittest.TestCase):
    def test_a_package_that_only_shares_the_prefix_is_not_the_holder(self) -> None:
        # `vn.hoicon.sentinel` là tiền tố của `vn.hoicon.sentinel.demo`: kiểm bằng "in" từng báo nhầm là đã giữ vai trò.
        self.assertTrue(emu.holds_role("vn.hoicon.sentinel.demo\n", "vn.hoicon.sentinel.demo"))
        self.assertFalse(emu.holds_role("vn.hoicon.sentinel.demo\n", "vn.hoicon.sentinel"))
        self.assertFalse(emu.holds_role("vn.hoicon.sentinel\n", "vn.hoicon.sentinel.demo"))
        self.assertTrue(emu.holds_role("com.x\nvn.hoicon.sentinel\n", "vn.hoicon.sentinel"))
        self.assertFalse(emu.holds_role("", "vn.hoicon.sentinel"))


class AnswerAfterTelecomSettlesTest(unittest.TestCase):
    def test_every_answer_waits_for_telecom_to_build_the_incoming_call(self) -> None:
        # Nhấc máy ngay khi telephony.registry báo đổ chuông ⇒ Telecom ghi MISSED "Found no ringing call" (hc-api34, 25/10/2026).
        self.assertGreaterEqual(emu.CALL_SETTLE_S, 1.0)
        lines = (_ROOT / "scripts" / "emu-scenario.py").read_text(encoding="utf-8").splitlines()
        answers = [i for i, line in enumerate(lines) if 'adb("emu", "gsm", "accept"' in line]
        self.assertGreaterEqual(len(answers), 4)
        for i in answers:
            self.assertIn("CALL_SETTLE_S", lines[i - 1] + lines[i - 2], f"dòng {i + 1}: nhấc máy không chờ Telecom")
