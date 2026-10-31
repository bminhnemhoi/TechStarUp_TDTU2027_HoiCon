"""MCP server `threat` đọc danh sách đe dọa trong Postgres (spec 003): tool in-process, h1 thô bị từ chối."""

from typing import Any

import pytest
from mcp.client import Client

from hoicon.mcp_servers.threat import mcp

pytestmark = pytest.mark.integration

FLAGGED = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"


async def test_mcp_tool_over_in_memory_client(seeded_threat: dict[str, Any]) -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert [t.name for t in tools.tools] == ["lookup_phone"]
        result = await client.call_tool("lookup_phone", {"h1": FLAGGED})
        assert not result.is_error
        assert result.structured_content["verdict"] == "flagged"
        assert result.structured_content["list_version"] == seeded_threat["version"]
        unknown = await client.call_tool("lookup_phone", {"h1": "0" * 64})
        assert unknown.structured_content["verdict"] == "unknown"
        bad = await client.call_tool("lookup_phone", {"h1": "0900000002"})
        assert bad.is_error
