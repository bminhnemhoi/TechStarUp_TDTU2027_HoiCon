"""Kiểm thử tích hợp spec 023 (cảnh báo người giám hộ & trang hành động `/a/[token]`) trên Postgres thật.

1. Sự cố mức cao ⇒ xếp ĐÚNG MỘT job `notify_guardian`; job không chứa token thô (chỉ chỗ trống), token sinh lúc gửi.
2. `GET /v1/action/{token}` đúng hợp đồng `action_view.v1.json`, không PII; sự cố đã xử lý ⇒ `token_valid=false`.
3. `POST /v1/action/{token}/decision` đóng sự cố + tiêu token trong một giao dịch; bấm lại ⇒ 409.
4. `POST /v1/incidents/{id}/decision` (JWT người giám hộ) chỉ trong gia đình mình.
5. Trả lời Zalo "1" ⇒ `resolved_safe`; "2 - vẫn thấy đáng ngờ" ⇒ `case_open` (không đóng sự cố).
6. Luồng máy chủ đầu–cuối: `POST /v1/events` ⇒ job ⇒ gửi (Zalo mock) ⇒ mở liên kết ⇒ quyết định ⇒ sự cố đóng, 0 PII.
"""

import json
import re
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, pair_device, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import String, cast, delete, func, select

from hoicon.agents.texts import ACTION_LINK_SLOT, AI_DISCLOSURE
from hoicon.api.auth import issue_guardian_access_token
from hoicon.channels.guardian import ChannelDeps, send_to_guardian
from hoicon.channels.updates import handle_update
from hoicon.channels.zalo import MockZaloClient
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import ActionToken, Family, Incident, Job, Member, MessageOut
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import encrypt_chat_id, hmac_zalo
from hoicon.services.action_token_service import ActionTokenService, hash_token
from hoicon.services.alert_service import AlertService

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
ACTION_VIEW = Draft202012Validator(
    json.loads((SCHEMAS / "action_view.v1.json").read_text(encoding="utf-8")), format_checker=FormatChecker()
)
EVENT = json.loads((SCHEMAS / "fixtures" / "risk_event.v1.valid.json").read_text(encoding="utf-8"))[0]
RAW_PHONE = re.compile(r"(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}")
LINK = re.compile(r"/a/([A-Za-z0-9_-]{43})")
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test


async def add_guardian(family_id: UUID, user_id: str = "zalo-user-023") -> tuple[Member, dict[str, Any]]:
    """Người giám hộ hạng 1 đã ghép Zalo (định danh HƯ CẤU) ⇒ (member, khung payload trả lời Zalo)."""
    bot_id = f"bot-{new_id().hex[:8]}"
    kid, user_hmac = hmac_zalo(bot_id, user_id)
    chat_enc = encrypt_chat_id(f"chat-{user_id}", user_hmac)
    async with get_sessionmaker().begin() as session:
        guardian = Member(
            family_id=family_id,
            role="guardian",
            guardian_rank=1,
            zalo_bot_id=bot_id,
            zalo_user_hmac=user_hmac,
            zalo_hmac_kid=kid,
            zalo_chat_enc=chat_enc,
        )
        session.add(guardian)
    reply = {"bot_id": bot_id, "user_hmac": user_hmac, "hmac_kid": kid, "chat_enc": chat_enc, "kind": "choice"}
    return guardian, reply


