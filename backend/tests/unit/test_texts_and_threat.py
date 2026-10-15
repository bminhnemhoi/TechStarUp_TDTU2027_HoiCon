"""Luật 6 (công khai AI) cho mọi tin của đồ thị sự cố. Tra cứu danh sách đe dọa + MCP `threat` (cần DB): xem
`tests/integration/test_threat_lookup.py`."""

import pytest

from hoicon.agents import texts
from hoicon.domain.risk import RiskLevel


@pytest.mark.parametrize("is_drill", [False, True])
def test_every_message_starts_with_ai_disclosure(is_drill: bool) -> None:
    messages = [
        texts.guardian_fast_alert("Mẹ", "002", "bank", is_drill),
        texts.guardian_fast_alert("Mẹ", None, "other", is_drill),
        texts.guardian_detail("Mẹ", RiskLevel.CRITICAL, "Tóm tắt.", "call_now", is_drill),
        texts.guardian_reminder("Mẹ", is_drill),
        texts.guardian_escalation("Mẹ", is_drill),
        *(texts.question_for_elder(q, is_drill) for q in texts.QUESTIONS),
    ]
    for message in messages:
        assert message.startswith("Đây là trợ lý AI HỏiCon"), message
        assert ("[DIỄN TẬP]" in message) is is_drill, message  # luật 8: diễn tập luôn có nhãn


def test_every_level_and_action_has_copy() -> None:
    assert set(texts.LEVEL_VI) == set(RiskLevel)
    for action in ("call_now", "call_and_stay_on_line", "visit_or_call_relative"):
        assert "{alias}" in texts.ACTION_VI[action]
