"""Luật 6 (công khai AI) cho mọi tin của đồ thị sự cố + MCP server `threat`."""

import pytest
from mcp.client import Client

from hoicon.agents import texts
from hoicon.domain.risk import RiskLevel
from hoicon.mcp_servers.threat import lookup_h1, mcp

FLAGGED = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"


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


def test_lookup_rejects_raw_numbers() -> None:
    assert lookup_h1(FLAGGED).verdict == "flagged"
    assert lookup_h1("0" * 64).verdict == "unknown"
    with pytest.raises(ValueError):
        lookup_h1("0900000002")


async def test_mcp_tool_over_in_memory_client() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert [t.name for t in tools.tools] == ["lookup_phone"]
        result = await client.call_tool("lookup_phone", {"h1": FLAGGED})
        assert not result.is_error
        assert result.structured_content["verdict"] == "flagged"
        bad = await client.call_tool("lookup_phone", {"h1": "0900000002"})
        assert bad.is_error
