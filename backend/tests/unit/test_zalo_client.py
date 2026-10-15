"""ZaloClient: token chỉ ghép URL lúc gọi, không bao giờ lọt vào lỗi/log (ADR-003, CLAUDE.md luật 9)."""

import json
import logging
import traceback

import httpx
import pytest
from pydantic import SecretStr

from hoicon.channels.zalo import (
    LiveZaloClient,
    MockZaloClient,
    ZaloError,
    build_zalo_client,
    redact,
)
from hoicon.config import Settings

TOKEN = "123456:TOKEN-GIA-KHONG-DUOC-LO"


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{"zalo_bot_token": None, **overrides})  # type: ignore[arg-type]


def _live(handler: httpx.MockTransport | None = None, **kwargs: object) -> LiveZaloClient:
    return LiveZaloClient(SecretStr(TOKEN), transport=handler, **kwargs)  # type: ignore[arg-type]


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"ok": True, "result": {"message_id": "fixture-msg-9", "date": 1750316131602}})


async def test_live_sends_to_token_url_and_parses_result() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _ok(request)

    sent = await _live(httpx.MockTransport(handler)).send_message("fixture-chat-0001", "Xin chào")
    assert sent.message_id == "fixture-msg-9"
    assert str(seen[0].url) == f"https://bot-api.zaloplatforms.com/bot{TOKEN}/sendMessage"
    assert seen[0].method == "POST"
    assert json.loads(seen[0].content) == {"chat_id": "fixture-chat-0001", "text": "Xin chào"}


@pytest.mark.parametrize("text", ["", "x" * 2001])
async def test_text_length_is_checked_before_any_network_call(text: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("không được gọi mạng")

    with pytest.raises(ValueError, match="1–2000"):
        await _live(httpx.MockTransport(handler)).send_message("fixture-chat-0001", text)


@pytest.mark.parametrize(
    ("response", "status", "retryable"),
    [
        (httpx.Response(401, json={"ok": False, "error_code": 401, "description": f"bad {TOKEN}"}), 401, False),
        (httpx.Response(404, json={"ok": False}), 404, False),
        (httpx.Response(429, json={"ok": False}), 429, True),
        (httpx.Response(500, text=f"upstream error at /bot{TOKEN}/sendMessage"), 500, True),
        (httpx.Response(200, json={"ok": False, "errorCode": 426}), 426, False),  # trần ngày: tài liệu viết camelCase
        (httpx.Response(200, json={"ok": False, "error_code": 429}), 429, True),
        (httpx.Response(200, text="không phải JSON"), 200, False),
    ],
)
async def test_http_and_api_errors_carry_status_but_never_token_or_url(
    response: httpx.Response, status: int, retryable: bool
) -> None:
    client = _live(httpx.MockTransport(lambda request: response))
    with pytest.raises(ZaloError) as info:
        await client.send_message("fixture-chat-0001", "Xin chào")
    err = info.value
    assert err.status == status
    assert err.retryable is retryable
    rendered = "".join(traceback.format_exception(err)) + str(err) + repr(err) + repr(err.args)
    for forbidden in (TOKEN, "bot-api.zaloplatforms.com", "TOKEN-GIA"):
        assert forbidden not in rendered
    assert "fixture-chat-0001" not in str(err) + repr(err)  # (traceback có dòng mã nguồn của test nên không xét)
    assert err.__cause__ is None
    assert err.__context__ is None  # không giữ ngoại lệ httpx gốc (có URL chứa token)


async def test_transport_error_has_no_status_is_retryable_and_leaks_nothing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot connect to {request.url}", request=request)

    with pytest.raises(ZaloError) as info:
        await _live(httpx.MockTransport(handler)).send_message("fixture-chat-0001", "Xin chào")
    err = info.value
    assert err.status is None
    assert err.retryable is True
    assert TOKEN not in "".join(traceback.format_exception(err)) + str(err) + repr(err)
    assert err.__context__ is None


def test_redact_hides_token_segment() -> None:
    assert redact(f"POST https://bot-api.zaloplatforms.com/bot{TOKEN}/sendMessage 200") == (
        "POST https://bot-api.zaloplatforms.com/bot***/sendMessage 200"
    )
    assert redact("không có token ở đây") == "không có token ở đây"


async def test_httpx_request_log_is_redacted_even_when_info_is_enabled(caplog: pytest.LogCaptureFixture) -> None:
    """httpx ghi `HTTP Request: POST <url>` ở mức INFO: dù ai bật INFO, URL trong log vẫn phải che token."""
    logging.getLogger("httpx").setLevel(logging.INFO)  # mô phỏng cấu hình log sai/dev bật INFO
    try:
        with caplog.at_level(logging.INFO, logger="httpx"):
            await _live(httpx.MockTransport(_ok)).send_message("fixture-chat-0001", "Xin chào")
    finally:
        logging.getLogger("httpx").setLevel(logging.WARNING)
    assert TOKEN not in caplog.text
    assert TOKEN not in "".join(str(r.__dict__) for r in caplog.records)


def test_importing_module_sets_httpx_logger_to_warning() -> None:
    assert logging.getLogger("httpx").level == logging.WARNING


async def test_mock_records_messages_and_never_calls_network() -> None:
    client = MockZaloClient()
    first = await client.send_message("fixture-chat-0001", "Xin chào")
    second = await client.send_message("fixture-chat-0002", "Chào bác")
    assert [(m.chat_id, m.text) for m in client.sent] == [
        ("fixture-chat-0001", "Xin chào"),
        ("fixture-chat-0002", "Chào bác"),
    ]
    assert first.message_id != second.message_id


async def test_mock_applies_same_text_limits_as_live() -> None:
    with pytest.raises(ValueError, match="1–2000"):
        await MockZaloClient().send_message("fixture-chat-0001", "")


def test_default_mode_is_mock() -> None:
    assert isinstance(build_zalo_client(_settings()), MockZaloClient)


def test_mock_mode_is_refused_in_prod_so_alerts_are_never_silently_lost() -> None:
    with pytest.raises(RuntimeError, match="HOICON_ZALO_MODE=live"):
        build_zalo_client(_settings(env="prod"))
    assert isinstance(build_zalo_client(_settings(env="dev")), MockZaloClient)
    live = build_zalo_client(_settings(env="prod", zalo_mode="live", zalo_bot_token=SecretStr(TOKEN)))
    assert isinstance(live, LiveZaloClient)


def test_live_mode_without_token_fails_at_startup_not_silently_mock() -> None:
    with pytest.raises(RuntimeError, match="HOICON_ZALO_BOT_TOKEN"):
        build_zalo_client(_settings(zalo_mode="live"))


def test_live_mode_with_token_builds_live_client_without_exposing_token() -> None:
    client = build_zalo_client(_settings(zalo_mode="live", zalo_bot_token=SecretStr(TOKEN)))
    assert isinstance(client, LiveZaloClient)
    assert TOKEN not in repr(client) + repr(vars(client))


@pytest.mark.parametrize("bad", ["abc def", "abc\n", "abc/def", "abc?x=1", "tốc-độ"])
def test_malformed_token_is_rejected_without_echoing_it(bad: str) -> None:
    with pytest.raises(RuntimeError) as info:
        LiveZaloClient(SecretStr(bad))
    assert bad.strip() not in str(info.value)


def test_invalid_mode_is_rejected() -> None:
    with pytest.raises(ValueError, match="zalo_mode"):
        _settings(zalo_mode="maybe")
