"""Suite eval `full` (spec 036, FR-002/FR-004): thành phần đạt Gate M3 và cassette trên đĩa trùng đầu ra của bộ sinh.

Chỉ đọc tệp, không cần DB."""

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

from hoicon.eval import cassettes
from hoicon.eval.cases import EVAL_DIR, ROOT, SCENARIOS_DIR, find_cassette, load_case, load_suite, plan_trigger

FULL = json.loads((EVAL_DIR / "suites" / "full.v1.json").read_text(encoding="utf-8"))
SMOKE = json.loads((EVAL_DIR / "suites" / "smoke.v1.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "docs" / "schemas" / "eval_cassette.v1.json").read_text(encoding="utf-8"))
IDS: list[str] = FULL["cases"]
BEHAVIORS: dict[str, str] = FULL["behaviors"]
ADVERSARIAL_KINDS = (
    "lower", "leak_phone", "leak_link", "obey_injection", "refusal", "timeout", "malformed", "missing"
)  # fmt: skip


@pytest.fixture(scope="module")
def cases() -> list:
    return [load_case(case_id) for case_id in IDS]


def test_suite_has_at_least_100_unique_cases_that_include_smoke() -> None:
    assert len(IDS) >= 100
    assert len(set(IDS)) == len(IDS)
    assert set(SMOKE["cases"]) <= set(IDS)
    assert IDS[: len(SMOKE["cases"])] == SMOKE["cases"], "20 ca smoke chạy trước, đúng thứ tự smoke"
    assert all((SCENARIOS_DIR / f"{i}.yaml").is_file() for i in IDS)


def test_composition_meets_gate_m3(cases: list) -> None:
    benign = [c for c in cases if c.is_benign]
    assert len(benign) / len(cases) >= 0.30
    assert sum(c.injection for c in cases) >= 10
    assert {c.region for c in cases} == {"north", "central", "south"}
    ids = set(IDS)
    twins = {c.id: _twin_of(c.id) for c in benign}  # ca hợp lệ "song sinh": ca lừa đảo gần giống nằm trong suite
    assert all(t in ids and not load_case(t).is_benign for t in twins.values()), twins
    assert sum(plan_trigger(c.signals) is None for c in cases) >= 3, "ca không kích hoạt luật"
    assert sum(c.signals["caller_flag"] == "flagged" for c in cases) >= 3
    assert sum(c.signals["app_category"] == "sideloaded" for c in cases) >= 5
    assert sum(c.signals["app_category"] == "securities" for c in cases) >= 3


def _twin_of(case_id: str) -> str:
    return yaml.safe_load((SCENARIOS_DIR / f"{case_id}.yaml").read_text(encoding="utf-8"))["twin_of"]


def test_every_case_has_a_valid_cassette() -> None:
    validator = Draft202012Validator(SCHEMA)
    for case_id in IDS:
        path = find_cassette(case_id, "full")
        doc = json.loads(path.read_text(encoding="utf-8"))
        errors = [e.message for e in validator.iter_errors(doc)]
        assert errors == [], (case_id, errors)
        assert doc["case_id"] == case_id
        assert doc["source"] == "synthetic"


def test_behaviors_cover_every_adversarial_kind_and_at_least_a_quarter_of_cases() -> None:
    smoke = set(SMOKE["cases"])
    assert set(BEHAVIORS) <= set(IDS) - smoke, "ca smoke dùng cassette viết tay"
    assert set(BEHAVIORS.values()) <= set(cassettes.KINDS)
    for kind in ADVERSARIAL_KINDS:
        assert list(BEHAVIORS.values()).count(kind) >= 2, kind
    non_honest = 0
    for case_id in IDS:
        doc = json.loads(find_cassette(case_id, "full").read_text(encoding="utf-8"))
        non_honest += doc["behavior"] != "honest"
    assert non_honest / len(IDS) >= 0.25


def test_injection_cases_are_obeyed_by_the_replayed_llm_and_no_incident_cases_stay_honest(cases: list) -> None:
    smoke = set(SMOKE["cases"])
    for c in cases:
        if c.id in smoke:
            continue
        kind = BEHAVIORS.get(c.id, "honest")
        if c.injection:
            assert kind == "obey_injection" and FULL["markers"].get(c.id), c.id
        else:
            assert kind != "obey_injection", c.id
        if plan_trigger(c.signals) is None:
            assert kind == "honest", f"{c.id}: không có sự cố thì không có lời gọi LLM để làm đối kháng"
    assert set(FULL["markers"]) <= set(BEHAVIORS)


def test_cassettes_on_disk_are_exactly_what_the_generator_produces() -> None:
    generated = cassettes.generate_all()
    on_disk = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in cassettes.FULL_DIR.glob("*.json")}
    assert set(on_disk) == set(generated), "tệp thừa/thiếu trong cassettes/full"
    for case_id, doc in generated.items():
        assert on_disk[case_id] == doc, f"{case_id}: chạy `python -m hoicon.eval.cassettes write` rồi xem diff"


def test_loader_serves_the_same_suite_as_the_file() -> None:
    assert [c.id for c in load_suite("full")] == IDS
    assert [c.id for c in load_suite("injection")] == [i for i in IDS if load_case(i).injection]
    assert Path(find_cassette(SMOKE["cases"][0], "full")).parent.name == "smoke"
