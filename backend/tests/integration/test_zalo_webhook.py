"""US2/US5 (FR-001/002/013, SC-004/005): webhook Zalo — kiểm secret, chống trùng, job không mang định danh thô."""

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from hoicon.api import webhooks
from hoicon.api.main import app as main_app
from hoicon.db.ids import new_id
from hoicon.db.models import Job
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import decrypt_chat_id, hmac_pairing_code, hmac_zalo

pytestmark = pytest.mark.integration

SECRET = "fixture-secret-0123456789"  # gitleaks:allow — secret giả của test
FIXTURES = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "fixtures" / "zalo_update.v1.valid.json"


def update(text: str = "1", *, message_id: str | None = None, user: str = "fixture-user-0001") -> dict[str, Any]:
    base = next(u for u in json.loads(FIXTURES.read_text(encoding="utf-8")) if u["_name"] == "text_reply_1")
    base = {k: v for k, v in base.items() if k != "_name"}
    base["result"]["message"].update({"text": text, "message_id": message_id or f"fixture-msg-{new_id().hex[:12]}"})
    base["result"]["message"]["from"]["id"] = user
    base["result"]["message"]["chat"]["id"] = f"chat-of-{user}"
    return base


@pytest.fixture
def hook(zalo_world: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    settings = zalo_world.settings.model_copy(update={"zalo_webhook_secret": SecretStr(SECRET)})
    monkeypatch.setattr(webhooks, "get_settings", lambda: settings)
    zalo_world.settings = settings
    return zalo_world


async def post(
    body: Any, bot_id: str, secret: str | None = SECRET, *, application: Any = webhooks.app, raw: bytes | None = None
) -> Any:
    headers = {"Content-Type": "application/json"}
    if secret is not None:
        headers["X-Bot-Api-Secret-Token"] = secret
    async with AsyncClient(transport=ASGITransport(app=application), base_url="http://test") as client:
        content = raw if raw is not None else json.dumps(body).encode()
        return await client.post(f"/webhooks/zalo/{bot_id}", content=content, headers=headers)


async def jobs_of(bot_id: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        query = select(Job).where(Job.idempotency_key.startswith(f"zalo:{bot_id}:", autoescape=True))
        return list(await session.scalars(query))


@pytest.mark.parametrize("secret", [None, "", "wrong-secret", SECRET + "x", SECRET[:-1], "Fixture-Secret-0123456789"])
async def test_wrong_or_missing_secret_is_rejected_and_queues_nothing(hook: Any, secret: str | None) -> None:
    response = await post(update(), hook.bot_id, secret)
    assert response.status_code == 401
    assert await jobs_of(hook.bot_id) == []  # SC-005


async def test_valid_update_returns_200_and_queues_one_job_without_raw_identifiers(hook: Any) -> None:
    body = update("1", message_id="fixture-msg-aaa")
    response = await post(body, hook.bot_id)
    assert response.status_code == 200 and response.json() == {"ok": True}
    (job,) = await jobs_of(hook.bot_id)
    assert job.kind == "zalo_update" and job.idempotency_key == f"zalo:{hook.bot_id}:fixture-msg-aaa"
    stored = json.dumps(job.payload, ensure_ascii=False)
    for raw in ("fixture-user-0001", "chat-of-fixture-user-0001", "Người giám hộ mẫu"):
        assert raw not in stored  # FR-010: job nằm trong DB 30 ngày
    kid, expected_hmac = hmac_zalo(hook.bot_id, "fixture-user-0001")
    assert job.payload["user_hmac"] == expected_hmac and job.payload["hmac_kid"] == kid
    assert decrypt_chat_id(job.payload["chat_enc"], expected_hmac) == "chat-of-fixture-user-0001"
    assert job.payload["kind"] == "choice" and job.payload["choice"] == "1" and "text" not in job.payload


async def test_start_command_keeps_only_the_hash_of_the_code(hook: Any) -> None:
    await post(update("/start 482913"), hook.bot_id)
    (job,) = await jobs_of(hook.bot_id)
    assert job.payload["kind"] == "start" and job.payload["code_hash"] == hmac_pairing_code("482913")
    assert "482913" not in json.dumps(job.payload)


async def test_same_update_sent_five_times_is_processed_once(hook: Any) -> None:
    body = update("/start 482913", message_id="fixture-msg-dup")
    statuses = [(await post(body, hook.bot_id)).status_code for _ in range(5)]
    assert statuses == [200] * 5
    assert len(await jobs_of(hook.bot_id)) == 1  # SC-004


async def test_database_failure_returns_503_so_zalo_can_retry(hook: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(*_: Any, **__: Any) -> None:
        raise OperationalError("insert", {}, Exception("db down"))

    monkeypatch.setattr(webhooks, "enqueue", broken)
    response = await post(update(), hook.bot_id)
    assert response.status_code == 503  # không trả 200 rồi mất cập nhật
    assert "db down" not in response.text


@pytest.mark.parametrize(
    "mutate",
    [
        lambda u: u["result"].update(event_name="message.image.received"),
        lambda u: u["result"]["message"]["chat"].update(chat_type="GROUP"),
        lambda u: u["result"]["message"]["from"].update(is_bot=True),
        lambda u: u["result"]["message"].pop("message_id"),
        lambda u: u["result"].pop("message"),
    ],
    ids=["image", "group", "bot", "no_message_id", "no_message"],
)
async def test_updates_we_cannot_use_are_acknowledged_without_a_job(hook: Any, mutate: Any) -> None:
    body = update()
    mutate(body)
    response = await post(body, hook.bot_id)
    assert response.status_code == 200  # 4xx/5xx làm Zalo gửi lại hoặc ngắt webhook
    assert await jobs_of(hook.bot_id) == []


async def test_unsupported_event_and_zalo_verification_probe_are_ok(hook: Any) -> None:
    for body in ({"ok": True, "result": {"event_name": "message.unsupported.received"}}, {"ok": True}, {}):
        assert (await post(body, hook.bot_id)).status_code == 200
    assert await jobs_of(hook.bot_id) == []


async def test_bad_bodies(hook: Any) -> None:
    assert (await post(None, hook.bot_id, raw=b"not json")).status_code == 400
    assert (await post(None, hook.bot_id, raw=b"x" * (webhooks.MAX_BODY + 1))).status_code == 413
    assert await jobs_of(hook.bot_id) == []


async def test_unknown_bot_is_404_only_after_authentication(hook: Any) -> None:
    assert (await post(update(), "some-other-bot")).status_code == 404
    assert (await post(update(), "some-other-bot", secret="wrong")).status_code == 401  # không lộ bot nào tồn tại


async def test_webhook_not_configured_fails_closed(hook: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    unset = hook.settings.model_copy(update={"zalo_webhook_secret": None})
    monkeypatch.setattr(webhooks, "get_settings", lambda: unset)
    response = await post(update(), hook.bot_id, secret="anything")
    assert response.status_code == 503
    assert await jobs_of(hook.bot_id) == []


async def test_tunnel_app_exposes_only_the_webhook_route(hook: Any) -> None:
    """FR-013: đường hầm dev chỉ phơi ứng dụng con — không có /docs, /openapi.json, /mcp, /healthz."""
    async with AsyncClient(transport=ASGITransport(app=webhooks.app), base_url="http://test") as client:
        for path in ("/docs", "/redoc", "/openapi.json", "/mcp/threat/", "/healthz", "/readyz", "/"):
            assert (await client.get(path)).status_code == 404, path
    assert (await post(update(), hook.bot_id, application=webhooks.app)).status_code == 200  # route webhook vẫn chạy


async def test_main_app_serves_the_same_route(hook: Any) -> None:
    response = await post(update(), hook.bot_id, application=main_app)
    assert response.status_code == 200 and len(await jobs_of(hook.bot_id)) == 1


async def test_secret_and_identifiers_never_reach_the_logs(hook: Any, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        await post(update("/start 482913"), hook.bot_id)
        await post(update(), hook.bot_id, secret="wrong-secret-value")
    for forbidden in (SECRET, "wrong-secret-value", "fixture-user-0001", "482913"):
        assert forbidden not in caplog.text
