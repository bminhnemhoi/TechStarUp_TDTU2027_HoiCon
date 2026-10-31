"""Spec 021 (FR-004, FR-008, FR-009, SC-001, SC-004, SC-005): `POST /v1/events`."""

import asyncio
import copy
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, pair_device
from drill_support import running_drill_for
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import delete, func, select, text

from hoicon.db.ids import new_id
from hoicon.db.models import Incident, IncidentTransition, RiskEventRecord, Verification
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_h1

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
RESULT = json.loads((SCHEMAS / "events_result.v1.json").read_text(encoding="utf-8"))
BASE = json.loads((SCHEMAS / "fixtures" / "risk_event.v1.valid.json").read_text(encoding="utf-8"))[0]
FAKE_H1 = "3f1c9a5e2b7d4c8a6e0f1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f6a"  # băm HƯ CẤU, không phải số thật


def make_event(**changes: Any) -> dict[str, Any]:
    event = copy.deepcopy(BASE)
    event["id"] = str(new_id())
    event["occurred_at"] = "2026-12-01T02:15:30.120Z"
    event.update(changes)
    return event


def harmless(**changes: Any) -> dict[str, Any]:
    """Sự kiện không đủ điều kiện mở sự cố."""
    return make_event(type="call_ended", rule_floor="none", rule_id=None, **changes)


def valid_result(doc: Any) -> list[str]:
    return [e.message for e in Draft202012Validator(RESULT, format_checker=FormatChecker()).iter_errors(doc)]


async def post(token: str | None, *events: dict[str, Any]) -> Any:
    return await call("POST", "/v1/events", token=token, json={"events": list(events)})


@pytest.fixture
async def token(device_world: Any) -> str:
    return (await pair_device(device_world.code))["access_token"]


async def count(model: Any, family_id: Any) -> int:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(func.count()).select_from(model).where(model.family_id == family_id)) or 0


# --- xác thực -----------------------------------------------------------------------------------------------------


async def test_requires_a_device_token(device_world: Any) -> None:
    assert (await post(None, make_event())).status_code == 401
    assert (await post("not-a-token", make_event())).status_code == 401
    assert await count(RiskEventRecord, device_world.family_id) == 0


async def test_revoked_device_is_refused(device_world: Any, token: str) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update devices set revoked_at = now() where family_id = :f"), {"f": device_world.family_id}
        )
    assert (await post(token, make_event())).status_code == 401
    assert await count(RiskEventRecord, device_world.family_id) == 0


# --- nhận lô + chống trùng (SC-001) -------------------------------------------------------------------------------


async def test_valid_batch_is_stored_with_identity_from_the_token(device_world: Any, token: str) -> None:
    ev = make_event()
    resp = await post(token, ev, harmless())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert valid_result(body) == [] and (body["accepted"], body["duplicates"]) == (2, 0)
    async with get_sessionmaker()() as session:
        row = await session.get(RiskEventRecord, UUID(ev["id"]))
    assert row is not None and row.family_id == device_world.family_id  # lấy từ token, không từ thân yêu cầu
    assert (row.type, row.rule_id, row.rule_floor, row.app_category, row.app_package) == (
        "banking_app_foreground",
        "R1",
        "high",
        "bank",
        "vn.hoicon.demobank",
    )
    assert (row.timing_detect_ms, row.timing_pause_ms, row.call_duration_s) == (940, 1610, 212)
    assert (row.caller_last3, row.caller_in_contacts, row.is_drill) == ("000", False, False)
    assert row.occurred_at.isoformat().startswith("2026-12-01T02:15:30") and row.received_at is not None


async def test_resending_the_same_batch_creates_nothing_new(device_world: Any, token: str) -> None:
    events = [make_event(), harmless(), harmless()]
    first = (await post(token, *events)).json()
    second = await post(token, *events)
    assert second.status_code == 200 and valid_result(second.json()) == []
    assert (first["accepted"], first["duplicates"]) == (3, 0)
    assert (second.json()["accepted"], second.json()["duplicates"]) == (0, 3)
    assert await count(RiskEventRecord, device_world.family_id) == 3
    assert await count(Incident, device_world.family_id) == 1  # gửi lại không mở thêm sự cố
    assert second.json()["incident_id"] is None and second.json()["incident_opened"] is False


async def test_partial_overlap_and_repeats_inside_one_batch(device_world: Any, token: str) -> None:
    old, fresh = harmless(), harmless()
    await post(token, old)
    resp = (await post(token, old, fresh, fresh)).json()  # `fresh` lặp ngay trong lô
    assert (resp["accepted"], resp["duplicates"]) == (1, 2)
    assert await count(RiskEventRecord, device_world.family_id) == 2


