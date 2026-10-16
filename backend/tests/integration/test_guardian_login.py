"""Kiểm thử spec 027 (FR-002, SC-001, SC-003): người giám hộ nhắn "4" ⇒ nhận liên kết đăng nhập web qua Zalo (mock).

Định danh Zalo HƯ CẤU; token thô chỉ được phép có trong tin đã gửi, không có trong DB, job hay log.
"""

import logging
import re
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from consent_support import call
from sqlalchemy import func, select, text

from hoicon.agents import texts
from hoicon.channels.guardian import quota_month
from hoicon.channels.inbound import ParsedUpdate, build_job_payload
from hoicon.channels.updates import handle_update
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import ActionToken, Incident, MessageOut
from hoicon.db.session import get_sessionmaker
from hoicon.services.action_token_service import hash_token

pytestmark = pytest.mark.integration

USER_1, USER_2, STRANGER = "fixture-user-1", "fixture-user-2", "fixture-stranger"
LINK = re.compile(r"/login/([A-Za-z0-9_-]{43})")
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Origin": "http://localhost:3100"}


async def pair(world: Any, user: str) -> Any:
    await handle_update(world.deps, None, world.update_payload(user, kind="start", value=await world.make_code()))
    return next(
        m for m in await world.members() if m.zalo_user_hmac == world.update_payload(user, kind="x")["user_hmac"]
    )


async def say_4(world: Any, user: str, *, message_id: str | None = None) -> str | None:
    payload = world.update_payload(user, kind="login", message_id=message_id)
    return await handle_update(world.deps, None, payload)


def raw_token(world: Any, user: str) -> str:
    [match] = [LINK.search(t) for t in world.sent_to(user) if LINK.search(t)][-1:]
    assert match is not None
    return match.group(1)


async def tokens_of(member_id: Any) -> list[ActionToken]:
    async with get_sessionmaker()() as session:
        query = select(ActionToken).where(ActionToken.member_id == member_id).order_by(ActionToken.created_at)
        return list((await session.scalars(query)).all())


# --- phân loại ở webhook: job không mang chữ thô ----------------------------------------------------------------


def test_webhook_classifies_4_into_a_login_job_without_the_text() -> None:
    parsed = ParsedUpdate("m-1", "u-1", "c-1", "Đăng nhập")
    payload = build_job_payload("bot-x", parsed)
    assert payload["kind"] == "login" and "choice" not in payload and "code_hash" not in payload
    assert "Đăng nhập" not in str(payload) and "u-1" not in str(payload) and "c-1" not in str(payload)


# --- FR-002: phát liên kết --------------------------------------------------------------------------------------


async def test_paired_guardian_gets_one_login_link_with_the_ai_disclosure(zalo_world: Any) -> None:
    world = zalo_world
    guardian = await pair(world, USER_1)
    started = time.monotonic()
    assert await say_4(world, USER_1) == "sent"
    assert time.monotonic() - started <= 5  # SC-001: liên kết ≤ 5 s ở máy chủ (mock)
    message = world.sent_to(USER_1)[-1]
    assert message.startswith(texts.AI_DISCLOSURE)
    url = LINK.search(message)
    assert url is not None and f"{world.settings.web_base_url.rstrip('/')}/login/" in message
    [row] = [r for r in await world.rows() if r.template_id == "login_link"]
    assert row.status == "sent" and row.member_id == guardian.id and row.incident_id is None
    [record] = await tokens_of(guardian.id)
    assert record.scope == "guardian_view" and record.incident_id is None and record.used_at is None
    assert record.token_hash == hash_token(url.group(1))
    lifetime = record.expires_at - record.created_at
    assert timedelta(minutes=14, seconds=50) <= lifetime <= timedelta(minutes=15, seconds=10)


@pytest.mark.parametrize("word", ["4", "web", "Đăng nhập", "dang nhap"])
async def test_every_spelling_of_the_command_works(zalo_world: Any, word: str) -> None:
    from hoicon.channels.inbound import classify

    assert classify(word) == ("login", None)