@pytest.fixture
async def world(zalo_env: None, require_db: None, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[dict[str, Any]]:
    """Gia đình demo: 1 người được bảo vệ ("Mẹ") + 1 người giám hộ đã ghép Zalo; khóa GIẢ; dọn sạch sau test."""
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()
    async with get_sessionmaker().begin() as session:
        family = Family(display_name="Gia đình mẫu 023", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add(protected)
        await session.flush()
        family_id, protected_id = family.id, protected.id
    guardian, reply = await add_guardian(family_id)
    created: list[UUID] = []
    yield {
        "family": family_id,
        "protected": protected_id,
        "guardian": guardian.id,
        "reply": reply,
        "incidents": created,
    }
    async with get_sessionmaker().begin() as session:
        for incident in created:
            await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{incident}:", autoescape=True)))
    await purge_family(family_id)
    get_settings.cache_clear()


async def new_incident(w: dict[str, Any], state: str = "awaiting_guardian", **changes: Any) -> Incident:
    async with get_sessionmaker().begin() as session:
        incident = Incident(
            family_id=w["family"],
            member_id=w["protected"],
            state=state,
            level="high",
            rule_floor="high",
            is_demo=True,
            **changes,
        )
        session.add(incident)
        await session.flush()
    w["incidents"].append(incident.id)
    return incident


async def new_token(w: dict[str, Any], incident: Incident) -> str:
    async with get_sessionmaker().begin() as session:
        _, raw = await ActionTokenService.create_token(session, incident_id=incident.id, member_id=w["guardian"])
    return raw


async def fast_alert_job(incident_id: UUID) -> Job | None:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(Job).where(Job.idempotency_key == f"{incident_id}:msg:fast_alert"))


async def state_of(incident_id: UUID) -> Incident:
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        return incident


# --- FR-003: xếp cảnh báo, token chỉ sinh lúc gửi ------------------------------------------------------------------


async def test_fast_alert_job_never_carries_a_raw_token(world: dict[str, Any]) -> None:
    incident = await new_incident(world, state="detected")
    async with get_sessionmaker().begin() as session:
        assert await AlertService.trigger_guardian_fast_alert(session, incident=incident) is True
        assert await AlertService.trigger_guardian_fast_alert(session, incident=incident) is False  # chống trùng

    job = await fast_alert_job(incident.id)
    assert job is not None and job.kind == "notify_guardian"
    assert job.payload["action_link"] is True and ACTION_LINK_SLOT in job.payload["text"]
    assert "/a/" not in job.payload["text"].replace(ACTION_LINK_SLOT, "")
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).where(ActionToken.incident_id == incident.id)) == 0

    client = MockZaloClient()
    assert await send_to_guardian(ChannelDeps(get_sessionmaker(), client, get_settings()), job.payload) == "sent"
    [sent] = client.sent
    assert sent.text.startswith(AI_DISCLOSURE) and "Mẹ vừa nghe một cuộc gọi lạ" in sent.text
    match = LINK.search(sent.text)
    assert match is not None and ACTION_LINK_SLOT not in sent.text
    raw = match.group(1)
    async with get_sessionmaker()() as session:
        record = await ActionTokenService.get_token_record(session, raw)
        assert record is not None and record.token_hash == hash_token(raw) and record.member_id == world["guardian"]
        leaked = await session.scalar(select(func.count()).where(cast(Job.payload, String).contains(raw)))
        assert leaked == 0

    # Job chạy lại sau khi đã gửi ⇒ không gửi lần hai, không sinh thêm token
    assert await send_to_guardian(ChannelDeps(get_sessionmaker(), client, get_settings()), job.payload) == "sent"
    async with get_sessionmaker()() as session:
        assert await session.scalar(select(func.count()).where(ActionToken.incident_id == incident.id)) == 1
    assert len(client.sent) == 1


async def test_family_without_guardian_queues_nothing(world: dict[str, Any]) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Member).where(Member.id == world["guardian"]))
    incident = await new_incident(world, state="detected")
    async with get_sessionmaker().begin() as session:
        assert await AlertService.trigger_guardian_fast_alert(session, incident=incident) is False
    assert await fast_alert_job(incident.id) is None


# --- FR-004 / FR-005: trang hành động ------------------------------------------------------------------------------