async def test_concurrent_identical_batches_store_each_event_once(device_world: Any, token: str) -> None:
    events = [make_event(), harmless(), harmless()]
    results = await asyncio.gather(*(post(token, *events) for _ in range(5)))
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    assert sum(r.json()["accepted"] for r in results) == 3
    assert sum(r.json()["duplicates"] for r in results) == 12
    assert await count(RiskEventRecord, device_world.family_id) == 3
    assert await count(Incident, device_world.family_id) == 1


async def test_another_familys_event_id_cannot_overwrite_or_attach(device_world: Any, token: str) -> None:
    ev = make_event()
    await post(token, ev)
    from consent_support import purge_family

    from hoicon.db.models import Family
    from hoicon.ops.pairing_code import create_pairing_code

    async with get_sessionmaker().begin() as session:
        other = Family(display_name=f"{device_world.display_name}-b", region="bac", is_demo=True)
        session.add(other)
        await session.flush()
        other_id = other.id
    try:
        code = await create_pairing_code(get_sessionmaker(), other_id)
        other_token = (await pair_device(code))["access_token"]
        resp = (await post(other_token, {**ev, "type": "call_ended", "rule_floor": "none", "rule_id": None})).json()
        assert (resp["accepted"], resp["duplicates"]) == (0, 1)
        assert await count(RiskEventRecord, other_id) == 0
        async with get_sessionmaker()() as session:
            row = await session.get(RiskEventRecord, UUID(ev["id"]))
        assert row is not None and row.family_id == device_world.family_id and row.type == "banking_app_foreground"
    finally:
        await purge_family(other_id)


# --- mở / liên kết sự cố (FR-008, SC-004) -------------------------------------------------------------------------


async def test_high_floor_opens_an_incident(device_world: Any, token: str) -> None:
    ev = make_event()
    body = (await post(token, ev)).json()
    assert body["incident_opened"] is True and body["incident_id"] is not None
    async with get_sessionmaker()() as session:
        incident = (await session.scalars(select(Incident).where(Incident.family_id == device_world.family_id))).one()
        assert str(incident.id) == body["incident_id"]
        assert (incident.state, incident.level, incident.rule_floor, incident.is_drill, incident.is_demo) == (
            "detected",
            "high",
            "high",
            False,
            True,
        )
        assert str(incident.opened_by_event_id) == ev["id"]
        steps = (
            await session.scalars(select(IncidentTransition).where(IncidentTransition.incident_id == incident.id))
        ).all()
        assert [(s.from_state, s.to_state, s.actor) for s in steps] == [(None, "detected", "device")]


async def test_harmless_events_open_no_incident(device_world: Any, token: str) -> None:
    body = (await post(token, harmless())).json()
    assert (body["incident_id"], body["incident_opened"]) == (None, False)
    assert await count(Incident, device_world.family_id) == 0


async def test_following_events_join_the_open_incident(device_world: Any, token: str) -> None:
    first = (await post(token, make_event())).json()
    follow = make_event(type="safe_pause_shown", rule_floor="none", rule_id=None)
    second = (await post(token, follow)).json()
    assert second["incident_opened"] is False and second["incident_id"] == first["incident_id"]
    assert await count(Incident, device_world.family_id) == 1
    async with get_sessionmaker()() as session:
        linked = await session.scalar(
            select(RiskEventRecord.incident_id).where(RiskEventRecord.id == UUID(follow["id"]))
        )
    assert str(linked) == first["incident_id"]


async def test_drill_events_make_a_drill_incident(device_world: Any, token: str) -> None:
    drill_id = str(await running_drill_for(token))  # spec 028 D2: cờ diễn tập chỉ được tin khi khớp bài `in_progress`
    body = (await post(token, make_event(is_drill=True, drill_id=drill_id))).json()
    async with get_sessionmaker()() as session:
        incident = await session.get(Incident, UUID(body["incident_id"]))
    assert incident is not None and incident.is_drill is True and str(incident.drill_id) == drill_id


