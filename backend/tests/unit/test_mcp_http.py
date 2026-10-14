"""/mcp/threat trong app FastAPI: gọi được từ localhost; Host lạ bị từ chối (chưa xác thực, chưa mở ra ngoài)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from hoicon.api.main import app

H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
CALL = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "lookup_phone", "arguments": {"h1": H1}},
}


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    # Lifespan (session manager MCP) chỉ chạy được một lần mỗi tiến trình — như uvicorn ở production.
    with TestClient(app, base_url="http://127.0.0.1:18000") as test_client:
        yield test_client


def test_threat_tool_over_streamable_http(client: TestClient) -> None:
    resp = client.post("/mcp/threat/", json=CALL, headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["result"]["structuredContent"]["verdict"] == "flagged"


def test_foreign_host_is_rejected(client: TestClient) -> None:
    resp = client.post("/mcp/threat/", json=CALL, headers={**HEADERS, "Host": "hoicon.example"})
    assert resp.status_code == 421
