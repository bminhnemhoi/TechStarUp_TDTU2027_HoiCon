"""Kiểm tra scripts/check-baseline-profile.py (spec 012 T021, plan D13) — python3 -m unittest scripts/tests/test_check_baseline_profile.py"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / "scripts" / "check-baseline-profile.py"

_MAPPING = """\
# compiler: R8
vn.hoicon.sentinel.sensing.CallScreen -> a.a:
    int x -> a
vn.hoicon.sentinel.pause.PauseController -> a.b:
vn.hoicon.sentinel.ui.SafePauseScreenKt -> a.c:
"""


def _run(profile: str, mapping: str = _MAPPING) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmp:
        p, m = Path(tmp, "baseline-prof.txt"), Path(tmp, "mapping.txt")
        p.write_text(profile, encoding="utf-8")
        m.write_text(mapping, encoding="utf-8")
        return subprocess.run([sys.executable, str(_SCRIPT), str(p), "--mapping", str(m)], capture_output=True, text=True, check=False)


class CheckBaselineProfileTest(unittest.TestCase):
    def test_every_pattern_matching_a_class_exits_0(self) -> None:
        r = _run("# c\nHSPLvn/hoicon/sentinel/sensing/**;->**(**)**\nLvn/hoicon/sentinel/pause/**;\nHSPLvn/hoicon/sentinel/ui/SafePauseScreen**;->**(**)**\n")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_pattern_with_no_class_exits_1_and_names_the_line(self) -> None:
        r = _run("Lvn/hoicon/sentinel/pause/**;\nHSPLvn/hoicon/sentinel/renamed/**;->**(**)**\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("renamed", r.stdout + r.stderr)
        self.assertIn("dòng 2", r.stdout + r.stderr)

    def test_star_does_not_cross_package_but_double_star_does(self) -> None:
        self.assertEqual(_run("Lvn/hoicon/sentinel/*;\n").returncode, 1)
        self.assertEqual(_run("Lvn/hoicon/**;\n").returncode, 0)

    def test_missing_or_empty_class_list_is_unavailable_not_pass(self) -> None:
        self.assertEqual(_run("Lvn/hoicon/**;\n", mapping="# none\n").returncode, 2)


if __name__ == "__main__":
    unittest.main()
