"""SC-003/FR-010/011: chạy cả luồng Zalo bằng client THẬT (qua transport giả) với token có dấu hiệu nhận biết rồi quét
log, stdout và mọi bảng DB: không có token, khóa webhook, Zalo ID thô, mã ghép thô hay tên hiển thị."""

import json
import logging
from typing import Any

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import text

from hoicon.agents import texts
from hoicon.api import webhooks
from hoicon.channels.guardian import ChannelDeps, send_to_guardian
from hoicon.channels.updates import handle_update
from hoicon.channels.zalo import LiveZaloClient, ZaloError
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

TOKEN = "987654:LEAKCANARY-TOKEN-ZALO-9f3a"
SHARED = "LEAKCANARY-SHARED-VALUE-77aa11"
USER, CHAT = "fixture-user-LEAKCANARY", "chat-of-fixture-user-LEAKCANARY"
DISPLAY_NAME = "Người giám hộ mẫu LEAKCANARY"
TABLES = ("members", "messages_out", "pairing_codes", "families", "jobs")


def zalo_update(message_text: str, message_id: str) -> dict[str, Any]:
    return {
        "ok": True,
        "result": {
            "event_name": "message.text.received",
            "message": {
                "from": {"id": USER, "display_name": DISPLAY_NAME, "is_bot": False},
                "chat": {"id": CHAT, "chat_type": "PRIVATE"},
                "text": message_text,
                "message_id": message_id,
            },
        },
    }


async def dump_database(bot_id: str) -> str:
    """Mọi dòng liên quan tới bot/gia đình của test, dạng JSON text (cả cột lẫn payload)."""
    queries = [
        "select row_to_json(t)::text from members t where zalo_bot_id = :bot",
        "select row_to_json(t)::text from messages_out t where bot_id = :bot",
        "select row_to_json(t)::text from jobs t where idempotency_key like :job",
        "select row_to_json(t)::text from pairing_codes t",
        "select row_to_json(t)::text from families t",
    ]
    out: list[str] = []
    async with get_sessionmaker()() as session:
        for query in queries:
            params = {"bot": bot_id, "job": f"%{bot_id}%"} if ":" in query else {}
            result = await session.execute(
                text(query).bindparams(**{k: v for k, v in params.items() if f":{k}" in query})
            )
            out.extend(result.scalars())
    return "\n".join(out)


async def test_whole_zalo_flow_leaks_nothing(
    zalo_world: Any,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    world = zalo_world
    settings = world.settings.model_copy(
        update={"zalo_webhook_secret": SecretStr(SHARED), "zalo_bot_token": SecretStr(TOKEN)}
    )
    monkeypatch.setattr(webhooks, "get_settings", lambda: settings)

    calls: list[httpx.Request] = []
    failing = {"on": False}

    def zalo(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if failing["on"]:
            return httpx.Response(500, text=f"upstream error for {request.url} token {TOKEN}")
        return httpx.Response(200, json={"ok": True, "result": {"message_id": "fixture-sent-1", "date": 1}})

    live = LiveZaloClient(SecretStr(TOKEN), transport=httpx.MockTransport(zalo))
    deps = ChannelDeps(get_sessionmaker(), live, settings)
    logging.getLogger("httpx").setLevel(logging.INFO)  # kể cả khi ai đó bật INFO, URL trong log vẫn phải che token
    try:
        with caplog.at_level(logging.DEBUG):
            code = await world.make_code()
            async with AsyncClient(transport=ASGITransport(app=webhooks.app), base_url="http://test") as http:
                for index, message in enumerate((f"/start {code}", "xin chào", "1")):
                    response = await http.post(
                        f"/webhooks/zalo/{world.bot_id}",
                        json=zalo_update(message, f"fixture-msg-leak-{index}"),
                        headers={"X-Bot-Api-Secret-Token": SHARED},
                    )
                    assert response.status_code == 200
                await http.post(  # secret sai: lỗi xác thực cũng không được in secret
                    f"/webhooks/zalo/{world.bot_id}", json={}, headers={"X-Bot-Api-Secret-Token": SHARED + "x"}
                )
            async with get_sessionmaker()() as session:
                jobs = (
                    await session.execute(
                        text("select payload from jobs where idempotency_key like :k order by created_at").bindparams(
                            k=f"zalo:{world.bot_id}:%"
                        )
                    )
                ).scalars()
                payloads = list(jobs)
            assert len(payloads) == 3
            for payload in payloads:
                await handle_update(deps, None, payload)

            alert = {
                "incident_id": world.new_incident(),
                "family_id": str(world.family.id),
                "template": "fast_alert",
                "text": texts.guardian_fast_alert("Mẹ", "002", "bank", False),
                "guardian_rank": 1,
                "is_drill": False,
                "is_demo": True,
            }
            assert await send_to_guardian(deps, alert) == "sent"
            failing["on"] = True  # Zalo lỗi 500 kèm thân có token: lỗi gói lại không mang URL/thân
            second = {**alert, "incident_id": world.new_incident(), "template": "reminder"}
            second["text"] = texts.guardian_reminder("Mẹ", False)
            with pytest.raises(ZaloError) as info:
                await send_to_guardian(deps, second, attempt=1)
            logging.getLogger("leak-test").warning("lỗi gửi: %r %s", info.value, info.value)
    finally:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    assert len(calls) >= 4 and all(
        TOKEN in str(c.url) for c in calls
    )  # token thật sự đã đi trên URL, chỉ không lọt ra ngoài
    assert "/bot***/sendMessage" in caplog.text  # bộ lọc log đã che token (host công khai thì không cần che)
    forbidden = (TOKEN, "LEAKCANARY", SHARED, USER, CHAT, DISPLAY_NAME, code)
    observed = caplog.text + "\n".join(capsys.readouterr()) + "\n" + await dump_database(world.bot_id)
    observed += "".join(repr(vars(r)) for r in await world.rows())
    for needle in forbidden:
        assert needle not in observed, needle


async def test_no_raw_identifier_columns_exist(require_db: None) -> None:
    async with get_sessionmaker()() as session:
        rows = await session.execute(
            text(
                "select table_name, column_name from information_schema.columns"
                " where table_name in ('members', 'messages_out', 'pairing_codes', 'families')"
            )
        )
        columns = {(t, c) for t, c in rows}
    assert ("members", "zalo_chat_enc") in columns and ("members", "zalo_user_hmac") in columns
    for table, column in columns:
        assert column not in {"zalo_chat_id", "zalo_user_id", "chat_id", "user_id", "zalo_id", "display_name_zalo"}, (
            table,
            column,
        )
        assert "phone" not in column and "code" not in column.replace("code_hash", ""), (table, column)


def test_forbidden_markers_are_distinctive() -> None:
    """Dấu hiệu nhận biết phải đủ riêng để nếu lọt ra sẽ bị bắt (không trùng chuỗi vô tình có sẵn trong mẫu tin)."""
    for marker in ("LEAKCANARY",):
        assert marker not in json.dumps(texts.__dict__.get("QUESTIONS", {}))
        assert marker not in texts.pairing_confirmed()
