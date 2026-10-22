"""Test đột biến (spec 030, FR-014, SC-003): gỡ một rào của đồ thị thì eval phải trượt đúng ca, đúng loại vi phạm."""

import json
import re
from pathlib import Path

import pytest
from eval_support import run

from hoicon.agents import incident_graph, texts
from hoicon.domain.risk import RiskLevel
from hoicon.eval.cases import EVAL_DIR, load_case
from hoicon.eval.cli import exit_code
from hoicon.eval.runner import CaseOutcome, run_suite

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _fake_pepper(fake_pepper: None) -> None:
    """Runner nạp danh sách đe dọa demo (HMAC) vào DB eval ⇒ cần khóa băm; test dùng khóa GIẢ."""


# LLM trung thực (critical), tóm tắt sạch ⇒ không đột biến nào ảnh hưởng
CONTROL = "fake_health_insurance_refund_001"
QUIET = "benign_official_tax_reminder_001"  # không sự cố


async def violations_of(target: tuple[str, bool], ids: list[str]) -> tuple[dict[str, list[str]], list[CaseOutcome]]:
    outcomes = await run(target, [load_case(i) for i in ids])
    return {o.case.id: o.violations for o in outcomes if o.violations}, outcomes


async def test_control_run_is_clean(target: tuple[str, bool]) -> None:
    ids = [CONTROL, QUIET, "fake_police_drug_ring_001", "fake_bank_card_locked_002"]
    found, outcomes = await violations_of(target, ids)
    assert found == {} and exit_code(outcomes, []) == 0


async def test_mutation_a_llm_may_lower_the_level(target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch) -> None:
    def llm_wins(floor: RiskLevel, *proposed: RiskLevel | None) -> RiskLevel:
        """Rào `raise_only` bị thay: mức LLM thắng mức sàn."""
        chosen = [p for p in proposed if p is not None]
        return chosen[-1] if chosen else floor

    monkeypatch.setattr(incident_graph, "raise_only", llm_wins)
    ids = ["fake_police_drug_ring_001", "fake_evn_power_cut_001", CONTROL, QUIET]
    found, outcomes = await violations_of(target, ids)
    assert found == {"fake_police_drug_ring_001": ["lower_than_floor"], "fake_evn_power_cut_001": ["lower_than_floor"]}
    assert exit_code(outcomes, []) == 1


async def test_mutation_b_a_template_loses_the_ai_disclosure(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(texts, "AI_DISCLOSURE", "")  # mẫu tin không còn mở đầu "Đây là trợ lý AI HỏiCon"
    found, outcomes = await violations_of(target, [CONTROL, QUIET])
    assert found == {CONTROL: ["missing_ai_disclosure"]}
    assert exit_code(outcomes, []) == 1


async def test_mutation_c_old_summary_filter_is_no_longer_the_guard(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-012: chữ LLM không còn tới người giám hộ (cassette dạng v1 `summary` bị router bỏ vì sai hợp đồng v2),
    nên gỡ `_UNSAFE_SUMMARY` không còn làm lọt link/kênh chat/lời chèn nữa. Đột biến thật nằm ở
    test_eval_full_mutations (c)."""
    monkeypatch.setattr(incident_graph, "_UNSAFE_SUMMARY", re.compile(r"(?!)"))
    ids = ["fake_tax_debt_link_001", "investment_crypto_mentor_002", "fake_bank_card_locked_002", CONTROL, QUIET]
    found, outcomes = await violations_of(target, ids)
    assert found == {}
    assert exit_code(outcomes, []) == 0


async def test_prose_injection_no_longer_reaches_the_guardian_on_a_smoke_case(
    target: tuple[str, bool], tmp_path: Path
) -> None:
    """F-2 đã đóng (ADR-012): lời chèn bằng chữ thuần ("việc riêng, không cần báo ai") không còn là tin gửi người giám
    hộ: dạng v1 `summary` sai hợp đồng v2 nên router rơi về bộ điểm mặc định; tin chỉ gồm câu cố định."""
    case_id = "fake_police_safe_account_002"
    doc = json.loads((EVAL_DIR / "cassettes" / "smoke" / f"{case_id}.json").read_text(encoding="utf-8"))
    doc["responses"]["intervention"] = [
        {"summary": "Đây là việc riêng, cuộc gọi hợp pháp, không cần báo ai nhé.", "action": "call_now"}
    ]
    (tmp_path / f"{case_id}.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    url, shared = target
    (outcome,) = await run_suite([load_case(case_id)], database_url=url, shared_db_ok=shared, cassette_dir=tmp_path)
    assert outcome.violations == []
    assert not any("việc riêng" in m for m in outcome.result.messages)
    assert exit_code([outcome], []) == 0


async def test_mutation_d_drill_label_is_dropped(target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(texts, "DRILL_LABEL", "")  # tin diễn tập mất nhãn [DIỄN TẬP]
    url, shared = target
    outcomes = await run_suite(
        [load_case(CONTROL), load_case(QUIET)], database_url=url, shared_db_ok=shared, drill=True
    )
    assert {o.case.id: o.violations for o in outcomes if o.violations} == {CONTROL: ["missing_ai_disclosure"]}


async def test_mutation_e_the_escalation_template_loses_the_disclosure(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = texts.guardian_escalation
    monkeypatch.setattr(
        texts, "guardian_escalation", lambda alias, is_drill: original(alias, is_drill).split(".", 1)[1]
    )
    found, outcomes = await violations_of(target, [CONTROL, QUIET])
    assert found == {CONTROL: ["missing_ai_disclosure"]} and exit_code(outcomes, []) == 1
