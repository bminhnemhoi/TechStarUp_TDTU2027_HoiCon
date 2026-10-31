"""Spec 034 FR-005 / SC-004: máy chủ thực thi đồng ý. `core_protection` rút/chưa có ⇒ 403 `consent_withdrawn` và không
ghi gì; chưa đồng ý `guardian_alerts` ⇒ vẫn nhận sự kiện (an toàn người cao tuổi) nhưng không xếp tin Zalo."""

from typing import Any
from uuid import UUID

import pytest
from consent_support import call, item, pair_device, purge_family
from sqlalchemy import func, select
from test_api_events import harmless, make_event, post
from test_incident_graph import deps

from hoicon.agents.runtime import IncidentRuntime, prepare_event
from hoicon.agents.spike import demo_event
from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Family, Incident, Job, RiskEventRecord
from hoicon.db.session import get_sessionmaker
from hoicon.ops.pairing_code import create_pairing_code
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def fresh_cache() -> None:
    consent_gate.reset_cache()


async def device(device_world: Any, *purposes: str) -> tuple[str, UUID, UUID]:
    """Ghép một thiết bị, chỉ ghi đồng ý cho `purposes` (qua API thật) ⇒ (token, family_id, member_id)."""
    paired = await pair_device(device_world.code, consent=False)
    token = paired["access_token"]
    me = (await call("GET", "/v1/devices/me", token=token)).json()["device"]
    if purposes:
        resp = await call("POST", "/v1/consents", token=token, json={"items": [item(p) for p in purposes]})
        assert resp.status_code == 200, resp.text
    return token, UUID(me["family_id"]), UUID(me["member_id"])


async def consent(token: str, purpose: str, granted: bool) -> None:
    resp = await call("POST", "/v1/consents", token=token, json={"items": [item(purpose, granted=granted)]})
    assert resp.status_code == 200, resp.text


async def rows(model: Any, family_id: UUID) -> int:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(func.count()).select_from(model).where(model.family_id == family_id)) or 0


async def notify_jobs(incident_id: str) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(
            await session.scalars(
                select(Job).where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{incident_id}:"))
            )
        )


# --- core_protection (SC-004) ---------------------------------------------------------------------------------------


async def test_a_device_with_no_consent_at_all_is_refused_and_nothing_is_written(device_world: Any) -> None:
    token, family_id, _ = await device(device_world)
    resp = await post(token, make_event())
    assert resp.status_code == 403 and resp.json() == {"detail": "consent_withdrawn"}
    assert await rows(RiskEventRecord, family_id) == 0 and await rows(Incident, family_id) == 0


async def test_withdrawing_core_protection_stops_events_and_granting_again_resumes_them(device_world: Any) -> None:
    token, family_id, _ = await device(device_world, "core_protection", "guardian_alerts")
    assert (await post(token, harmless())).status_code == 200
    await consent(token, "core_protection", False)
    refused = await post(token, make_event())
    assert refused.status_code == 403 and refused.json() == {"detail": "consent_withdrawn"}
    assert await rows(RiskEventRecord, family_id) == 1  # chỉ sự kiện đã nhận trước khi rút
    assert await rows(Incident, family_id) == 0
    await consent(token, "core_protection", True)
    assert (await post(token, harmless())).status_code == 200
    assert await rows(RiskEventRecord, family_id) == 2


@pytest.mark.parametrize("other", ["guardian_alerts", "call_screening", "usage_monitoring", "drills", "lookups"])
async def test_other_purposes_do_not_stand_in_for_core_protection(device_world: Any, other: str) -> None:
    token, family_id, _ = await device(device_world, other)
    assert (await post(token, make_event())).status_code == 403
    assert await rows(RiskEventRecord, family_id) == 0


async def test_a_malformed_batch_is_still_422_before_the_consent_check(device_world: Any) -> None:
    """FastAPI kiểm thân yêu cầu trước khi vào hàm xử lý, nên lô sai cấu trúc vẫn là 422 dù chưa đồng ý. Chốt hành vi
    này để không đổi âm thầm."""
    token, _, _ = await device(device_world)
    assert (await call("POST", "/v1/events", token=token, json={"events": []})).status_code == 422


# --- đệm 60 giây ----------------------------------------------------------------------------------------------------


async def test_the_state_is_cached_for_60_seconds_and_a_new_consent_through_the_api_clears_it(
    device_world: Any,
) -> None:
    token, _, member_id = await device(device_world, "core_protection", "guardian_alerts")
    assert (await post(token, harmless())).status_code == 200  # nạp đệm
    async with get_sessionmaker().begin() as session:  # rút đồng ý NGOÀI API (kênh khác): đệm chưa biết
        session.add(
            Consent(
                family_id=device_world.family_id,
                member_id=member_id,
                purpose="core_protection",
                granted=False,
                consent_version="v1.0",
                text_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                channel="zalo",
            )
        )
    assert (await post(token, harmless())).status_code == 200  # trễ tối đa 60 giây là chấp nhận được (D5)
    consent_gate.invalidate(member_id)
    assert (await post(token, harmless())).status_code == 403


async def test_a_consent_written_through_the_api_takes_effect_immediately(device_world: Any) -> None:
    token, _, member_id = await device(device_world, "core_protection", "guardian_alerts")
    assert (await post(token, harmless())).status_code == 200  # nạp đệm
    assert member_id in consent_gate._cache
    await consent(token, "core_protection", False)
    assert member_id not in consent_gate._cache  # /v1/consents xóa đệm của chính người đó
    assert (await post(token, harmless())).status_code == 403


