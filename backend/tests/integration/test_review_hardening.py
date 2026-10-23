"""Các sửa theo review bảo mật/UX ngày 15/10 cho spec 002 (mỗi test ứng với một phát hiện)."""

import dataclasses
import logging
import uuid
from typing import Any

import pytest
from consent_support import SHA, purge_family
from pydantic import SecretStr
from sqlalchemy import select, update

from hoicon.agents import texts
from hoicon.api import webhooks
from hoicon.channels.guardian import send_to_guardian
from hoicon.channels.updates import handle_update
from hoicon.channels.zalo import MockZaloClient, build_zalo_client
from hoicon.config import Settings
from hoicon.db.models import Consent, Family, Job, Member, MessageOut, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.jobs.queue import ATTEMPT_KEY, enqueue
from hoicon.jobs.worker import incident_handlers
from hoicon.ops import pairing_code
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


def alert(world: Any, **override: Any) -> dict[str, Any]:
    is_drill = override.get("is_drill", False)
    base = {
        "incident_id": world.new_incident(),
        "family_id": str(world.family.id),
        "template": "fast_alert",
        "text": texts.guardian_fast_alert("Mẹ", "002", "bank", is_drill),
        "guardian_rank": 1,
        "is_drill": is_drill,
        "is_demo": True,
    }
    return {**base, **override}


async def set_family_demo(world: Any, is_demo: bool) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(update(Family).where(Family.id == world.family.id).values(is_demo=is_demo))


async def test_real_incident_never_reaches_a_demo_family_either(zalo_world: Any) -> None:
    """Luật 8 đối xứng: demo ↔ thật không bao giờ lẫn (L8)."""
    world = zalo_world
    await world.add_guardian(1)
    assert await send_to_guardian(world.deps, alert(world, is_demo=False)) == "failed"
    assert (await world.rows())[0].error == "real_to_demo_family" and world.client.sent == []
    await set_family_demo(world, False)
    # spec 037: gia đình thật cần người cao tuổi đồng ý `guardian_alerts`
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=world.family.id,
                member_id=world.protected_id,
                purpose="guardian_alerts",
                granted=True,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()
    try:
        assert await send_to_guardian(world.deps, alert(world, is_demo=False)) == "sent"  # thật ↔ thật: đi
    finally:
        await purge_family(world.family.id)


