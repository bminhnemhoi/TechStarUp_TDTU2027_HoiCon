#!/usr/bin/env python3
"""Kiểm hồ sơ khởi động viết tay không "chết" (spec 012 T021, plan D13).

  scripts/check-baseline-profile.py <baseline-prof.txt> (--mapping mapping.txt | --classes classes.tsv)

Mỗi mẫu lớp trong hồ sơ (dòng `[HSP]*L…;` hoặc `[HSP]*L…;->…`) phải khớp ≥ 1 lớp thật. Nguồn danh sách lớp:
`--mapping` = mapping.txt của R8 (tên gốc trước dấu `->`), `--classes` = đầu ra `apkanalyzer dex packages --defined-only`
của APK chưa rút gọn (hoặc mỗi dòng một tên lớp). Đổi tên gói/lớp mà quên sửa hồ sơ ⇒ thoát 1 nêu dòng.
Thoát: 0 đạt · 1 có mẫu không khớp · 2 dùng sai / không có danh sách lớp (không bao giờ tính là đạt).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_RULE = re.compile(r"^[HSP]*(L[^;]*;)")
_MAPPING_CLASS = re.compile(r"^(\S+) -> \S+:$")


def _glob(pattern: str) -> re.Pattern[str]:
    """Quy tắc của profgen: `**` khớp mọi ký tự (kể cả `/`), `*` khớp mọi ký tự trừ `/`."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _descriptor(name: str) -> str:
    return "L" + name.replace(".", "/") + ";"


def _classes(path: Path, kind: str) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if kind == "mapping":
            m = _MAPPING_CLASS.match(line)
            if m:
                names.append(m.group(1))
        else:  # apkanalyzer tsv ("C <tab> … <tab> tên") hoặc mỗi dòng một tên
            fields = line.split("\t")
            if fields[0] == "C" or len(fields) == 1 and line.strip() and not line.startswith("#"):
                names.append(fields[-1].strip())
    return [_descriptor(n) for n in names if n]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("profile", type=Path)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--mapping", type=Path)
    src.add_argument("--classes", type=Path)
    args = ap.parse_args(argv)
    path, kind = (args.mapping, "mapping") if args.mapping else (args.classes, "classes")
    for f in (args.profile, path):
        if not f.is_file():
            print(f"UNAVAILABLE: không thấy tệp {f}", file=sys.stderr)
            return 2
    classes = _classes(path, kind)
    if not classes:
        print(f"UNAVAILABLE: {path} không có lớp nào — không thể kết luận hồ sơ còn khớp", file=sys.stderr)
        return 2
    dead = []
    rules = 0
    for n, line in enumerate(args.profile.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _RULE.match(line)
        if not m:
            continue
        rules += 1
        rx = _glob(m.group(1))
        if not any(rx.match(c) for c in classes):
            dead.append((n, line))
    for n, line in dead:
        print(f"[TRƯỢT] dòng {n}: không khớp lớp nào trong {len(classes)} lớp: {line}")
    if dead:
        return 1
    print(f"[ĐẠT] {rules} mẫu hồ sơ khởi động, mỗi mẫu khớp ≥ 1 lớp (trong {len(classes)} lớp)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
