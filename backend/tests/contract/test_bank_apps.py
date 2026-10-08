"""Hợp đồng data/bank_apps.vn.json (luật R1 + <queries> trên máy). Dùng chung với Android (P1-S1/S2)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "bank_apps.vn.json"
SCHEMA = ROOT / "docs" / "schemas" / "bank_apps.v1.json"

pytestmark = pytest.mark.skipif(not DATA.exists(), reason="data/bank_apps.vn.json chưa có (P1-S1 seed)")


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_matches_schema(data: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = [e.message for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data)]
    assert errors == []


def test_packages_unique_and_demo_present(data: dict) -> None:
    packages = [a["package"] for a in data["apps"]]
    assert len(packages) == len(set(packages)), "package trùng lặp"
    assert "vn.hoicon.demobank" in packages, "thiếu app demo cho máy ảo/gian trưng bày"


def test_real_apps_have_play_url(data: dict) -> None:
    for app in data["apps"]:
        if not app.get("demo"):
            assert app.get("play_url", "").endswith(f"id={app['package']}"), app["package"]


def test_covers_state_owned_banks(data: dict) -> None:
    """Người cao tuổi (nhất là nông thôn) dùng nhiều nhất 4 ngân hàng quốc doanh."""
    orgs = " ".join(a.get("org", "") + " " + a["name"] for a in data["apps"]).lower()
    for bank in ("vietcombank", "vietinbank", "bidv", "agribank"):
        assert bank in orgs, f"thiếu {bank}"
