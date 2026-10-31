"""Bộ chuyển kịch bản → RiskEvent tất định (spec 030, FR-002/FR-003): bảng ánh xạ theo ADR-001 + RiskEngine R0/R1/R2."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from hoicon.agents.spike import DEMO_H1
from hoicon.domain.events import RiskEvent
from hoicon.domain.risk import RiskLevel
from hoicon.eval.cases import (
    SCENARIOS_DIR,
    SMOKE_SUITE,
    Case,
    build_event,
    elder_reply,
    incident_id,
    load_suite,
    plan_trigger,
)

ROOT = Path(__file__).resolve().parents[3]
H1_VECTORS = json.loads((ROOT / "docs/schemas/fixtures/h1_vectors.json").read_text(encoding="utf-8"))["vectors"]


def signals(caller: str, app: str, bucket: str = "1_5m", in_call: bool = True) -> dict:
    return {"caller_flag": caller, "in_call": in_call, "duration_bucket": bucket, "app_category": app}


@pytest.fixture(scope="module")
def suite() -> list[Case]:
    return load_suite("smoke")


def by_id(suite: list[Case], case_id: str) -> Case:
    return next(c for c in suite if c.id == case_id)


# --- Suite (FR-002) --------------------------------------------------------------------------------------------------


def test_suite_has_exactly_20_unique_existing_scenarios(suite: list[Case]) -> None:
    ids = [c.id for c in suite]
    assert len(ids) == 20 and len(set(ids)) == 20
    assert all((SCENARIOS_DIR / f"{i}.yaml").is_file() for i in ids)
    assert json.loads(SMOKE_SUITE.read_text(encoding="utf-8"))["cases"] == ids  # thứ tự trong file = thứ tự chạy


def test_suite_composition_meets_fr_002(suite: list[Case]) -> None:
    benign = [c for c in suite if c.is_benign]
    assert len(benign) >= 6 and len(benign) / len(suite) >= 0.30
    assert sum(c.injection for c in suite) >= 4
    assert sum(c.signals["caller_flag"] == "flagged" for c in suite) >= 1
    assert sum(c.signals["app_category"] == "sideloaded" for c in suite) >= 2
    assert sum(plan_trigger(c.signals) is None for c in suite) >= 1  # ít nhất một ca không kích hoạt luật
    assert {c.region for c in suite} == {"north", "central", "south"}


def test_every_scam_case_opens_an_incident_and_every_thread_id_fits(suite: list[Case]) -> None:
    for case in suite:
        if not case.is_benign:
            assert plan_trigger(case.signals) is not None, case.id  # ca lừa đảo không sự cố ⇒ recall vô nghĩa
        assert len(incident_id("0123abcd", case.id)) <= 64, case.id  # agent_runs.thread_id là String(64)


def test_incident_id_is_prefixed_and_unique_per_nonce() -> None:
    a, b = incident_id("aaaaaaaa", "fake_police_drug_ring_001"), incident_id("bbbbbbbb", "fake_police_drug_ring_001")
    assert a.startswith("eval-") and a != b and "fake_police_drug_ring_001" in a


# --- Bảng ánh xạ (FR-003) ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sig", "expected"),
    [
        (signals("trusted", "bank", "gt_15m"), None),  # R0: số tin cậy ⇒ không sự cố
        (signals("trusted", "sideloaded"), None),  # R0 thắng mọi thứ
        (signals("unknown", "none"), None),  # không mở app tài chính
        (signals("flagged", "none"), None),
        (signals("unknown", "bank", "lt_1m"), ("R1", RiskLevel.HIGH)),
        (signals("unknown", "wallet", "1_5m"), ("R1", RiskLevel.HIGH)),
        (signals("unknown", "securities", "1_5m"), ("R1", RiskLevel.HIGH)),
        (signals("unknown", "bank", "5_15m"), ("R1", RiskLevel.CRITICAL)),
        (signals("unknown", "bank", "gt_15m"), ("R1", RiskLevel.CRITICAL)),
        (signals("flagged", "bank", "lt_1m"), ("R1", RiskLevel.CRITICAL)),
        (signals("flagged", "wallet", "1_5m", in_call=False), ("R1", RiskLevel.CRITICAL)),
        (signals("unknown", "sideloaded", "1_5m"), ("R2", RiskLevel.CRITICAL)),
        (signals("flagged", "sideloaded", "lt_1m"), ("R2", RiskLevel.CRITICAL)),
    ],
)
def test_trigger_table(sig: dict, expected: tuple[str, RiskLevel] | None) -> None:
    assert plan_trigger(sig) == expected


def test_event_for_flagged_bank_case_matches_the_device_contract(suite: list[Case]) -> None:
    case = by_id(suite, "fake_bank_card_locked_002")
    event = build_event(case)
    assert isinstance(event, RiskEvent)
    assert event.rule_id == "R1" and event.rule_floor is RiskLevel.CRITICAL and event.type == "banking_app_foreground"
    assert event.caller.h1 == DEMO_H1 and event.caller.flagged and not event.caller.in_contacts
    assert event.call.active is True and event.call.duration_s == 180 and event.call.direction == "incoming"
    assert event.app.category == "bank" and event.is_drill is False


def test_event_for_just_ended_call_and_sideloaded_app(suite: list[Case]) -> None:
    ended = build_event(by_id(suite, "benign_family_vegetables_001"))
    assert ended.call.active is False and ended.call.since_end_s == 60 and ended.call.duration_s == 30
    sideloaded = build_event(by_id(suite, "fake_tax_refund_app_002"))
    assert sideloaded.rule_id == "R2" and sideloaded.rule_floor is RiskLevel.CRITICAL
    assert sideloaded.type == "sideload_detected" and sideloaded.app.category == "sideloaded"
    assert sideloaded.call.duration_s == 600


def test_no_trigger_case_has_no_event(suite: list[Case]) -> None:
    assert build_event(by_id(suite, "benign_official_tax_reminder_001")) is None


def test_unknown_caller_h1_comes_from_the_fictional_fixture(suite: list[Case]) -> None:
    event = build_event(by_id(suite, "fake_police_drug_ring_001"))
    vector = next(v for v in H1_VECTORS if v["input"] == "0900000001")
    assert event.caller.h1 == vector["h1"] == hashlib.sha256(("hoicon:v1:" + vector["e164"]).encode()).hexdigest()
    assert event.caller.last3 == "001" and not event.caller.flagged


def test_events_are_deterministic(suite: list[Case]) -> None:
    for case in suite:
        first, second = build_event(case), build_event(case)
        assert first == second
        if first is not None:
            assert first.id == uuid.uuid5(uuid.NAMESPACE_URL, f"hoicon:eval:{case.id}")
            assert first.occurred_at == datetime(2026, 10, 15, 9, 0, tzinfo=UTC)  # không phụ thuộc giờ hệ thống


# --- Trả lời người cao tuổi (FR-005) ----------------------------------------------------------------------------------


def test_elder_replies_follow_the_question_and_default_to_unsure(suite: list[Case]) -> None:
    case = by_id(suite, "fake_police_safe_account_002")  # claims_authority/asks_transfer = yes, không có knows_caller
    assert elder_reply(case, "q_caller_authority", first=False) == {"answer": "yes"}
    assert elder_reply(case, "q_asked_transfer", first=False) == {"answer": "yes"}
    assert elder_reply(case, "q_know_caller", first=False) == {"answer": "unsure"}


def test_note_is_attached_only_to_the_first_reply(suite: list[Case]) -> None:
    injected = by_id(suite, "fake_bank_card_locked_002")
    assert injected.elder_note and elder_reply(injected, "q_know_caller", first=True)["note"] == injected.elder_note
    assert "note" not in elder_reply(injected, "q_know_caller", first=False)
    without_note = [c for c in suite if not c.elder_note]
    assert without_note, "suite cần ít nhất một ca không có lời kể để kiểm nhánh này"
    assert "note" not in elder_reply(without_note[0], "q_know_caller", first=True)


def test_case_secrets_cover_every_spelling_of_the_phone_number(suite: list[Case]) -> None:
    from hoicon.eval.cases import case_secrets

    found = case_secrets(by_id(suite, "fake_bank_card_locked_002"))  # số gắn cờ
    for spelling in ("0900000002", "+84900000002", "84900000002", "090 000 0002", "090.000.0002", "090-000-0002"):
        assert spelling in found, spelling
    assert DEMO_H1 in found and "vn.hoicon.demobank" in found


def test_every_injection_case_has_cassette_markers(suite: list[Case]) -> None:
    from hoicon.eval.cases import EVAL_DIR

    for case in suite:
        if case.injection:
            doc = json.loads((EVAL_DIR / "cassettes" / "smoke" / f"{case.id}.json").read_text(encoding="utf-8"))
            assert doc.get("injected_markers"), f"{case.id}: ca chèn lệnh phải có injected_markers"


# --- Suite full / injection (spec 036, FR-001/FR-002) ----------------------------------------------------------------


def test_full_suite_loads_in_file_order_and_extends_smoke() -> None:
    full = [c.id for c in load_suite("full")]
    assert len(full) >= 100 and len(set(full)) == len(full)
    assert full[:20] == [c.id for c in load_suite("smoke")]


def test_injection_suite_is_exactly_the_injection_cases_of_full() -> None:
    injection = load_suite("injection")
    assert len(injection) >= 10 and all(c.injection for c in injection)
    assert [c.id for c in injection] == [c.id for c in load_suite("full") if c.injection]


def test_find_cassette_prefers_the_generated_folder_then_smoke() -> None:
    from hoicon.eval.cases import find_cassette

    assert find_cassette("fake_bank_card_locked_002", "full").parent.name == "smoke"  # cassette viết tay của smoke
    assert find_cassette("fake_bank_transfer_error_007", "full").parent.name == "full"  # cassette sinh
    assert find_cassette("fake_bank_card_locked_002", "smoke").parent.name == "smoke"
    with pytest.raises(FileNotFoundError, match="fake_bank_transfer_error_007"):
        find_cassette("fake_bank_transfer_error_007", "smoke")  # smoke không nhìn vào thư mục full
    with pytest.raises(FileNotFoundError, match="khong_co_ca_nay_999"):
        find_cassette("khong_co_ca_nay_999", "full")


@pytest.mark.parametrize("bad", ["../../etc/passwd_001", "a/b_001", "FAKE_001", "fake_police", "x_01", ""])
def test_case_ids_must_match_the_scenario_contract_so_paths_cannot_escape(bad: str) -> None:
    from hoicon.eval.cases import find_cassette, load_case

    with pytest.raises(ValueError, match="id"):
        load_case(bad)
    with pytest.raises(ValueError, match="id"):
        find_cassette(bad, "full")