async def test_only_a_hash_is_stored_and_the_raw_token_is_nowhere_but_the_message(
    zalo_world: Any, caplog: pytest.LogCaptureFixture
) -> None:
    world = zalo_world
    caplog.set_level(logging.DEBUG)
    await pair(world, USER_1)
    await say_4(world, USER_1)
    raw = raw_token(world, USER_1)
    assert raw not in caplog.text
    needle = {"needle": f"%{raw}%"}
    queries = (
        text("select count(*) from jobs t where t::text like :needle"),
        text("select count(*) from messages_out t where t::text like :needle"),
        text("select count(*) from action_tokens t where t::text like :needle"),
    )
    async with get_sessionmaker()() as session:
        in_jobs, in_messages, in_tokens = [await session.scalar(query, needle) for query in queries]
    assert (in_jobs, in_messages, in_tokens) == (0, 0, 0)


async def test_a_new_link_kills_the_older_unused_one(zalo_world: Any) -> None:
    world = zalo_world
    guardian = await pair(world, USER_1)
    await say_4(world, USER_1)
    await say_4(world, USER_1)
    old, new = await tokens_of(guardian.id)
    assert old.used_at is not None and new.used_at is None


async def test_old_link_is_refused_by_the_session_endpoint_and_the_new_one_works(
    zalo_world: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()
    world = zalo_world
    await pair(world, USER_1)
    await say_4(world, USER_1)
    first = raw_token(world, USER_1)
    await say_4(world, USER_1)
    second = raw_token(world, USER_1)
    assert first != second
    assert (await call("POST", "/v1/guardian/session", json={"token": first}, headers=ORIGIN)).status_code == 410
    assert (await call("POST", "/v1/guardian/session", json={"token": second}, headers=ORIGIN)).status_code == 200


async def test_each_guardian_gets_their_own_link(zalo_world: Any) -> None:
    world = zalo_world
    first, second = await pair(world, USER_1), await pair(world, USER_2)
    await say_4(world, USER_1)
    await say_4(world, USER_2)
    assert raw_token(world, USER_1) != raw_token(world, USER_2)
    assert len(await tokens_of(first.id)) == 1 and len(await tokens_of(second.id)) == 1
    assert (await tokens_of(first.id))[0].used_at is None  # người kia xin link không đụng tới link của mình


async def test_the_same_zalo_message_delivered_twice_sends_one_link(zalo_world: Any) -> None:
    world = zalo_world
    guardian = await pair(world, USER_1)
    assert await say_4(world, USER_1, message_id="dup-1") == "sent"
    assert await say_4(world, USER_1, message_id="dup-1") == "sent"
    assert len([t for t in world.sent_to(USER_1) if LINK.search(t)]) == 1
    [record] = await tokens_of(guardian.id)
    assert record.used_at is None  # lần giao lại không vô hiệu liên kết vừa gửi


async def test_the_sixth_request_in_an_hour_is_declined_gently(zalo_world: Any) -> None:
    world = zalo_world
    guardian = await pair(world, USER_1)
    for _ in range(5):
        assert await say_4(world, USER_1) == "sent"
    assert await say_4(world, USER_1) == "sent"  # câu từ chối cũng là một tin trả lời
    last = world.sent_to(USER_1)[-1]
    assert last == texts.login_rate_limited() and not LINK.search(last)
    assert last.startswith(texts.AI_DISCLOSURE)
    assert len(await tokens_of(guardian.id)) == 5
    alive = [t for t in await tokens_of(guardian.id) if t.used_at is None]
    assert len(alive) == 1  # liên kết thứ 5 vẫn dùng được


async def test_requests_older_than_an_hour_do_not_count(zalo_world: Any) -> None:
    world = zalo_world
    guardian = await pair(world, USER_1)
    for _ in range(5):
        await say_4(world, USER_1)
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update action_tokens set created_at = :t where member_id = :m"),
            {"t": datetime.now(UTC) - timedelta(hours=2), "m": guardian.id},
        )
    assert await say_4(world, USER_1) == "sent"
    assert LINK.search(world.sent_to(USER_1)[-1])


