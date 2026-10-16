#!/usr/bin/env python3
"""Kiểm truy vết Spec Kit của HỏiCon — chống "xong trên giấy" (docs/MASTER-PLAN.md §2.6).

    python3 scripts/check-spec-trace.py [--root PATH]

Luật:
  1. Mỗi thư mục specs/NNN-slug phải có trong danh mục docs/MASTER-PLAN.md (số được cấp trước, không tự đặt).
  2. Mỗi link `specs/NNN-slug` trong docs/ROADMAP.md phải trỏ tới thư mục có thật.
  3. Khi có tasks.md: mọi FR-xxx định nghĩa trong spec.md phải xuất hiện trong tasks.md.
  4. tasks.md đã tick hết ⇒ có evidence.md thật (không còn chỗ trống mẫu; mỗi SC-xxx có dòng bảng điền đủ).
  5. Dòng ROADMAP đánh ☑ có link spec ⇒ spec đó đã tick hết tasks và có evidence.md.
Thoát 1 nếu có lỗi. Chỉ đọc file, không ghi gì.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPEC_DIR = re.compile(r"^\d{3}-[a-z0-9-]+$")
CATALOG_ENTRY = re.compile(r"\*\*(\d{3}-[a-z0-9-]+)\*\*")
ROADMAP_LINK = re.compile(r"specs/(\d{3}-[a-z0-9-]+)")
# `**FR-001**` (mẫu Spec Kit) hoặc `**(FR-001)**` (spec 021–025): bỏ sót dạng có ngoặc ⇒ luật 3/4 chạy rỗng.
FR_DEF = re.compile(r"\*\*\(?(FR-\d{3})\)?\*\*")
SC_DEF = re.compile(r"\*\*\(?(SC-\d{3})\)?\*\*")
TASK = re.compile(r"^\s*- \[([ xX])\] T\d+", re.M)
EVIDENCE_PLACEHOLDERS = ("[FEATURE NAME]", "[DATE]", "[P2-xx]")


def task_state(tasks_md: Path) -> tuple[int, int]:
    """(tổng số task, số task đã tick)."""
    marks = TASK.findall(tasks_md.read_text(encoding="utf-8"))
    return len(marks), sum(1 for m in marks if m.lower() == "x")


def evidence_problems(spec: Path) -> list[str]:
    """Rỗng nếu evidence.md thật: không còn chỗ trống của mẫu, mọi SC-xxx của spec có dòng bảng điền đủ."""
    ev = spec / "evidence.md"
    if not ev.is_file():
        return ["thiếu evidence.md"]
    text = ev.read_text(encoding="utf-8")
    problems = [f"evidence.md còn chỗ trống mẫu {p}" for p in EVIDENCE_PLACEHOLDERS if p in text]
    spec_md = spec / "spec.md"
    for sc in sorted(set(SC_DEF.findall(spec_md.read_text(encoding="utf-8")))) if spec_md.is_file() else []:
        rows = [ln for ln in text.splitlines() if ln.lstrip().startswith(f"| {sc} ")]
        if not any(all(c.strip() for c in row.strip().strip("|").split("|")) for row in rows):
            problems.append(f"evidence.md chưa có số đo cho {sc} (dòng bảng phải điền đủ mọi cột)")
    return problems


def find_specs(root: Path) -> dict[str, Path]:
    specs = root / "specs"
    if not specs.is_dir():
        return {}
    return {d.name: d for d in specs.iterdir() if d.is_dir() and SPEC_DIR.match(d.name)}


def check(root: Path) -> list[str]:
    errors: list[str] = []
    plan = root / "docs" / "MASTER-PLAN.md"
    roadmap = root / "docs" / "ROADMAP.md"
    if not plan.is_file():
        return [f"thiếu {plan.relative_to(root)}"]
    catalog = set(CATALOG_ENTRY.findall(plan.read_text(encoding="utf-8")))
    spec_dirs = find_specs(root)

    for name in sorted(spec_dirs.keys() - catalog):
        errors.append(f"specs/{name}: không có trong danh mục docs/MASTER-PLAN.md §3 (số spec phải được cấp trước)")

    done_rows: set[str] = set()
    if roadmap.is_file():
        for line in roadmap.read_text(encoding="utf-8").splitlines():
            for name in ROADMAP_LINK.findall(line):
                if name not in spec_dirs:
                    errors.append(f"docs/ROADMAP.md trỏ tới specs/{name} nhưng thư mục không tồn tại")
                elif "☑" in line:
                    done_rows.add(name)

    for name, d in sorted(spec_dirs.items()):
        spec_md, tasks_md = d / "spec.md", d / "tasks.md"
        if not tasks_md.is_file():
            if name in done_rows:
                errors.append(f"specs/{name}: ROADMAP đánh ☑ nhưng chưa có tasks.md")
            continue
        if spec_md.is_file():
            tasks_text = tasks_md.read_text(encoding="utf-8")
            for fr in sorted(set(FR_DEF.findall(spec_md.read_text(encoding="utf-8")))):
                if fr not in tasks_text:
                    errors.append(f"specs/{name}: {fr} không có task nào đáp ứng trong tasks.md")
        total, ticked = task_state(tasks_md)
        all_done = total > 0 and ticked == total
        ev_problems = evidence_problems(d) if all_done or name in done_rows else []
        if all_done:
            errors.extend(f"specs/{name}: tasks đã tick hết ({total}) nhưng {p}" for p in ev_problems)
        if name in done_rows and not (all_done and not ev_problems):
            errors.append(f"specs/{name}: ROADMAP đánh ☑ nhưng tasks chưa xong ({ticked}/{total}) hoặc thiếu evidence")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    root = ap.parse_args().root.resolve()
    errors = check(root)
    for e in errors:
        print(f"LỖI  {e}")
    print(f"check-spec-trace: {len(find_specs(root))} spec, {len(errors)} lỗi")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
