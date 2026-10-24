"""Kịch bản máy ảo tại gian (spec 050 T014): mỗi mục danh sách phát của /booth có một cảnh trên máy ảo — python3 -m unittest scripts/tests/test_emu_scenario_booth.py"""

from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("emu_scenario", _ROOT / "scripts" / "emu-scenario.py")
emu = importlib.util.module_from_spec(_SPEC)
sys.modules["emu_scenario"] = emu  # dataclass tra module theo tên
_SPEC.loader.exec_module(emu)  # type: ignore[union-attr]


def _playlist_ids() -> list[str]:
    ts = (_ROOT / "apps" / "web" / "src" / "lib" / "booth.ts").read_text(encoding="utf-8")
    block = ts[ts.index("export const PLAYLIST") :]
    return re.findall(r'scenarioId:\s*"([a-z0-9_]+)"', block.split("];", 1)[0])


class BoothScenesTest(unittest.TestCase):
    def test_every_booth_playlist_item_has_a_scene(self) -> None:
        ids = _playlist_ids()
        self.assertGreaterEqual(len(ids), 3)
        self.assertEqual(sorted(set(ids) - set(emu.BOOTH_SCENES)), [])

    def test_scenes_only_use_registered_fictional_numbers(self) -> None:
        for name, scene in emu.BOOTH_SCENES.items():
            self.assertIn(scene.caller, emu.PHONES, name)
            self.assertTrue(emu.PHONES[scene.caller].startswith("0900"), name)  # dải số hư cấu của fixture

    def test_a_legitimate_call_expects_no_pause_and_scams_expect_one(self) -> None:
        self.assertFalse(emu.BOOTH_SCENES["benign_family_son_rent_002"].expect_pause)
        self.assertTrue(emu.BOOTH_SCENES["fake_police_safe_account_002"].expect_pause)

    def test_resolving_all_gives_playlist_order_and_unknown_name_is_rejected(self) -> None:
        self.assertEqual(emu.booth_plan("all"), _playlist_ids())
        with self.assertRaises(ValueError):
            emu.booth_plan("khong_co")


if __name__ == "__main__":
    unittest.main()
