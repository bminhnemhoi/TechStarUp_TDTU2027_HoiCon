"""FR-013: lệnh vận hành đặt/xem/xóa webhook Zalo — chỉ in Đạt/Lỗi, không bao giờ in token, secret hay URL."""

import json
import logging
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from hoicon.channels.zalo import LiveZaloClient
from hoicon.config import Settings
from hoicon.ops import zalo_webhook

TOKEN = "123456:TOKEN-GIA-KHONG-DUOC-IN"
SHARED = "fixture-shared-0123456789abcdef"
HOST = "demo-tunnel-fixture.trycloudflare.com"
BASE = f"https://{HOST}"
FULL = f"{BASE}/webhooks/zalo/hoicon-dev"


def settings(**override: Any) -> Settings:
    values: dict[str, Any] = {
        "zalo_bot_token": SecretStr(TOKEN),
        "zalo_webhook_secret": SecretStr(SHARED),
        "zalo_bot_id": "hoicon-dev",
    }
    return Settings(_env_file=None, **{**values, **override})


class Recorder:
    def __init__(self, response: httpx.Response | None = None, outcome: str = "webhook.ok") -> None:
        self.requests: list[httpx.Request] = []
        self.response = response
        self.outcome = outcome

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.response is not None:
            return self.response
        method = request.url.path.rsplit("/", 1)[1]
        result: dict[str, Any] = {
            "setWebhook": {"url": FULL, "updated_at": 1, "verification": {"ok": True, "outcome": self.outcome}},
            "getWebhookInfo": {"url": FULL, "updated_at": 1749538250568},
            "deleteWebhook": {"url": "", "updated_at": 2},
        }[method]
        return httpx.Response(200, json={"ok": True, "result": result})


def client_for(recorder: Recorder) -> LiveZaloClient:
    return LiveZaloClient(SecretStr(TOKEN), transport=httpx.MockTransport(recorder))


def assert_clean(output: str) -> None:
    for forbidden in (TOKEN, "TOKEN-GIA", SHARED, HOST, "trycloudflare", "bot-api.zaloplatforms.com"):
        assert forbidden not in output