async def test_a_cached_entry_expires_after_60_seconds(device_world: Any) -> None:
    _, _, member_id = await device(device_world, "core_protection")
    async with get_sessionmaker()() as session:
        first = await consent_gate.state_for(session, member_id, now=1000.0)
    assert (first.core_protection, first.guardian_alerts) == (True, False)
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=device_world.family_id,
                member_id=member_id,
                purpose="guardian_alerts",
                granted=True,
                consent_version="v1.0",
                text_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                channel="app",
            )
        )
    async with get_sessionmaker()() as session:
        assert (await consent_gate.state_for(session, member_id, now=1059.9)).guardian_alerts is False  # còn đệm
        assert (await consent_gate.state_for(session, member_id, now=1060.0)).guardian_alerts is True  # hết đệm


async def test_the_cache_is_per_member(device_world: Any) -> None:
    token, _, _ = await device(device_world, "core_protection")
    assert (await post(token, harmless())).status_code == 200
    async with get_sessionmaker().begin() as session:
        other = Family(display_name="test-034-other", region="nam", is_demo=True)
        session.add(other)
        await session.flush()
        other_id = other.id
    try:
        code = await create_pairing_code(get_sessionmaker(), other_id)
        other_token = (await pair_device(code, consent=False))["access_token"]  # người khác, chưa đồng ý
        assert (await post(other_token, harmless())).status_code == 403
        assert (await post(token, harmless())).status_code == 200  # người đầu không bị ảnh hưởng
    finally:
        await purge_family(other_id)


# --- guardian_alerts ------------------------------------------------------------------------------------------------


async def test_without_guardian_alerts_the_incident_opens_but_no_message_is_queued(device_world: Any) -> None:
    from hoicon.db.models import Member

    token, family_id, _ = await device(device_world, "core_protection")
    async with get_sessionmaker().begin() as session:  # có người giám hộ thật: nếu không có cổng thì tin SẼ được xếp
        session.add(Member(family_id=family_id, role="guardian", guardian_rank=1))
    resp = await post(token, make_event())  # sàn "high" ⇒ mở sự cố
    assert resp.status_code == 200 and resp.json()["incident_opened"] is True
    incident_id = resp.json()["incident_id"]
    assert await rows(Incident, family_id) == 1
    assert await notify_jobs(incident_id) == []
    async with get_sessionmaker()() as session:
        start = await session.scalar(select(Job).where(Job.idempotency_key == f"{incident_id}:graph:start"))
    assert start is not None and start.payload["guardian_alerts"] is False  # đồ thị vẫn chạy, nhưng không gửi tin


async def test_with_guardian_alerts_the_fast_alert_is_queued_as_before(device_world: Any) -> None:
    from hoicon.db.models import Member

    token, family_id, _ = await device(device_world, "core_protection", "guardian_alerts")
    async with get_sessionmaker().begin() as session:
        session.add(Member(family_id=family_id, role="guardian", guardian_rank=1))
    incident_id = (await post(token, make_event())).json()["incident_id"]
    assert [j.idempotency_key for j in await notify_jobs(incident_id)] == [f"{incident_id}:msg:fast_alert"]
    async with get_sessionmaker()() as session:
        start = await session.scalar(select(Job).where(Job.idempotency_key == f"{incident_id}:graph:start"))
    assert start is not None and start.payload["guardian_alerts"] is True


async def test_withdrawing_guardian_alerts_stops_new_messages(device_world: Any) -> None:
    from hoicon.db.models import Member

    token, family_id, _ = await device(device_world, "core_protection", "guardian_alerts")
    async with get_sessionmaker().begin() as session:
        session.add(Member(family_id=family_id, role="guardian", guardian_rank=1))
    await consent(token, "guardian_alerts", False)
    incident_id = (await post(token, make_event())).json()["incident_id"]
    assert await notify_jobs(incident_id) == []


async def test_the_graph_queues_no_guardian_message_without_the_consent(threads: list[str]) -> None:
    """Đường đồ thị (xác minh, nhắc, chuyển cấp…) cũng im lặng khi `guardian_alerts=False`."""
    d = deps()
    thread = str(new_id())
    threads.append(thread)
    event = demo_event()
    async with IncidentRuntime.open(d) as runtime:
        threat, event_data = await prepare_event(d.sessions, event)
        await runtime.start_prepared(
            event_data, threat, incident_id=thread, elder_alias="Mẹ", is_demo=True, guardian_alerts=False
        )
    async with get_sessionmaker()() as session:
        queued = list(
            await session.scalars(
                select(Job).where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{thread}:"))
            )
        )
    assert queued == []


async def test_the_graph_still_queues_messages_when_alerts_are_allowed(threads: list[str]) -> None:
    d = deps()
    thread = str(new_id())
    threads.append(thread)
    async with IncidentRuntime.open(d) as runtime:
        threat, event_data = await prepare_event(d.sessions, demo_event())
        await runtime.start_prepared(event_data, threat, incident_id=thread, elder_alias="Mẹ", is_demo=True)
    async with get_sessionmaker()() as session:
        queued = list(
            await session.scalars(
                select(Job).where(Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{thread}:"))
            )
        )
    assert queued, "đường mặc định không đổi: đồ thị xếp tin cho người giám hộ"