async def test_unpaired_user_is_pointed_to_pairing_and_gets_no_token(zalo_world: Any) -> None:
    world = zalo_world
    assert await say_4(world, STRANGER) == "sent"
    assert world.sent_to(STRANGER)[-1] == texts.pairing_help()
    async with get_sessionmaker()() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(ActionToken)
                .where(
                    ActionToken.scope == "guardian_view",
                    ActionToken.created_at > func.now() - timedelta(minutes=1),
                    ActionToken.incident_id.is_(None),
                )
            )
            == 0
        )


async def test_login_does_not_touch_incidents_and_works_in_a_drill_family(zalo_world: Any) -> None:
    world = zalo_world
    await pair(world, USER_1)
    incident = world.new_incident()
    await say_4(world, USER_1)
    async with get_sessionmaker()() as session:
        row = await session.get(Incident, __import__("uuid").UUID(incident))
        assert row is not None and row.state == "detected" and row.version == 1
    assert LINK.search(world.sent_to(USER_1)[-1])


# --- review bảo mật 027 (#5, #6) ---------------------------------------------------------------------------------


async def test_a_retry_after_a_failed_send_does_not_use_up_the_hourly_limit(zalo_world: Any) -> None:
    """Zalo lỗi tạm thời ⇒ job thử lại cùng `message_id`: token của lần hỏng bị thay, không cộng dồn vào hạn mức."""
    from hoicon.channels.zalo import ZaloError

    world = zalo_world
    guardian = await pair(world, USER_1)
    real_send = world.client.send_message
    failures = {"left": 3}

    async def flaky(chat_id: str, text: str) -> Any:
        if failures["left"] > 0:
            failures["left"] -= 1
            raise ZaloError(503)
        return await real_send(chat_id, text)

    world.client.send_message = flaky
    payload = world.update_payload(USER_1, kind="login", message_id="retry-1")
    for attempt in range(1, 4):  # hàng đợi thử lại cùng một job
        with pytest.raises(ZaloError):
            await handle_update(world.deps, None, payload, attempt)
    assert await handle_update(world.deps, None, payload, 4) == "sent"
    alive = [t for t in await tokens_of(guardian.id) if t.used_at is None]
    assert len(await tokens_of(guardian.id)) == 1 and len(alive) == 1  # 4 lần thử ⇒ vẫn chỉ MỘT token, dùng được
    # Hạn mức giờ không bị 3 lần thử hỏng ăn mất: vẫn xin thêm được 4 liên kết nữa.
    for _ in range(4):
        assert await say_4(world, USER_1) == "sent"
        assert LINK.search(world.sent_to(USER_1)[-1])


async def test_the_login_link_is_urgent_so_a_held_quota_cannot_swallow_it(zalo_world: Any) -> None:
    """Gần hết hạn mức tháng, tin không khẩn bị giữ (`held_quota`); liên kết đăng nhập thì vẫn phải tới tay."""
    world = zalo_world
    await pair(world, USER_1)
    async with get_sessionmaker().begin() as session:
        for _ in range(18):  # hạn mức test = 20, ngưỡng giữ tin không khẩn = 19; tin ghép đôi đã tính 1
            session.add(
                MessageOut(
                    family_id=None,
                    channel="zalo",
                    bot_id=world.bot_id,
                    template_id="seed",
                    status="sent",
                    quota_month=quota_month(),
                    job_key=f"seed:{new_id()}",
                )
            )
    assert await say_4(world, USER_1) == "sent"
    assert LINK.search(world.sent_to(USER_1)[-1])
