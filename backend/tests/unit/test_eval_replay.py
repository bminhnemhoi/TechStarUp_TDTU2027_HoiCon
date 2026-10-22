"""ReplayClient: phản hồi LLM ghi sẵn cắm vào LlmRouter thật (spec 030, FR-004)."""

import json
from decimal import Decimal
from typing import Any

import pytest

from hoicon.agents.incident_graph import GuardianBrief, RiskAssessment
from hoicon.agents.llm_router import LlmRouter, load_prompt
from hoicon.eval.replay import ReplayClient

RISK = {"level": "high", "tactic": "bank_security", "reasons": ["a"], "ask_question": "q_asked_transfer"}
BRIEF = {"points": ["unknown_call_then_finance_app", "common_scam_pattern"], "action": "call_now"}


def cassette(risk: list[dict] | None = None, brief: list[dict] | None = None) -> dict[str, Any]:
    return {
        "case_id": "fake_police_drug_ring_001",
        "source": "synthetic",
        "behavior": "honest",
        "prompt_versions": {"risk_scorer": "risk_scorer@1", "intervention": "intervention@2"},
        "responses": {"risk_scorer": risk or [], "intervention": brief or []},
    }


def router(client: ReplayClient) -> LlmRouter:
    return LlmRouter(client, "claude-haiku-5-5", Decimal(10))


async def ask_risk(r: LlmRouter, context: dict[str, Any] | None = None):
    fallback = RiskAssessment(level="medium", tactic="unknown", reasons=[], ask_question="none")
    return await r.structured(
        prompt=load_prompt("risk_scorer"), context=context or {"k": "v"}, output=RiskAssessment, fallback=fallback
    )


async def ask_brief(r: LlmRouter):
    fallback = GuardianBrief(points=["common_scam_pattern"], action="call_now")
    return await r.structured(
        prompt=load_prompt("intervention"), context={"k": "v"}, output=GuardianBrief, fallback=fallback
    )


async def test_outputs_come_back_in_order_per_node() -> None:
    second = {**RISK, "level": "critical", "ask_question": "none"}
    client = ReplayClient(cassette(risk=[RISK, second], brief=[BRIEF]))
    r = router(client)
    first_risk, brief, second_risk = await ask_risk(r), await ask_brief(r), await ask_risk(r)
    assert (first_risk.output.level, second_risk.output.level) == ("high", "critical")
    assert brief.output.points == BRIEF["points"]
    assert not any(x.fallback_used for x in (first_risk, brief, second_risk))
    assert first_risk.tokens_in > 0 and first_risk.cost_usd > 0  # có usage cố định để router tính chi phí


async def test_refusal_goes_through_the_router_as_fallback() -> None:
    client = ReplayClient(cassette(risk=[{"error": "refusal"}]))
    result = await ask_risk(router(client))
    assert result.fallback_used and result.error == "stop_refusal"
    assert result.output.level == "medium"  # đúng giá trị fallback do node đưa


async def test_timeout_raises_inside_and_router_falls_back() -> None:
    client = ReplayClient(cassette(risk=[{"error": "timeout"}]))
    result = await ask_risk(router(client))
    assert result.fallback_used and result.error == "TimeoutError"


async def test_malformed_output_falls_back() -> None:
    client = ReplayClient(cassette(risk=[{"error": "malformed"}]))
    result = await ask_risk(router(client))
    assert result.fallback_used and result.error == "stop_end_turn"


async def test_missing_and_exhausted_responses_fall_back() -> None:
    client = ReplayClient(cassette(risk=[{"error": "missing"}]))
    r = router(client)
    assert (await ask_risk(r)).fallback_used  # phản hồi 'missing'
    assert (await ask_risk(r)).fallback_used  # hết danh sách
    assert (await ask_brief(r)).fallback_used  # node không có phản hồi nào


async def test_invalid_structured_output_in_cassette_falls_back() -> None:
    client = ReplayClient(cassette(risk=[{**RISK, "level": "apocalyptic"}]))
    assert (await ask_risk(router(client))).fallback_used


async def test_records_what_was_sent_already_masked() -> None:
    client = ReplayClient(cassette(risk=[RISK]))
    await ask_risk(router(client), context={"note": "gọi lại 0900000001 ngay"})
    (call,) = client.calls
    assert call.node == "risk_scorer"
    sent = json.dumps(call.messages, ensure_ascii=False) + call.system
    assert "0900000001" not in sent and "[SĐT ***001]" in sent  # router che PII trước khi tới client
    assert client.sent_text().count("[SĐT ***001]") == 1


async def test_load_resets_cursor_and_calls() -> None:
    client = ReplayClient(cassette(risk=[RISK]))
    r = router(client)
    await ask_risk(r)
    client.load(cassette(risk=[{**RISK, "level": "low"}]))
    assert client.calls == []
    assert (await ask_risk(r)).output.level == "low"


def test_client_has_the_surface_the_router_uses() -> None:
    client = ReplayClient(cassette())
    assert client.with_options(timeout=4.0, max_retries=0).messages is not None


async def test_unknown_output_format_is_a_programming_error() -> None:
    client = ReplayClient(cassette())
    with pytest.raises(ValueError):
        await client.parse(model="m", max_tokens=1, system="s", messages=[], output_format=dict)
