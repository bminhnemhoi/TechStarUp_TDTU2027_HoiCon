"""Test cho scripts/check-spec-trace.py — chạy: python3 -m unittest discover -s scripts/tests"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "check-spec-trace.py"
_spec = importlib.util.spec_from_file_location("check_spec_trace", _SCRIPT)
if _spec is None or _spec.loader is None:
    raise ImportError(_SCRIPT)
cst = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cst)

PLAN = "| **001-demo-feature** | x |\n| **002-other** | y |\n"
SPEC = "- **FR-001**: System MUST a\n- **FR-002**: System MUST b\n- **SC-001**: p95 ≤ 3 s\n"
EVIDENCE = "# Bằng chứng nghiệm thu: Demo\n\n" + "| SC-001 | p95 ≤ 3 s | 1,2 s | AVD api36, n=10 | Đạt | log |\n" * 5


class CheckSpecTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "MASTER-PLAN.md").write_text(PLAN, encoding="utf-8")
        roadmap = "| P2-05 | Lính gác | ◐ specs/001-demo-feature |\n"
        (self.root / "docs" / "ROADMAP.md").write_text(roadmap, encoding="utf-8")
        self.spec = self.root / "specs" / "001-demo-feature"
        self.spec.mkdir(parents=True)
        (self.spec / "spec.md").write_text(SPEC, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_tasks(self, *lines: str) -> None:
        (self.spec / "tasks.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_spec_without_tasks_is_ok(self) -> None:
        self.assertEqual(cst.check(self.root), [])

    def test_uncatalogued_spec_dir_fails(self) -> None:
        (self.root / "specs" / "099-rogue").mkdir()
        self.assertTrue(any("099-rogue" in e and "danh mục" in e for e in cst.check(self.root)))

    def test_roadmap_link_to_missing_dir_fails(self) -> None:
        (self.root / "docs" / "ROADMAP.md").write_text("| x | specs/002-other ☐ |\n", encoding="utf-8")
        self.assertTrue(any("002-other" in e for e in cst.check(self.root)))

    def test_fr_not_covered_by_any_task_fails(self) -> None:
        self.write_tasks("- [ ] T001 [US1] do a — FR-001 · Verify: `pytest`")
        errors = cst.check(self.root)
        self.assertEqual(len(errors), 1)
        self.assertIn("FR-002", errors[0])

    def test_all_tasks_done_requires_real_evidence(self) -> None:
        self.write_tasks("- [x] T001 a — FR-001", "- [X] T002 b — FR-002")
        self.assertTrue(any("evidence.md" in e for e in cst.check(self.root)))
        (self.spec / "evidence.md").write_text("# Bằng chứng nghiệm thu: [FEATURE NAME]\n" + EVIDENCE, encoding="utf-8")
        self.assertTrue(any("evidence.md" in e for e in cst.check(self.root)), "placeholder mẫu phải bị bắt")
        (self.spec / "evidence.md").write_text(EVIDENCE, encoding="utf-8")
        self.assertEqual(cst.check(self.root), [])

    def test_evidence_with_empty_sc_row_fails(self) -> None:
        self.write_tasks("- [x] T001 a — FR-001", "- [x] T002 b — FR-002")
        filled_header = "# Bằng chứng nghiệm thu: Demo\n\n" + "Ghi chú dài cho đủ độ dài. " * 20 + "\n"
        (self.spec / "evidence.md").write_text(filled_header + "| SC-001 | | | | | |\n", encoding="utf-8")
        self.assertTrue(any("SC-001" in e for e in cst.check(self.root)), "dòng SC để trống phải bị bắt")

    def test_roadmap_done_with_open_tasks_fails(self) -> None:
        self.write_tasks("- [x] T001 a — FR-001", "- [ ] T002 b — FR-002")
        (self.root / "docs" / "ROADMAP.md").write_text("| P2-05 | ☑ specs/001-demo-feature |\n", encoding="utf-8")
        self.assertTrue(any("☑" in e and "1/2" in e for e in cst.check(self.root)))

    def test_missing_master_plan_fails(self) -> None:
        (self.root / "docs" / "MASTER-PLAN.md").unlink()
        self.assertEqual(cst.check(self.root), ["thiếu docs/MASTER-PLAN.md"])


if __name__ == "__main__":
    unittest.main()