# --- kiểm tra đầu vào ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.update(caller={**e["caller"], "h1": "0900000001"}),  # số điện thoại thô
        lambda e: e.update(caller_phone="0900000001"),
        lambda e: e.update(type="teleport"),
        lambda e: e.update(rule_floor="extreme"),
        lambda e: e.update(is_drill=True),  # diễn tập mà thiếu drill_id
        lambda e: e.update(occurred_at="2026-12-01T02:15:30"),  # thiếu múi giờ
        lambda e: e.update(schema_version=2),
        lambda e: e.pop("id"),
        lambda e: e.update(app_version="v" * 33),
    ],
    ids=[
        "raw_phone",
        "extra_field",
        "bad_type",
        "bad_floor",
        "drill_without_id",
        "naive_time",
        "version",
        "no_id",
        "long",
    ],
)
async def test_invalid_event_rejects_the_whole_batch(device_world: Any, token: str, mutate: Any) -> None:
    good, bad = make_event(), make_event()
    mutate(bad)
    resp = await post(token, good, bad)
    assert resp.status_code == 422
    assert await count(RiskEventRecord, device_world.family_id) == 0  # lô hỏng không ghi gì (kể cả sự kiện tốt)
    assert "0900000001" not in resp.text  # thông báo lỗi không lặp lại giá trị đã gửi


async def test_batch_size_limits(device_world: Any, token: str) -> None:
    assert (await call("POST", "/v1/events", token=token, json={"events": []})).status_code == 422
    assert (await call("POST", "/v1/events", token=token, json={})).status_code == 422
    assert (await post(token, *[harmless() for _ in range(51)])).status_code == 422
    resp = await post(token, *[harmless() for _ in range(50)])
    assert resp.status_code == 200 and resp.json()["accepted"] == 50
    extra = await call("POST", "/v1/events", token=token, json={"events": [harmless()], "family_id": str(new_id())})
    assert extra.status_code == 422  # gia đình/thiết bị không đến từ thân yêu cầu


# --- không rò PII (FR-009, SC-005) ---------------------------------------------------------------------------------


