"""`McpGuard` (spec 003 US2): Bearer token + giới hạn tần suất cho /mcp/threat, đóng mặc định, log không lộ h1/token."""

import hashlib
import json
import logging
import secrets
from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from hoicon.config import get_settings
from hoicon.mcp_servers import auth
from hoicon.mcp_servers.auth import McpGuard

VN = ZoneInfo("Asia/Ho_Chi_Minh")
H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
CALL = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "lookup_phone", "arguments": {"h1": H1}}}


class Downstream:
    """App ASGI giả đứng sau guard: đếm lần được gọi và (như tool thật) ghi chú tool + verdict cho dòng log."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, scope, receive, send) -> None:
        self.calls += 1
        auth.note(tool="lookup_phone", verdict="flagged")
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b'{"ok": true}'})


class Clock:
    def __init__(self, at: datetime) -> None:
        self.now = at.timestamp()

    def __call__(self) -> float:
        return self.now


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)  # token GIẢ sinh ngẫu nhiên cho test
    return token, hashlib.sha256(token.encode()).hexdigest()


def configure(monkeypatch: pytest.MonkeyPatch, clients: dict[str, str], per_min: int = 30, per_day: int = 1000) -> None:
    monkeypatch.setenv("HOICON_MCP_THREAT_CLIENTS", json.dumps(clients))
    monkeypatch.setenv("HOICON_MCP_RATE_PER_MIN", str(per_min))
    monkeypatch.setenv("HOICON_MCP_RATE_PER_DAY", str(per_day))
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def client_for(app: Downstream, clock: Clock | None = None) -> httpx.AsyncClient:
    guard = McpGuard(app, clock=clock or Clock(datetime(2026, 10, 15, 10, 0, 0, tzinfo=VN)))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=guard), base_url="http://127.0.0.1:18000")


async def post(client: httpx.AsyncClient, token: str | None, scheme: str = "Bearer") -> httpx.Response:
    headers = {"Authorization": f"{scheme} {token}"} if token is not None else {}
    return await client.post("/", json=CALL, headers=headers)


async def test_missing_header_is_401_and_the_tool_does_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    _, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})
    app = Downstream()
    async with client_for(app) as client:
        resp = await post(client, None)
    assert resp.status_code == 401 and resp.headers["www-authenticate"] == "Bearer"
    assert resp.json() == {"error": "unauthorized"} and app.calls == 0


@pytest.mark.parametrize("scheme", ["Basic", "Token", "bearer-ish"])
async def test_wrong_scheme_is_401(monkeypatch: pytest.MonkeyPatch, scheme: str) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})
    app = Downstream()
    async with client_for(app) as client:
        resp = await post(client, token, scheme=scheme)
    assert resp.status_code == 401 and app.calls == 0


async def test_wrong_and_empty_token_are_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})
    app = Downstream()
    async with client_for(app) as client:
        assert (await post(client, new_token()[0])).status_code == 401
        assert (await post(client, "")).status_code == 401
        assert (await client.post("/", json=CALL, headers={"Authorization": "Bearer"})).status_code == 401
    assert app.calls == 0


async def test_no_configured_client_means_401_even_with_a_header(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, {})  # đóng mặc định
    app = Downstream()
    async with client_for(app) as client:
        resp = await post(client, new_token()[0])
    assert resp.status_code == 401 and app.calls == 0


async def test_a_hash_that_is_not_hex_never_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    token, _ = new_token()
    configure(monkeypatch, {"broken": "", "also-broken": "không phải hex"})
    app = Downstream()
    async with client_for(app) as client:
        resp = await post(client, token)
    assert resp.status_code == 401 and app.calls == 0


async def test_valid_token_reaches_the_tool_and_scheme_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"claude-team": digest.upper()})  # hash viết hoa vẫn khớp
    app = Downstream()
    async with client_for(app) as client:
        assert (await post(client, token)).status_code == 200
        assert (await post(client, token, scheme="bearer")).status_code == 200
    assert app.calls == 2


async def test_per_minute_limit_returns_429_with_retry_after_and_is_per_client(monkeypatch: pytest.MonkeyPatch) -> None:
    token_a, hash_a = new_token()
    token_b, hash_b = new_token()
    configure(monkeypatch, {"alpha": hash_a, "beta": hash_b}, per_min=3)
    clock = Clock(datetime(2026, 10, 15, 10, 0, 20, tzinfo=VN))
    app = Downstream()
    async with client_for(app, clock) as client:
        assert [(await post(client, token_a)).status_code for _ in range(3)] == [200, 200, 200]
        over = await post(client, token_a)
        assert over.status_code == 429 and app.calls == 3  # tool không chạy
        assert over.headers["retry-after"] == "40"  # còn 40 giây tới hết phút
        assert (await post(client, token_b)).status_code == 200  # client khác không bị ảnh hưởng
        clock.now += 41
        assert (await post(client, token_a)).status_code == 200  # sang phút mới


async def test_per_day_limit_uses_vietnam_midnight(monkeypatch: pytest.MonkeyPatch) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"alpha": digest}, per_min=100, per_day=2)
    clock = Clock(datetime(2026, 10, 15, 23, 58, 0, tzinfo=VN))
    app = Downstream()
    async with client_for(app, clock) as client:
        assert [(await post(client, token)).status_code for _ in range(2)] == [200, 200]
        over = await post(client, token)
        assert over.status_code == 429 and over.headers["retry-after"] == "120"  # 2 phút tới 00:00 giờ VN
        clock.now += 121
        assert (await post(client, token)).status_code == 200  # ngày mới theo giờ Việt Nam


async def test_non_http_scopes_pass_through() -> None:
    seen: list[str] = []

    async def lifespan_app(scope, receive, send) -> None:
        seen.append(scope["type"])

    guard = McpGuard(lifespan_app)
    await guard({"type": "lifespan"}, None, None)
    assert seen == ["lifespan"]


async def test_log_has_client_status_tool_verdict_and_never_h1_or_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    token, digest = new_token()
    stranger = new_token()[0]
    configure(monkeypatch, {"claude-team": digest}, per_min=1)
    app = Downstream()
    with caplog.at_level(logging.INFO, logger="hoicon.mcp"):
        async with client_for(app) as client:
            await post(client, token)  # 200
            await post(client, token)  # 429
            await post(client, stranger)  # 401
    lines = [r.getMessage() for r in caplog.records if r.name == "hoicon.mcp"]
    assert len(lines) == 3
    assert "client=claude-team" in lines[0] and "status=200" in lines[0]
    assert "tool=lookup_phone" in lines[0] and "verdict=flagged" in lines[0]
    assert "client=claude-team" in lines[1] and "status=429" in lines[1] and "tool=-" in lines[1]
    assert "client=-" in lines[2] and "status=401" in lines[2]  # kẻ lạ: không có tên client
    everything = "\n".join(lines) + caplog.text
    for secret in (H1, token, stranger, digest, "127.0.0.1"):
        assert secret not in everything, "log không được chứa h1/token/hash token/IP"


async def test_get_is_rejected_after_authentication_so_no_connection_hangs(monkeypatch: pytest.MonkeyPatch) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})
    app = Downstream()
    async with client_for(app) as client:
        resp = await client.get("/", headers={"Authorization": f"Bearer {token}"})
        anon = await client.get("/")
    assert resp.status_code == 405 and resp.headers["allow"] == "POST" and app.calls == 0
    assert anon.status_code == 401  # chưa xác thực thì vẫn 401, không lộ phương thức được phép


async def test_oversized_body_is_rejected_before_the_tool_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})
    app = Downstream()
    async with client_for(app) as client:
        big = await client.post("/", content=b"x" * 70_000, headers={"Authorization": f"Bearer {token}"})
    assert big.status_code == 413 and app.calls == 0


async def test_websocket_scope_is_closed_not_passed_through() -> None:
    sent: list[dict] = []
    app = Downstream()

    async def send(message: dict) -> None:
        sent.append(message)

    await McpGuard(app)({"type": "websocket", "headers": []}, None, send)
    assert app.calls == 0 and sent == [{"type": "websocket.close", "code": 1008}]


async def test_a_crashing_tool_is_still_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    token, digest = new_token()
    configure(monkeypatch, {"claude-team": digest})

    async def crashing(scope, receive, send) -> None:
        raise RuntimeError("boom")

    guard = McpGuard(crashing, clock=Clock(datetime(2026, 10, 15, 10, 0, 0, tzinfo=VN)))
    with caplog.at_level(logging.INFO, logger="hoicon.mcp"), pytest.raises(RuntimeError):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=guard), base_url="http://x") as client:
            await post(client, token)
    assert any("client=claude-team" in r.getMessage() and "status=0" in r.getMessage() for r in caplog.records)