async def test_drill_incident_message_without_the_drill_label_is_refused(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    unlabeled = texts.guardian_fast_alert("Mẹ", "002", "bank", False)  # thiếu nhãn dù sự cố là diễn tập
    assert await send_to_guardian(world.deps, alert(world, is_drill=True, text=unlabeled)) == "failed"
    assert (await world.rows())[0].error == "no_drill_label" and world.client.sent == []


async def test_messages_sent_by_the_mock_are_marked_so_nobody_mistakes_them_for_real_deliveries(
    zalo_world: Any,
) -> None:
    """C1: mock ghi `sent` nhưng tin không tới người nhận ⇒ đánh dấu error='mock'; client thật thì không."""
    world = zalo_world
    await world.add_guardian(1)
    await send_to_guardian(world.deps, alert(world))
    assert [r.error for r in await world.rows()] == ["mock"]

    @dataclasses.dataclass
    class PretendLive(MockZaloClient):
        simulated = False

    deps = dataclasses.replace(world.deps, client=PretendLive())
    await send_to_guardian(deps, alert(world))
    assert sorted(r.error or "" for r in await world.rows()) == ["", "mock"]


async def test_swapping_ciphertexts_between_guardians_cannot_redirect_an_alert(zalo_world: Any) -> None:
    """L4: bản mã `chat_enc` gắn với chủ sở hữu; ai chép bản mã của người khác sang hàng của mình thì giải mã hỏng."""
    world = zalo_world
    first, second = await world.add_guardian(1), await world.add_guardian(2)
    async with get_sessionmaker().begin() as session:
        await session.execute(update(Member).where(Member.id == first.id).values(zalo_chat_enc=second.zalo_chat_enc))
    assert await send_to_guardian(world.deps, alert(world)) == "fallback_required"
    assert (await world.rows())[0].error == "decrypt_failed" and world.client.sent == []


async def test_zalo_update_job_loses_its_ciphertext_and_code_hash_once_handled(zalo_world: Any) -> None:
    """M5: bản mã định danh và băm mã ghép không nằm lại trong `jobs.payload` sau khi xử lý xong."""
    world = zalo_world
    code = await world.make_code()
    payload = world.update_payload("fixture-user-scrub", kind="start", value=code, message_id="fixture-msg-scrub")
    await enqueue(world.deps.sessions, "zalo_update", payload, key=f"zalo:{world.bot_id}:fixture-msg-scrub")
    handler = incident_handlers(None, world.deps)["zalo_update"]  # type: ignore[arg-type]
    await handler({**payload, ATTEMPT_KEY: 1})
    async with get_sessionmaker()() as session:
        stored = await session.scalar(
            select(Job.payload).where(Job.idempotency_key == f"zalo:{world.bot_id}:fixture-msg-scrub")
        )
    assert "chat_enc" not in stored and "code_hash" not in stored
    assert (
        stored["kind"] == "start" and stored["bot_id"] == world.bot_id and stored["user_hmac"]
    )  # còn đủ để giới hạn tần suất
    assert len(await world.members()) == 1


async def test_failed_handling_keeps_the_payload_so_the_retry_can_still_reply(zalo_world: Any) -> None:
    world = zalo_world
    payload = world.update_payload("fixture-user-retry", kind="other", message_id="fixture-msg-retry")
    await enqueue(world.deps.sessions, "zalo_update", payload, key=f"zalo:{world.bot_id}:fixture-msg-retry")

    class Boom(MockZaloClient):
        async def send_message(self, chat_id: str, text: str) -> Any:
            from hoicon.channels.zalo import ZaloError

            raise ZaloError(500)

    deps = dataclasses.replace(world.deps, client=Boom())
    handler = incident_handlers(None, deps)["zalo_update"]  # type: ignore[arg-type]
    with pytest.raises(Exception):  # noqa: B017 — ZaloError (lỗi tạm) làm job thử lại
        await handler({**payload, ATTEMPT_KEY: 1})
    async with get_sessionmaker()() as session:
        stored = await session.scalar(
            select(Job.payload).where(Job.idempotency_key == f"zalo:{world.bot_id}:fixture-msg-retry")
        )
    assert "chat_enc" in stored  # chưa xong ⇒ chưa xóa


async def test_pairing_code_command_revokes_older_unused_codes_of_the_family(
    zalo_world: Any, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    world = zalo_world
    old = await world.make_code()
    await pairing_code.run(world.family.display_name)
    async with get_sessionmaker()() as session:
        rows = (await session.scalars(select(PairingCode).where(PairingCode.family_id == world.family.id))).all()
    assert len(rows) == 1 and rows[0].used_at is None  # chỉ còn mã mới
    await handle_update(world.deps, None, world.update_payload("fixture-user-old", kind="start", value=old))
    assert await world.members() == []  # mã cũ không còn dùng được


async def test_pairing_code_command_is_dev_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prod = Settings(_env_file=None, env="prod")
    monkeypatch.setattr(pairing_code, "get_settings", lambda: prod)
    assert await pairing_code.run("khong-bao-gio-duoc-tao") == 2
    assert "HOICON_ENV=dev" in capsys.readouterr().out


async def test_webhook_with_a_too_short_secret_fails_closed(zalo_world: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """L5: Zalo yêu cầu secret 8–256 ký tự; secret ngắn hơn bị coi là chưa cấu hình (503), không chấp nhận âm thầm."""
    from httpx import ASGITransport, AsyncClient

    world = zalo_world
    for secret in ("short", "x" * 257):
        settings = world.settings.model_copy(update={"zalo_webhook_secret": SecretStr(secret)})
        monkeypatch.setattr(webhooks, "get_settings", lambda s=settings: s)
        async with AsyncClient(transport=ASGITransport(app=webhooks.app), base_url="http://test") as http:
            response = await http.post(
                f"/webhooks/zalo/{world.bot_id}", json={}, headers={"X-Bot-Api-Secret-Token": secret}
            )
        assert response.status_code == 503


def test_mock_mode_warns_loudly_at_startup(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="hoicon.channels.zalo"):
        build_zalo_client(Settings(_env_file=None))
    assert "MOCK" in caplog.text and "KHÔNG được gửi thật" in caplog.text


async def test_rows_written_by_the_gate_never_lose_the_incident_flag_of_drills(zalo_world: Any) -> None:
    world = zalo_world
    await world.add_guardian(1)
    drill_text = texts.guardian_fast_alert("Mẹ", "002", "bank", True)
    assert await send_to_guardian(world.deps, alert(world, is_drill=True, text=drill_text)) == "sent"
    rows = await world.rows()
    assert rows[0].status == "sent" and world.client.sent[0].text.startswith("Đây là trợ lý AI HỏiCon. [DIỄN TẬP]")
    assert isinstance(rows[0], MessageOut)


async def test_repeatable_replies_are_not_urgent_so_a_guardian_cannot_burn_the_incident_reserve(
    zalo_world: Any,
) -> None:
    """T2: tin lặp lại được (detail_*, incident_closed…) không được bỏ qua ngưỡng giữ 95% — chỉ ack_* mới khẩn."""
    from hoicon.agents.runtime import IncidentRuntime  # noqa: F401 — chỉ để chắc import hợp lệ
    from hoicon.channels.updates import QUIET_TEMPLATES, _reply

    world = zalo_world
    assert {"detail_pending", "detail_resend", "incident_closed", "pairing_already"} <= QUIET_TEMPLATES
    member = await world.add_guardian(1)
    async with get_sessionmaker().begin() as session:
        for index in range(19):  # 95% của hạn mức test (20)
            session.add(
                MessageOut(
                    channel="zalo", bot_id=world.bot_id, template_id="seed", status="sent",
                    quota_month=__import__("hoicon.channels.guardian", fromlist=["quota_month"]).quota_month(),
                    job_key=f"seed:{world.bot_id}:{index}",
                )
            )  # fmt: skip
    payload = world.update_payload(world.zalo_ids[1][0], kind="choice", value="3")
    status = await _reply(
        world.deps,
        payload,
        "detail_resend",
        texts.detail_pending(False),
        1,
        member=member,
        incident_id=uuid.UUID(world.new_incident()),
    )
    assert status == "held_quota"  # tin lặp lại bị giữ ở ngưỡng 95%, dù có gắn sự cố
    ack = world.update_payload(world.zalo_ids[1][0], kind="choice", value="1")
    assert await _reply(world.deps, ack, "ack_safe", texts.guardian_ack("safe", False), 1, member=member) == "sent"


async def test_mock_is_refused_outside_dev_and_test() -> None:
    for env in ("prod", "staging", "ci"):
        with pytest.raises(RuntimeError, match="HOICON_ZALO_MODE=live"):
            build_zalo_client(Settings(_env_file=None, env=env))
    for env in ("dev", "test"):
        assert isinstance(build_zalo_client(Settings(_env_file=None, env=env)), MockZaloClient)


async def test_readyz_reports_the_send_mode(zalo_world: Any, service_keys: None) -> None:
    from httpx import ASGITransport, AsyncClient

    from hoicon.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        body = (await http.get("/readyz")).json()
    assert body["zalo_mode"] in ("mock", "live") and body["db"] == "up"


async def test_a_job_that_fails_for_good_still_loses_its_ciphertext(
    zalo_world: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2: lần thử cuối cũng lỗi (không phải lỗi gửi, vd. DB) ⇒ job dừng hẳn, bản mã không nằm lại trong `jobs`."""
    from hoicon.jobs import worker
    from hoicon.jobs.queue import MAX_ATTEMPTS

    world = zalo_world

    async def broken(*_: Any, **__: Any) -> None:
        raise RuntimeError("lỗi không phải lỗi gửi")

    monkeypatch.setattr(worker, "handle_update", broken)
    payload = world.update_payload("fixture-user-dead", kind="other", message_id="fixture-msg-dead")
    await enqueue(world.deps.sessions, "zalo_update", payload, key=f"zalo:{world.bot_id}:fixture-msg-dead")
    handler = incident_handlers(None, world.deps)["zalo_update"]  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        await handler({**payload, ATTEMPT_KEY: 1})  # chưa phải lần cuối: còn thử lại ⇒ giữ nguyên
    async with get_sessionmaker()() as session:
        before = await session.scalar(
            select(Job.payload).where(Job.idempotency_key == f"zalo:{world.bot_id}:fixture-msg-dead")
        )
    assert "chat_enc" in before
    with pytest.raises(RuntimeError):
        await handler({**payload, ATTEMPT_KEY: MAX_ATTEMPTS})
    async with get_sessionmaker()() as session:
        stored = await session.scalar(
            select(Job.payload).where(Job.idempotency_key == f"zalo:{world.bot_id}:fixture-msg-dead")
        )
    assert "chat_enc" not in stored