async def test_only_the_hmac_and_last3_are_stored_never_h1(
    device_world: Any, token: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    ev = make_event()
    assert (await post(token, ev)).status_code == 200
    kid, expected = hmac_h1(FAKE_H1)
    async with get_sessionmaker()() as session:
        row = await session.get(RiskEventRecord, UUID(ev["id"]))
        assert row is not None and (row.caller_hmac, row.caller_kid, row.caller_last3) == (expected, kid, "000")
        assert "h1" not in row.payload.get("caller", {}) and row.payload["caller"]["last3"] == "000"
        dump = " ".join(
            filter(
                None,
                [
                    await session.scalar(
                        text("select string_agg(t::text, ' ') from risk_events t where family_id = :f"),
                        {"f": device_world.family_id},
                    ),
                    await session.scalar(
                        text("select string_agg(t::text, ' ') from incidents t where family_id = :f"),
                        {"f": device_world.family_id},
                    ),
                ],
            )
        )
    assert FAKE_H1 not in dump and "0900000001" not in dump
    assert (
        FAKE_H1 not in caplog.text
        and expected not in caplog.text
        and "000" not in [r.getMessage() for r in caplog.records if "last3" in r.getMessage()]
    )


async def test_event_without_caller_is_stored_with_null_caller_columns(device_world: Any, token: str) -> None:
    ev = harmless()
    del ev["caller"]
    assert (await post(token, ev)).status_code == 200
    async with get_sessionmaker()() as session:
        row = await session.get(RiskEventRecord, UUID(ev["id"]))
    assert row is not None and (row.caller_hmac, row.caller_kid, row.caller_last3, row.caller_in_contacts) == (
        None,
        None,
        None,
        None,
    )


# --- lỗi hạ tầng --------------------------------------------------------------------------------------------------


async def test_a_failure_while_opening_the_incident_rolls_the_whole_batch_back(
    device_world: Any, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.services.incident_service import IncidentService

    async def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(IncidentService, "correlate_event", boom)
    with pytest.raises(RuntimeError):
        await post(token, make_event(), harmless())
    assert await count(RiskEventRecord, device_world.family_id) == 0  # app gửi lại được, không mất sự kiện
    monkeypatch.undo()
    assert (await post(token, make_event())).status_code == 200


async def test_missing_pepper_gives_503_and_stores_nothing(
    device_world: Any, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_pepper(_: str) -> tuple[int, str]:
        raise RuntimeError("thiếu HOICON_PHONE_PEPPER_1")

    monkeypatch.setattr("hoicon.api.routers.events.hmac_h1", no_pepper)
    resp = await post(token, make_event())
    assert resp.status_code == 503 and FAKE_H1 not in resp.text
    assert await count(RiskEventRecord, device_world.family_id) == 0


# --- review độc lập: giới hạn, khóa chờ, đầu vào tự do ---------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_event_limits() -> None:
    from hoicon.api.routers import events

    events.reset_limits()


async def test_batches_are_rate_limited_per_device(
    device_world: Any, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.api.routers import events

    monkeypatch.setattr(events, "MAX_BATCHES_PER_WINDOW", 3)
    codes = [(await post(token, harmless())).status_code for _ in range(5)]
    assert codes == [200, 200, 200, 429, 429]
    resp = await post(token, harmless())
    assert resp.status_code == 429 and int(resp.headers["Retry-After"]) >= 1
    assert await count(RiskEventRecord, device_world.family_id) == 3  # lô bị từ chối không ghi gì


async def test_waiting_for_the_device_lock_times_out_with_503(
    device_world: Any, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Một giao dịch giữ khóa thiết bị không được làm nghẽn pool kết nối: chờ quá hạn ⇒ 503, lô không ghi gì."""
    from hoicon.api.routers import events

    monkeypatch.setattr(events, "LOCK_TIMEOUT_MS", 300)
    async with get_sessionmaker().begin() as holder:
        device_id = await holder.scalar(
            text("select id from devices where family_id = :f"), {"f": device_world.family_id}
        )
        await holder.execute(text("select pg_advisory_xact_lock(hashtext(:k))"), {"k": f"open-incident:{device_id}"})
        resp = await asyncio.wait_for(post(token, make_event()), 5)
    assert resp.status_code == 503 and "Retry-After" in resp.headers
    assert await count(RiskEventRecord, device_world.family_id) == 0
    assert (await post(token, make_event())).status_code == 200  # nhả khóa rồi thì gửi lại được


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e["app"].update(package="call 0900000001 now"),
        lambda e: e["app"].update(package="vn.hoicon demobank"),
        lambda e: e.update(app_version="0900000001"),
        lambda e: e.update(app_version="0912.3456.78"),  # đúng mẫu phiên bản nhưng ghép lại thành số điện thoại
        lambda e: e["app"].update(package="vn.0900000001"),
        lambda e: e.update(app_version="1.0-0900000001"),  # số điện thoại nằm trong hậu tố
        lambda e: e.update(app_version="0.1.0-84912345678"),
        lambda e: e.update(rules_version="1.0.0+0912.345.678"),
        lambda e: e.update(app_version="0912.3456-78"),  # một số điện thoại chia đôi qua phần chính và hậu tố
        lambda e: e.update(app_version="1234.5678-9012"),
        lambda e: e.update(app_version="٠٩١٢.٣٤٥٦-78"),  # chữ số Unicode
        lambda e: e.update(rules_version="OTP-123456"),
        lambda e: e.update(rules_version="r 1"),
        lambda e: e["call"].update(duration_s=2**31),
        lambda e: e["call"].update(duration_s=86401),
        lambda e: e["timing"].update(detect_ms=2**40),
        lambda e: e["timing"].update(pause_ms=3_600_001),
        lambda e: e.update(is_drill="yes"),
        lambda e: e["caller"].update(in_contacts="false"),
    ],
    ids=[
        "pkg_phone",
        "pkg_space",
        "ver_phone",
        "ver_dotted_phone",
        "pkg_dotted_phone",
        "ver_suffix_phone",
        "ver_suffix_84",
        "rules_suffix_dotted",
        "ver_split_phone",
        "ver_split_cccd",
        "ver_unicode_digits",
        "rules_otp",
        "rules_space",
        "dur_int32",
        "dur_day",
        "detect_big",
        "pause_big",
        "drill_str",
        "contacts_str",
    ],
)
async def test_free_text_and_numbers_are_bounded(device_world: Any, token: str, mutate: Any) -> None:
    bad = make_event()
    mutate(bad)
    resp = await post(token, bad)
    assert resp.status_code == 422, resp.text  # không phải 500 (DataError) và không lọt vào DB
    assert await count(RiskEventRecord, device_world.family_id) == 0


def test_the_hash_never_appears_in_repr() -> None:
    from hoicon.domain.events import RiskEventIn

    event = RiskEventIn.model_validate(make_event())
    assert FAKE_H1 not in repr(event) and FAKE_H1 not in str(event)


@pytest.mark.parametrize(
    "version",
    [
        "0.1.0",
        "r1",
        "rules-2026.12.01",
        "0.1.0-20261016",
        "0.0.1-20261201",
        "1.0.0-g1a2b3c4",
        "0.1.0-SNAPSHOT",
        "rules-2026.12.01-20261016",
    ],
)
async def test_real_version_strings_are_accepted(device_world: Any, token: str, version: str) -> None:
    """Không chặn nhầm phiên bản hợp lệ (kể cả bản pre-1.0 có hậu tố ngày build) — chặn nhầm làm mất cảnh báo thật."""
    resp = await post(token, make_event(app_version=version, rules_version=version))
    assert resp.status_code == 200, (version, resp.text)


async def test_the_device_table_is_capped_even_when_nothing_expires(monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from uuid import uuid4

    from hoicon.api.routers import events

    monkeypatch.setattr(events, "MAX_TRACKED_DEVICES", 5)
    now = time.monotonic()
    for _ in range(50):
        assert events._retry_after(uuid4(), now) is None
    assert len(events._batches) <= 5


# --- Spec 026 FR-008: ghi xác minh số gọi đến khi đồ thị khởi động ------------------------------------------------


LIST_VERSION = "test-spec026-events"


async def call_verifications(family_id: Any) -> list[Verification]:
    async with get_sessionmaker()() as session:
        return list((await session.scalars(select(Verification).where(Verification.family_id == family_id))).all())


@pytest.fixture
async def flagged_caller(device_world: Any) -> Any:
    """Đưa số hư cấu `FAKE_H1` vào danh sách đe dọa (độ tin cậy 0,9) cho test này; dọn theo `list_version`."""
    from hoicon.db.models import ThreatIndicator
    from hoicon.ops import threat_list

    doc = {
        "version": LIST_VERSION,
        "is_demo": True,
        "indicators": [{"h1": FAKE_H1, "source": "Nguồn thử nghiệm", "confidence": 0.9, "last3": "000"}],
    }
    await threat_list.load_seed(get_sessionmaker(), doc, env="dev", with_bucket=False)
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == LIST_VERSION))


async def test_high_event_records_one_system_verification_for_the_caller(device_world: Any, token: str) -> None:
    body = (await post(token, make_event())).json()
    (row,) = await call_verifications(device_world.family_id)
    assert (row.actor, row.actor_id, row.kind, row.via, row.last3) == ("system", None, "phone", "call", "000")
    assert (row.subject_kid, row.subject_hmac) == hmac_h1(FAKE_H1)
    assert (row.verdict, float(row.confidence), row.is_demo) == ("unknown", 0.0, False)
    assert str(row.incident_id) == body["incident_id"]


async def test_flagged_caller_is_recorded_as_dangerous_with_its_source(
    device_world: Any, token: str, flagged_caller: None
) -> None:
    await post(token, make_event())
    (row,) = await call_verifications(device_world.family_id)
    assert (row.verdict, float(row.confidence), row.list_version, row.is_demo) == ("dangerous", 0.9, LIST_VERSION, True)
    assert row.sources == [{"name": "Nguồn thử nghiệm", "type": "threat_list", "list_version": LIST_VERSION}]


async def test_the_same_caller_in_later_events_does_not_add_a_second_row(
    device_world: Any, token: str, flagged_caller: None
) -> None:
    first = make_event()
    await post(token, first)
    await post(token, make_event(), first)  # sự kiện mới cùng số gọi + gửi lại sự kiện cũ
    assert len(await call_verifications(device_world.family_id)) == 1


async def test_event_without_a_caller_records_nothing(device_world: Any, token: str) -> None:
    no_caller = make_event()
    del no_caller["caller"]
    assert (await post(token, no_caller)).json()["incident_opened"] is True
    assert await call_verifications(device_world.family_id) == []


async def test_event_that_opens_no_incident_records_nothing(device_world: Any, token: str) -> None:
    assert (await post(token, harmless())).json()["incident_id"] is None
    assert await call_verifications(device_world.family_id) == []


async def test_failed_lookup_records_nothing_and_does_not_block_the_alert(
    device_world: Any, token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def broken(*_: Any, **__: Any) -> Any:
        raise RuntimeError("lỗi mô phỏng 0900000001")

    monkeypatch.setattr("hoicon.agents.runtime.lookup_h1", broken)
    resp = await post(token, make_event())
    assert resp.status_code == 200
    assert resp.json()["incident_opened"] is True
    assert await call_verifications(device_world.family_id) == []  # không ghi "chưa có trong danh sách" khi tra lỗi


async def test_verification_and_start_graph_job_hold_no_h1(
    device_world: Any, token: str, flagged_caller: None, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    body = (await post(token, make_event())).json()
    async with get_sessionmaker()() as session:
        dump = await session.scalar(
            text("select string_agg(t::text, ' ') from verifications t where family_id = :f"),
            {"f": device_world.family_id},
        )
        job = await session.scalar(
            text("select payload::text from jobs where idempotency_key = :k"),
            {"k": f"{body['incident_id']}:graph:start"},
        )
    assert FAKE_H1 not in dump and FAKE_H1 not in job
    assert FAKE_H1 not in caplog.text
    assert hmac_h1(FAKE_H1)[1] not in (job or "")
    assert hmac_h1(FAKE_H1)[1] not in caplog.text
