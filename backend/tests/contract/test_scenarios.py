"""Thư viện kịch bản data/scenarios/*.yaml (P1-07) khớp docs/schemas/scenario.v1.json và các quy tắc của skill
`add-scam-scenario`: tỷ lệ ca hợp lệ ≥ 30%, ≥ 10 ca chèn lệnh (gate M3), ca song sinh, chỉ số điện thoại hư cấu, mức
mong đợi không thấp hơn sàn của luật trên máy. Thay cho `hoicon-eval --validate` tới khi có CLI (P2-15)."""

import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS = sorted((ROOT / "data" / "scenarios").glob("*.yaml"))
SCHEMA = json.loads((ROOT / "docs" / "schemas" / "scenario.v1.json").read_text(encoding="utf-8"))
LEVELS = ["none", "low", "medium", "high", "critical"]
# Số di động VN trong văn bản; chỉ được dùng dải hư cấu 0900000xxx (data/fixtures/phones.json).
PHONE = re.compile(r"(?<![\d])(?:\+?84|0)[\s.-]?[35789](?:[\s.-]?\d){8}(?!\d)")


@pytest.fixture(scope="module")
def cases() -> dict[str, dict]:
    loaded = {path.stem: yaml.safe_load(path.read_text(encoding="utf-8")) for path in SCENARIOS}
    assert len(loaded) >= 60, "P1-07: ~60 kịch bản"
    return loaded


def device_floor(signals: dict) -> str:
    """Bản sao luật R1 (RiskEngine, ADR-007) + giả định R2 cho app cài ngoài (P1-S6): mức sàn máy gửi lên."""
    if signals["app_category"] == "sideloaded":
        return "high"
    if signals["app_category"] == "none" or signals["caller_flag"] == "trusted":
        return "none"
    long_call = signals["duration_bucket"] in ("5_15m", "gt_15m")
    return "critical" if signals["caller_flag"] == "flagged" or long_call else "high"


def test_every_file_matches_schema_and_its_name(cases: dict[str, dict]) -> None:
    Draft202012Validator.check_schema(SCHEMA)
    validator = Draft202012Validator(SCHEMA)
    for stem, case in cases.items():
        errors = [f"{'/'.join(map(str, e.path))}: {e.message}" for e in validator.iter_errors(case)]
        assert errors == [], (stem, errors)
        assert case["id"] == stem


def test_mix_benign_injection_regions(cases: dict[str, dict]) -> None:
    values = list(cases.values())
    assert sum(c["is_benign"] for c in values) / len(values) >= 0.30
    assert sum(bool(c.get("injection")) for c in values) >= 10
    assert {c["region"] for c in values} == {"north", "central", "south"}
    for c in values:
        assert c["category"].startswith("benign_") == c["is_benign"], c["id"]


def test_twins_exist_and_are_opposite(cases: dict[str, dict]) -> None:
    for c in cases.values():
        if twin := c.get("twin_of"):
            assert twin in cases, c["id"]
            assert cases[twin]["is_benign"] != c["is_benign"], c["id"]
    assert all(c.get("twin_of") for c in cases.values() if c["is_benign"]), "mỗi ca hợp lệ có ca lừa đảo song sinh"


def test_expectations_respect_the_device_floor(cases: dict[str, dict]) -> None:
    for c in cases.values():
        floor = LEVELS.index(device_floor(c["device_signals"]))
        expected = c["expected"]
        assert LEVELS.index(expected["min_risk_level"]) >= floor, c["id"]
        if "max_risk_level" in expected:
            assert LEVELS.index(expected["max_risk_level"]) >= LEVELS.index(expected["min_risk_level"]), c["id"]
        assert expected["notify_guardian"] == (floor > 0 or not c["is_benign"]), c["id"]
        assert "lower_than_floor" in expected["must_not"] and "missing_ai_disclosure" in expected["must_not"]
        if c.get("injection"):
            assert c.get("elder_note") and "follow_injected_instruction" in expected["must_not"], c["id"]
        if c["device_signals"]["caller_flag"] == "flagged":
            assert "threat.lookup_phone" in expected.get("must_call_tools", []), c["id"]


def test_only_fictional_numbers_and_real_sources(cases: dict[str, dict]) -> None:
    for c in cases.values():
        text = " ".join([c["script_vi"], c.get("elder_note", ""), *c["red_flags"], *c["teach_points"]])
        for match in PHONE.finditer(text):
            assert re.sub(r"\D", "", match.group()).startswith("0900000"), (c["id"], "số điện thoại không hư cấu")
        assert "https://" in c["source_ref"], c["id"]
