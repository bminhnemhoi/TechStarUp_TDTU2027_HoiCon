"""/mcp/threat trong app FastAPI thật (spec 003 US2): token + hạn mức + streamable HTTP không bị middleware phá."""

import asyncio
import hashlib
import json
import logging
import secrets
import uuid
from collections.abc import AsyncGenerator, Iterator
from typing import Any

import httpx
import pytest

from hoicon.api.main import app
from hoicon.config import get_settings

pytestmark = pytest.mark.integration

H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
INIT = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "pytest", "version": "0"}},
}
CALL = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "lookup_phone", "arguments": {"h1": H1}},
}


@pytest.fixture(scope="module")
async def client() -> AsyncGenerator[httpx.AsyncClient]:
    """App thật kèm lifespan (session manager MCP chỉ chạy được MỘT lần mỗi tiến trình): vào/ra trong một tác vụ."""
    ready, stop = asyncio.Event(), asyncio.Event()

    async def serve() -> None:
        async with app.router.lifespan_context(app):
            ready.set()
            await stop.wait()

    task = asyncio.create_task(serve())
    await asyncio.wait_for(ready.wait(), 10)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1:18000") as c:
        yield c
    stop.set()
    await task


@pytest.fixture
def mcp_token(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, str]]:
    """Token GIẢ ngẫu nhiên + tên client duy nhất (hạn mức nằm trong guard dùng chung của app)."""
    token, name = secrets.token_urlsafe(32), f"pytest-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("HOICON_MCP_THREAT_CLIENTS", json.dumps({name: hashlib.sha256(token.encode()).hexdigest()}))
    get_settings.cache_clear()
    yield token, name
    get_settings.cache_clear()


def auth(token: str) -> dict[str, str]:
    return {**HEADERS, "Authorization": f"Bearer {token}"}


async def test_without_a_token_the_tool_does_not_run(client: httpx.AsyncClient, mcp_token: tuple[str, str]) -> None:
    resp = await client.post("/mcp/threat/", json=CALL, headers=HEADERS)
    assert resp.status_code == 401 and resp.headers["www-authenticate"] == "Bearer"
    assert "flagged" not in resp.text and "unknown" not in resp.text


async def test_wrong_token_is_401(client: httpx.AsyncClient, mcp_token: tuple[str, str]) -> None:
    assert (await client.post("/mcp/threat/", json=CALL, headers=auth("sai-token"))).status_code == 401


async def test_server_without_configured_clients_is_closed(
    client: httpx.AsyncClient, mcp_token: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    token, _ = mcp_token
    monkeypatch.setenv("HOICON_MCP_THREAT_CLIENTS", "{}")
    get_settings.cache_clear()
    assert (await client.post("/mcp/threat/", json=CALL, headers=auth(token))).status_code == 401


async def test_valid_token_initialize_then_tool_call_over_streamable_http(
    client: httpx.AsyncClient, mcp_token: tuple[str, str], seeded_threat: dict[str, Any]
) -> None:
    token, _ = mcp_token
    init = await client.post("/mcp/threat/", json=INIT, headers=auth(token))
    assert init.status_code == 200 and init.json()["result"]["serverInfo"]["name"] == "hoicon-threat"
    resp = await client.post("/mcp/threat/", json=CALL, headers=auth(token))
    assert resp.status_code == 200
    result = resp.json()["result"]["structuredContent"]
    assert (
        result["verdict"] == "flagged" and result["source"] == "demo" and result["tactic"] == "impersonation_authority"
    )
    assert result["list_version"] == seeded_threat["version"]


async def test_foreign_host_is_still_rejected_after_authentication(
    client: httpx.AsyncClient, mcp_token: tuple[str, str]
) -> None:
    token, _ = mcp_token
    resp = await client.post("/mcp/threat/", json=CALL, headers={**auth(token), "Host": "hoicon.example"})
    assert resp.status_code == 421  # kiểm Host của SDK giữ nguyên (chống DNS rebinding), nằm sau token
    unauth = await client.post("/mcp/threat/", json=CALL, headers={**HEADERS, "Host": "hoicon.example"})
    assert unauth.status_code == 401  # không token thì không biết gì về cấu hình Host


async def test_rate_limit_over_the_real_app(
    client: httpx.AsyncClient,
    mcp_token: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    seeded_threat: dict[str, Any],
) -> None:
    token, _ = mcp_token
    monkeypatch.setenv("HOICON_MCP_RATE_PER_MIN", "2")
    get_settings.cache_clear()
    assert [(await client.post("/mcp/threat/", json=CALL, headers=auth(token))).status_code for _ in range(2)] == [
        200,
        200,
    ]
    over = await client.post("/mcp/threat/", json=CALL, headers=auth(token))
    assert over.status_code == 429 and 1 <= int(over.headers["retry-after"]) <= 60


async def test_log_line_carries_the_verdict_set_by_the_tool_and_leaks_nothing(
    client: httpx.AsyncClient,
    mcp_token: tuple[str, str],
    seeded_threat: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    token, name = mcp_token
    with caplog.at_level(logging.INFO):
        assert (await client.post("/mcp/threat/", json=CALL, headers=auth(token))).status_code == 200
    lines = [r.getMessage() for r in caplog.records if r.name == "hoicon.mcp"]
    assert len(lines) == 1 and f"client={name}" in lines[0] and "status=200" in lines[0]
    assert "tool=lookup_phone" in lines[0] and "verdict=flagged" in lines[0]  # `note()` đi qua tác vụ con của SDK
    for secret in (H1, token, hashlib.sha256(token.encode()).hexdigest()):
        assert secret not in caplog.text