async def test_set_posts_the_full_url_and_shared_value_but_prints_only_the_verdict(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rec = Recorder()
    assert await zalo_webhook.run(["set", "--url", FULL], settings(), client_for(rec)) == 0
    (request,) = rec.requests
    assert request.url.path == f"/bot{TOKEN}/setWebhook"
    assert json.loads(request.content) == {"url": FULL, "secret_token": SHARED}
    out = capsys.readouterr().out
    assert "Đạt" in out and "webhook.ok" in out
    assert_clean(out)


async def test_base_url_gets_the_webhook_path_appended(capsys: pytest.CaptureFixture[str]) -> None:
    rec = Recorder()
    assert await zalo_webhook.run(["set", "--url", BASE], settings(), client_for(rec)) == 0
    assert json.loads(rec.requests[0].content)["url"] == FULL
    assert await zalo_webhook.run(["set", "--url", BASE + "/"], settings(), client_for(rec)) == 0
    assert json.loads(rec.requests[1].content)["url"] == FULL


@pytest.mark.parametrize(
    "url",
    [
        "http://demo.example.com",  # phải HTTPS
        "https://localhost",
        "https://127.0.0.1",
        "https://192.168.1.10",
        "https://10.0.0.5/webhooks/zalo/hoicon-dev",
        "https://demo.example.com/other/path",  # đường dẫn khác route webhook của bot
        "https://demo.example.com/webhooks/zalo/another-bot",
        "https://user:pass@demo.example.com",
        "ftp://demo.example.com",
        "not a url",
        "",
    ],
)
async def test_bad_urls_are_rejected_before_any_network_call(url: str, capsys: pytest.CaptureFixture[str]) -> None:
    rec = Recorder()
    assert await zalo_webhook.run(["set", "--url", url], settings(), client_for(rec)) == 2
    assert rec.requests == []
    out = capsys.readouterr().out
    assert "Lỗi" in out and "pass" not in out


async def test_failed_verification_is_reported_as_an_error_even_though_zalo_saved_the_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rec = Recorder(outcome="webhook.http.403")
    body = {"ok": True, "result": {"url": FULL, "verification": {"ok": False, "outcome": "webhook.http.403"}}}
    rec.response = httpx.Response(200, json=body)
    assert await zalo_webhook.run(["set", "--url", FULL], settings(), client_for(rec)) == 1
    out = capsys.readouterr().out
    assert "Lỗi" in out and "webhook.http.403" in out
    assert_clean(out)


async def test_unexpected_outcome_text_is_not_echoed(capsys: pytest.CaptureFixture[str]) -> None:
    body = {"ok": True, "result": {"verification": {"ok": False, "outcome": f"echo {TOKEN} <script>"}}}
    rec = Recorder(httpx.Response(200, json=body))
    assert await zalo_webhook.run(["set", "--url", FULL], settings(), client_for(rec)) == 1
    out = capsys.readouterr().out
    assert TOKEN not in out and "<script>" not in out


async def test_info_reports_whether_a_webhook_is_set_without_printing_the_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert await zalo_webhook.run(["info"], settings(), client_for(Recorder())) == 0
    out = capsys.readouterr().out
    assert "Đạt" in out and "đã đặt" in out
    assert_clean(out)
    empty = Recorder(httpx.Response(200, json={"ok": True, "result": {"url": "", "updated_at": 0}}))
    assert await zalo_webhook.run(["info"], settings(), client_for(empty)) == 0
    assert "chưa đặt" in capsys.readouterr().out


async def test_delete(capsys: pytest.CaptureFixture[str]) -> None:
    rec = Recorder()
    assert await zalo_webhook.run(["delete"], settings(), client_for(rec)) == 0
    assert rec.requests[0].url.path.endswith("/deleteWebhook")
    out = capsys.readouterr().out
    assert "Đạt" in out
    assert_clean(out)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(401, json={"ok": False, "error_code": 401, "description": f"bad {TOKEN}"}), "HTTP 401"),
        (httpx.Response(500, text=f"boom {TOKEN}"), "HTTP 500"),
    ],
)
async def test_zalo_errors_print_only_the_status(
    response: httpx.Response, expected: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert await zalo_webhook.run(["info"], settings(), client_for(Recorder(response))) == 1
    out = capsys.readouterr().out
    assert "Lỗi" in out and expected in out
    assert_clean(out)


async def test_network_error_prints_a_generic_error(capsys: pytest.CaptureFixture[str]) -> None:
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {request.url}", request=request)

    client = LiveZaloClient(SecretStr(TOKEN), transport=httpx.MockTransport(boom))
    assert await zalo_webhook.run(["info"], settings(), client) == 1
    out = capsys.readouterr().out
    assert "Lỗi" in out and "mạng" in out
    assert_clean(out)


async def test_missing_token_or_shared_value_fails_without_network(capsys: pytest.CaptureFixture[str]) -> None:
    rec = Recorder()
    assert await zalo_webhook.run(["info"], settings(zalo_bot_token=None), None) == 1
    assert "Thiếu" in capsys.readouterr().out
    assert await zalo_webhook.run(["set", "--url", FULL], settings(zalo_webhook_secret=None), client_for(rec)) == 1
    assert "Thiếu" in capsys.readouterr().out
    assert (
        await zalo_webhook.run(
            ["set", "--url", FULL], settings(zalo_webhook_secret=SecretStr("short")), client_for(rec)
        )
        == 1
    )
    assert "8–256" in capsys.readouterr().out
    assert rec.requests == []


async def test_nothing_sensitive_reaches_the_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        await zalo_webhook.run(["set", "--url", FULL], settings(), client_for(Recorder()))
        await zalo_webhook.run(["info"], settings(), client_for(Recorder(httpx.Response(401, json={"ok": False}))))
    assert_clean(caplog.text)