async def test_action_view_matches_the_contract_and_hides_pii(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    raw = await new_token(world, incident)
    res = await call("GET", f"/v1/action/{raw}")
    assert res.status_code == 200
    data = res.json()
    assert [e.message for e in ACTION_VIEW.iter_errors(data)] == []
    assert data["token_valid"] is True and data["incident"]["protected_member_label"] == "Mẹ"
    assert not RAW_PHONE.search(res.text)
    assert (await call("GET", "/v1/action/khong-ton-tai-0123456789abcdef")).status_code == 404


async def test_decision_closes_the_incident_and_burns_the_token(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    raw = await new_token(world, incident)
    res = await call("POST", f"/v1/action/{raw}/decision", json={"decision": "safe"})
    assert res.status_code == 200
    assert res.json() == {"success": True, "incident_id": str(incident.id), "state": "resolved_safe", "outcome": "safe"}
    closed = await state_of(incident.id)
    assert closed.state == "resolved_safe" and closed.closed_at is not None
    async with get_sessionmaker()() as session:
        record = await ActionTokenService.get_token_record(session, raw)
        assert record is not None and record.used_at is not None

    again = await call("POST", f"/v1/action/{raw}/decision", json={"decision": "prevented"})
    assert again.status_code == 409
    view = (await call("GET", f"/v1/action/{raw}")).json()
    assert view["token_valid"] is False and view["used_at"] is not None


async def test_suspected_scam_opens_a_case_instead_of_closing(world: dict[str, Any]) -> None:
    incident = await new_incident(world, state="detected")
    raw = await new_token(world, incident)
    res = await call("POST", f"/v1/action/{raw}/decision", json={"decision": "emergency_pause"})
    assert res.status_code == 200 and res.json()["state"] == "case_open"
    opened = await state_of(incident.id)
    assert opened.closed_at is None and opened.outcome is None


async def test_unknown_decision_or_expired_link(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    raw = await new_token(world, incident)
    assert (await call("POST", f"/v1/action/{raw}/decision", json={"decision": "transfer"})).status_code == 422
    async with get_sessionmaker().begin() as session:
        record = await ActionTokenService.get_token_record(session, raw)
        assert record is not None
        record.expires_at = record.created_at
    assert (await call("POST", f"/v1/action/{raw}/decision", json={"decision": "safe"})).status_code == 410
    assert (await state_of(incident.id)).state == "awaiting_guardian"


# --- FR-006: JWT người giám hộ -------------------------------------------------------------------------------------


async def test_guardian_jwt_decides_only_inside_the_family(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    stranger = await call(
        "POST",
        f"/v1/incidents/{incident.id}/decision",
        token=issue_guardian_access_token(new_id(), new_id()),
        json={"decision": "safe"},
    )
    assert stranger.status_code == 401
    assert (await call("POST", f"/v1/incidents/{incident.id}/decision", json={"decision": "safe"})).status_code == 401

    token = issue_guardian_access_token(world["guardian"], world["family"])
    res = await call("POST", f"/v1/incidents/{incident.id}/decision", token=token, json={"decision": "prevented"})
    assert res.status_code == 200 and res.json()["state"] == "resolved_prevented"
    again = await call("POST", f"/v1/incidents/{incident.id}/decision", token=token, json={"decision": "safe"})
    assert again.status_code == 409
    missing = await call("POST", f"/v1/incidents/{new_id()}/decision", token=token, json={"decision": "safe"})
    assert missing.status_code == 404


# --- FR-007: trả lời Zalo 1/2 --------------------------------------------------------------------------------------


async def _zalo_reply(world: dict[str, Any], incident: Incident, choice: str) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            MessageOut(
                bot_id=world["reply"]["bot_id"],
                family_id=world["family"],
                member_id=world["guardian"],
                incident_id=incident.id,
                channel="zalo",
                template_id="fast_alert",
                status="sent",
                sent_at=func.now(),
                quota_month="2026-10",
                job_key=f"{incident.id}:msg:fast_alert",
            )
        )
    deps = ChannelDeps(get_sessionmaker(), MockZaloClient(), get_settings())
    payload = {**world["reply"], "message_id": f"reply-{new_id().hex[:8]}", "choice": choice}
    assert await handle_update(deps, None, payload) is not None


async def test_zalo_reply_1_closes_as_safe(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    raw = await new_token(world, incident)
    await _zalo_reply(world, incident, "1")
    closed = await state_of(incident.id)
    assert closed.state == "resolved_safe" and closed.outcome == "safe"
    assert (await call("GET", f"/v1/action/{raw}")).json()["token_valid"] is False  # liên kết hết tác dụng


async def test_zalo_reply_2_keeps_the_incident_open_as_a_case(world: dict[str, Any]) -> None:
    incident = await new_incident(world)
    await _zalo_reply(world, incident, "2")
    case = await state_of(incident.id)
    assert case.state == "case_open" and case.closed_at is None


# --- SC-006 (phần máy chủ): đầu–cuối qua API thật -----------------------------------------------------------------


async def test_m1_server_flow_event_to_closed_incident_without_pii(zalo_env: None, device_world: Any) -> None:
    access = (await pair_device(device_world.code))["access_token"]
    await add_guardian(device_world.family_id, "zalo-user-m1")
    event = {**EVENT, "id": str(new_id())}

    started = time.monotonic()
    res = await call("POST", "/v1/events", token=access, json={"events": [event]})
    assert res.status_code == 200, res.text
    incident_id = UUID(res.json()["incident_id"])
    try:
        job = await fast_alert_job(incident_id)
        assert job is not None
        client = MockZaloClient()
        assert await send_to_guardian(ChannelDeps(get_sessionmaker(), client, get_settings()), job.payload) == "sent"
        alert_s = time.monotonic() - started
        [sent] = client.sent
        assert sent.text.startswith(AI_DISCLOSURE) and "đuôi 000" in sent.text
        match = LINK.search(sent.text)
        assert match is not None
        raw = match.group(1)

        view = await call("GET", f"/v1/action/{raw}")
        assert view.status_code == 200 and view.json()["token_valid"] is True
        decided = await call("POST", f"/v1/action/{raw}/decision", json={"decision": "safe"})
        assert decided.status_code == 200 and decided.json()["state"] == "resolved_safe"

        async with get_sessionmaker()() as session:
            payloads = [
                str(p)
                for p in await session.scalars(
                    select(Job.payload).where(Job.idempotency_key.startswith(f"{incident_id}:"))
                )
            ]
            tokens = list(
                await session.scalars(select(ActionToken.token_hash).where(ActionToken.incident_id == incident_id))
            )
        assert payloads and not any(raw in p or RAW_PHONE.search(p) for p in payloads)
        assert tokens == [hash_token(raw)]
        assert alert_s < 10, f"xếp + gửi (Zalo mock, trong tiến trình) mất {alert_s:.2f}s"
        print(f"\nM1 máy chủ: sự kiện → tin cảnh báo (Zalo mock) {alert_s * 1000:.0f} ms")
    finally:
        async with get_sessionmaker().begin() as session:
            await session.execute(delete(Job).where(Job.idempotency_key.startswith(f"{incident_id}:", autoescape=True)))
