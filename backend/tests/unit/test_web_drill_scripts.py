"""Spec 028 T021: danh sách kịch bản trong web (`apps/web/src/lib/drills.ts`) trùng `data/drills/*.yaml` (id + tên)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def test_web_drill_scripts_match_data() -> None:
    web = dict(
        re.findall(
            r'\{ id: "(drill_[a-z0-9_]+)", title: "([^"]+)" \}',
            (ROOT / "apps/web/src/lib/drills.ts").read_text("utf-8"),
        )
    )
    data = {}
    for path in sorted((ROOT / "data" / "drills").glob("*.yaml")):
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        data[doc["id"]] = doc["title"]
    assert web == data
