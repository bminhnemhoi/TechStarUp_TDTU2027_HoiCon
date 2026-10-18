"""Spec 026 (FR-005, FR-006, SC-001..SC-003, SC-006): `POST /v1/lookups`.

Số điện thoại/h1/khóa dưới đây đều HƯ CẤU (băm một nhãn tùy ý), không liên quan người thật.
"""

import asyncio
import hashlib
import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, item, pair_device, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import delete, func, select, text

from hoicon.api.auth import issue_guardian_access_token
from hoicon.api.routers import lookups
from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Family, Incident, Job, Member, ThreatIndicator, Verification
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_h1
from hoicon.ops import threat_list

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
RESULT = json.loads((SCHEMAS / "lookup_result.v1.json").read_text(encoding="utf-8"))
REQUEST = json.loads((SCHEMAS / "lookup_request.v1.json").read_text(encoding="utf-8"))
AI_DISCLOSURE = "Đây là trợ lý AI HỏiCon."
VERSION = "test-spec026-lookups"
SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
SECRET_URL = "https://nguoi:matkhau@Tai-Ung-Dung-Gia.example/files/bidv-9876543210.apk?otp=123456&sdt=0900000123"
SECRET_HOST = "tai-ung-dung-gia.example"


def fake_h1(label: str) -> str:
    """h1 GIẢ (băm một nhãn tùy ý)."""
    return hashlib.sha256(f"fixture:{label}".encode()).hexdigest()


def phone_body(label: str, *, last3: str = "123", **changes: Any) -> dict[str, Any]:
    return {"kind": "phone", "via": "typed", "h1": fake_h1(label), "last3": last3, **changes}


def url_body(url: str = SECRET_URL, **changes: Any) -> dict[str, Any]:
    return {"kind": "url", "via": "typed", "url": url, **changes}


@dataclass
class World:
    family_id: UUID
    device_id: UUID
    device_member: UUID
    device_token: str
    guardian_id: UUID
    guardian_token: str
    incident_id: UUID
    other_family_id: UUID
    other_incident_id: UUID


def valid_result(doc: Any) -> list[str]:
    return [e.message for e in Draft202012Validator(RESULT, format_checker=FormatChecker()).iter_errors(doc)]


async def grant(member_id: UUID, family_id: UUID, *, granted: bool = True) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=family_id,
                member_id=member_id,
                purpose="lookups",
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="web",
            )
        )


@pytest.fixture
async def world(device_world: Any) -> AsyncGenerator[World]:
    lookups.reset_limits()
    paired = await pair_device(device_world.code)
    me = (await call("GET", "/v1/devices/me", token=paired["access_token"])).json()["device"]
    family_id = UUID(me["family_id"])
    async with get_sessionmaker().begin() as session:
        guardian = Member(family_id=family_id, role="guardian", guardian_rank=1)
        other = Family(display_name="test-026-other", region="nam", is_demo=True)
        session.add_all([guardian, other])
        await session.flush()
        other_member = Member(family_id=other.id, role="protected")
        session.add(other_member)
        await session.flush()
        mine = Incident(
            family_id=family_id,
            member_id=UUID(me["member_id"]),
            device_id=UUID(me["device_id"]),
            level="high",
            rule_floor="high",
            is_demo=True,
        )
        theirs = Incident(family_id=other.id, member_id=other_member.id, level="high", rule_floor="high", is_demo=True)
        session.add_all([mine, theirs])
        await session.flush()
        ids = (guardian.id, other.id, mine.id, theirs.id)
    await threat_list.load_seed(
        get_sessionmaker(),
        {
            "version": VERSION,
            "is_demo": True,
            "indicators": [
                {"h1": fake_h1("high"), "source": "Nguồn thử nghiệm A", "confidence": 0.9, "last3": "123"},
                {"h1": fake_h1("low"), "source": "Nguồn thử nghiệm B", "confidence": 0.5, "last3": "456"},
            ],
        },
        env="dev",
        with_bucket=False,
    )
    yield World(
        family_id=family_id,
        device_id=UUID(me["device_id"]),
        device_member=UUID(me["member_id"]),
        device_token=paired["access_token"],
        guardian_id=ids[0],
        guardian_token=issue_guardian_access_token(ids[0], family_id),
        incident_id=ids[2],
        other_family_id=ids[1],
        other_incident_id=ids[3],
    )
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == VERSION))
    await purge_family(ids[1])
    lookups.reset_limits()


@pytest.fixture
async def consented(world: World) -> World:
    await grant(world.device_member, world.family_id)
    await grant(world.guardian_id, world.family_id)
    return world


async def post(token: str | None, body: Any) -> Any:
    return await call("POST", "/v1/lookups", token=token, json=body)


async def verifications(family_id: UUID) -> list[Verification]:
    async with get_sessionmaker()() as session:
        return list((await session.scalars(select(Verification).where(Verification.family_id == family_id))).all())


async def level_of(incident_id: UUID) -> tuple[str, int]:
    async with get_sessionmaker()() as session:
        row = await session.get(Incident, incident_id, populate_existing=True)
        assert row is not None
        return row.level, row.version


async def evidence_jobs(incident_id: UUID) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(
            (await session.scalars(select(Job).where(Job.idempotency_key.like(f"{incident_id}:evidence:%")))).all()
        )


# --- hợp đồng + kết luận ----------------------------------------------------------------------------------------


def test_request_fixtures_used_here_match_the_contract() -> None:
    validator = Draft202012Validator(REQUEST, format_checker=FormatChecker())
    assert validator.is_valid(phone_body("high"))
    assert validator.is_valid(url_body())


async def test_listed_number_is_dangerous_and_cites_the_list(consented: World) -> None:
    resp = await post(consented.device_token, phone_body("high"))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert valid_result(body) == []
    assert body["kind"] == "phone"
    assert body["verdict"] == "dangerous"
    assert body["confidence"] == 0.9
    assert body["disclaimer"].startswith(AI_DISCLOSURE)
    assert body["is_demo"] is True
    assert body["reasons"][0]["code"] == "listed_high"
    assert body["sources"] == [{"name": "Nguồn thử nghiệm A", "type": "threat_list", "list_version": VERSION}]
    assert "incident_level" not in body


async def test_low_confidence_number_is_a_warning(consented: World) -> None:
    body = (await post(consented.guardian_token, phone_body("low", last3="456"))).json()
    assert valid_result(body) == []
    assert (body["verdict"], body["reasons"][0]["code"]) == ("warning", "listed_low")


async def test_unlisted_number_is_unknown_never_safe(consented: World) -> None:
    body = (await post(consented.device_token, phone_body("khong-co-trong-danh-sach"))).json()
    assert valid_result(body) == []
    assert (body["verdict"], body["confidence"], body["reasons"][0]["code"]) == ("unknown", 0.0, "not_listed")
    assert body["disclaimer"].startswith(AI_DISCLOSURE)


async def test_apk_link_is_dangerous(consented: World) -> None:
    resp = await post(consented.guardian_token, url_body())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert valid_result(body) == []
    assert (body["kind"], body["verdict"], body["reasons"][0]["code"]) == ("url", "dangerous", "app_download")
    assert body["sources"] == [{"name": "Quy tắc HỏiCon: app_download", "type": "heuristic"}]


async def test_a_lookup_is_recorded_without_any_identifier(consented: World) -> None:
    await post(consented.device_token, phone_body("high"))
    await post(consented.guardian_token, url_body())
    rows = {row.kind: row for row in await verifications(consented.family_id)}
    phone, url = rows["phone"], rows["url"]
    assert (phone.actor, phone.actor_id, phone.via, phone.verdict) == (
        "device",
        consented.device_id,
        "typed",
        "dangerous",
    )
    assert (phone.subject_kid, phone.subject_hmac) == hmac_h1(fake_h1("high"))
    assert phone.last3 == "123"
    assert (url.actor, url.actor_id, url.last3, url.verdict) == ("guardian", consented.guardian_id, None, "dangerous")
    digest = hashlib.sha256(b"hoicon:url:v1:" + SECRET_HOST.encode()).hexdigest()
    assert (url.subject_kid, url.subject_hmac) == hmac_h1(digest)


# --- xác thực, đồng ý, phạm vi -----------------------------------------------------------------------------------


async def test_requires_a_valid_token(consented: World) -> None:
    assert (await post(None, phone_body("high"))).status_code == 401
    assert (await post("not-a-token", phone_body("high"))).status_code == 401
    assert await verifications(consented.family_id) == []


async def test_revoked_device_and_unknown_guardian_are_refused(consented: World) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(text("update devices set revoked_at = now() where id = :d"), {"d": consented.device_id})
    assert (await post(consented.device_token, phone_body("high"))).status_code == 401
    stranger = issue_guardian_access_token(new_id(), consented.family_id)
    assert (await post(stranger, phone_body("high"))).status_code == 401


async def test_without_consent_both_actors_get_403_and_nothing_is_stored(world: World) -> None:
    for token in (world.device_token, world.guardian_token):
        resp = await post(token, phone_body("high"))
        assert resp.status_code == 403, resp.text
        assert "đồng ý" in resp.json()["detail"]
    assert await verifications(world.family_id) == []


async def test_withdrawn_consent_blocks_again(world: World) -> None:
    await grant(world.device_member, world.family_id)
    assert (await post(world.device_token, phone_body("high"))).status_code == 200
    await grant(world.device_member, world.family_id, granted=False)
    assert (await post(world.device_token, phone_body("high"))).status_code == 403


async def test_other_purposes_do_not_count_as_lookups_consent(world: World) -> None:
    resp = await call("POST", "/v1/consents", token=world.device_token, json={"items": [item("core_protection")]})
    assert resp.status_code in (200, 201), resp.text
    assert (await post(world.device_token, phone_body("high"))).status_code == 403


async def test_lookups_consent_can_be_recorded_through_the_consent_api(world: World) -> None:
    resp = await call("POST", "/v1/consents", token=world.device_token, json={"items": [item("lookups")]})
    assert resp.status_code in (200, 201), resp.text
    assert (await post(world.device_token, phone_body("high"))).status_code == 200


async def test_incident_of_another_family_or_unknown_is_a_404(consented: World) -> None:
    for incident in (consented.other_incident_id, new_id()):
        resp = await post(consented.device_token, phone_body("high", incident_id=str(incident)))
        assert resp.status_code == 404, resp.text
    assert await verifications(consented.family_id) == []
    assert await level_of(consented.other_incident_id) == ("high", 1)


@pytest.mark.parametrize(
    ("body", "error_type"),
    [
        ({"kind": "account", "via": "typed", "h1": fake_h1("x"), "last3": "123"}, "kind_not_supported"),
        (
            {"kind": "phone", "via": "typed", "h1": fake_h1("x"), "last3": "123", "number": "0900000123"},
            "extra_forbidden",
        ),
        ({"kind": "phone", "via": "typed", "h1": "0900000123", "last3": "123"}, None),
        ({"kind": "phone", "via": "typed", "h1": fake_h1("x").upper(), "last3": "123"}, None),
        ({"kind": "phone", "via": "typed", "h1": fake_h1("x")}, None),
        ({"kind": "phone", "via": "typed", "h1": fake_h1("x"), "last3": "12a"}, None),
        ({"kind": "phone", "via": "typed", "h1": fake_h1("x"), "last3": "123", "url": "https://a.example"}, None),
        ({"kind": "url", "via": "typed", "url": "https://a.example", "h1": fake_h1("x")}, None),
        ({"kind": "url", "via": "call", "url": "https://a.example"}, None),
        ({"kind": "url", "via": "typed", "url": "ab"}, None),
        ({"kind": "url", "via": "typed", "url": "https://a.example/" + "x" * 2100}, None),
        ({"kind": "url", "via": "typed"}, None),
        ({"kind": "phone", "via": "typed", "h1": fake_h1("x"), "last3": "123", "incident_id": "không-phải-uuid"}, None),
        ({}, None),
    ],
)
async def test_invalid_requests_are_422_and_never_echo_the_input(
    consented: World, body: dict[str, Any], error_type: str | None
) -> None:
    resp = await post(consented.device_token, body)
    assert resp.status_code == 422, resp.text
    if error_type is not None:
        assert error_type in {e["type"] for e in resp.json()["detail"]}
    assert "0900000123" not in resp.text
    assert fake_h1("x") not in resp.text
    assert await verifications(consented.family_id) == []


@pytest.mark.parametrize("bad", ["http://", "javascript:alert(1)", "ftp://a.example/x", "http://exa mple.com", "ab.c"])
async def test_unparseable_url_is_422_and_not_echoed(consented: World, bad: str) -> None:
    resp = await post(consented.device_token, url_body(bad))
    assert resp.status_code == 422, resp.text
    assert bad not in resp.text
    assert await verifications(consented.family_id) == []


# --- hạn mức (SC-006) --------------------------------------------------------------------------------------------


async def seed_history(world: World, actor: str, actor_id: UUID, count: int, *, ago: str) -> None:
    """Chèn thẳng `count` dòng xác minh cách đây `ago` (nhanh hơn gọi API); chủ thể là HMAC giả."""
    async with get_sessionmaker().begin() as session:
        for index in range(count):
            session.add(
                Verification(
                    family_id=world.family_id,
                    actor=actor,
                    actor_id=actor_id,
                    kind="phone",
                    via="typed",
                    subject_kid=1,
                    subject_hmac=f"{index:064x}",
                    last3="000",
                    verdict="unknown",
                    confidence=0,
                    at=func.now() - text(f"interval '{ago}'"),
                )
            )


async def test_device_gets_20_lookups_per_hour_then_429(consented: World) -> None:
    for index in range(20):
        assert (await post(consented.device_token, phone_body(f"n{index}"))).status_code == 200
    resp = await post(consented.device_token, phone_body("n21"))
    assert resp.status_code == 429, resp.text
    assert 1 <= int(resp.headers["Retry-After"]) <= 3600
    assert len(await verifications(consented.family_id)) == 20  # lần bị từ chối không được ghi


async def test_guardian_gets_60_lookups_per_hour_then_429(consented: World) -> None:
    await seed_history(consented, "guardian", consented.guardian_id, 60, ago="10 minutes")
    resp = await post(consented.guardian_token, phone_body("n61"))
    assert resp.status_code == 429, resp.text
    assert int(resp.headers["Retry-After"]) >= 1


async def test_device_daily_cap_is_60_even_when_the_hour_is_quiet(consented: World) -> None:
    await seed_history(consented, "device", consented.device_id, 60, ago="5 hours")
    assert (await post(consented.device_token, phone_body("n61"))).status_code == 429
    async with get_sessionmaker().begin() as session:  # dòng cách đây hơn 1 ngày thôi không tính
        await session.execute(text("update verifications set at = now() - interval '25 hours'"))
    assert (await post(consented.device_token, phone_body("n62"))).status_code == 200


async def test_family_gets_200_lookups_per_day_across_people(consented: World) -> None:
    await seed_history(consented, "guardian", consented.guardian_id, 100, ago="3 hours")
    await seed_history(consented, "device", consented.device_id, 100, ago="30 hours")  # ngoài ngày ⇒ không tính
    assert (await post(consented.guardian_token, phone_body("n1"))).status_code == 200
    await seed_history(consented, "guardian", consented.guardian_id, 99, ago="2 hours")
    assert (await post(consented.device_token, phone_body("n2"))).status_code == 429


async def test_automatic_call_verifications_do_not_use_up_the_quota(consented: World) -> None:
    async with get_sessionmaker().begin() as session:
        for index in range(30):
            session.add(
                Verification(
                    family_id=consented.family_id,
                    incident_id=None,
                    actor="system",
                    kind="phone",
                    via="call",
                    subject_kid=1,
                    subject_hmac=f"{index:064x}",
                    last3="000",
                    verdict="unknown",
                    confidence=0,
                )
            )
    assert (await post(consented.device_token, phone_body("n1"))).status_code == 200


async def test_25_concurrent_requests_let_exactly_20_through(consented: World) -> None:
    results = await asyncio.gather(*(post(consented.device_token, phone_body(f"c{i}")) for i in range(25)))
    codes = sorted(r.status_code for r in results)
    assert codes == [200] * 20 + [429] * 5, codes
    assert len(await verifications(consented.family_id)) == 20


async def test_limits_are_per_actor(consented: World) -> None:
    await seed_history(consented, "device", consented.device_id, 20, ago="1 minute")
    assert (await post(consented.device_token, phone_body("a"))).status_code == 429
    assert (await post(consented.guardian_token, phone_body("b"))).status_code == 200


# --- trần cuộn 30 ngày (review bảo mật 026 #1) -----------------------------------------------------------------------


async def test_device_monthly_cap_is_600_even_when_hour_and_day_are_quiet(consented: World) -> None:
    await seed_history(consented, "device", consented.device_id, lookups.DEVICE_PER_MONTH, ago="10 days")
    resp = await post(consented.device_token, phone_body("n601"))
    assert resp.status_code == 429, resp.text
    assert int(resp.headers["Retry-After"]) > 86400  # đợi theo mốc dòng cũ nhất trôi khỏi cửa sổ 30 ngày
    async with get_sessionmaker().begin() as session:  # dòng cách đây hơn 30 ngày thôi không tính
        await session.execute(text("update verifications set at = now() - interval '31 days'"))
    assert (await post(consented.device_token, phone_body("n602"))).status_code == 200


async def test_just_under_the_monthly_cap_is_still_allowed(consented: World) -> None:
    await seed_history(consented, "device", consented.device_id, lookups.DEVICE_PER_MONTH - 1, ago="10 days")
    assert (await post(consented.device_token, phone_body("n1"))).status_code == 200
    assert (await post(consented.device_token, phone_body("n2"))).status_code == 429


async def test_guardian_monthly_cap(consented: World) -> None:
    await seed_history(consented, "guardian", consented.guardian_id, lookups.GUARDIAN_PER_MONTH, ago="10 days")
    assert (await post(consented.guardian_token, phone_body("g1"))).status_code == 429


async def test_family_monthly_cap_counts_every_person_but_not_the_system(consented: World) -> None:
    remaining = lookups.FAMILY_PER_MONTH - 1
    while remaining:  # chia cho nhiều người khác nhau để không chạm trần cá nhân (600/tháng)
        chunk = min(remaining, lookups.DEVICE_PER_MONTH - 1)
        await seed_history(consented, "device", new_id(), chunk, ago="10 days")
        remaining -= chunk
    await seed_history(consented, "system", new_id(), 50, ago="10 days")  # dòng hệ thống không tính vào trần gia đình
    assert (await post(consented.guardian_token, phone_body("f1"))).status_code == 200  # còn đúng 1 chỗ của nhà
    assert (await post(consented.guardian_token, phone_body("f2"))).status_code == 429


# --- rút đồng ý `lookups` làm sạch dấu vết tra cứu (review bảo mật 026 #3) ------------------------------------------


async def own_rows(world: World) -> list[Verification]:
    return [r for r in await verifications(world.family_id) if r.actor == "device"]


async def test_withdrawing_lookups_scrubs_identifying_columns_but_keeps_the_quota_rows(consented: World) -> None:
    for label in ("a", "b", "c"):
        assert (await post(consented.device_token, phone_body(label))).status_code == 200
    before = await own_rows(consented)
    assert len(before) == 3 and all(r.last3 == "123" and r.subject_hmac != "0" * 64 for r in before)

    resp = await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("lookups", False)]})
    assert resp.status_code == 200, resp.text

    after = await own_rows(consented)
    assert len(after) == 3  # dòng vẫn còn: sổ đếm hạn mức
    assert {r.id for r in after} == {r.id for r in before}
    for row in after:
        assert row.subject_hmac == "0" * 64 and row.last3 is None and row.sources == [] and row.list_version is None
        assert row.verdict and row.at is not None  # chỉ phần nhận diện bị xóa
    assert (await post(consented.device_token, phone_body("d"))).status_code == 403  # đã rút đồng ý


async def test_withdrawing_lookups_cannot_reset_the_hourly_quota(consented: World) -> None:
    await seed_history(consented, "device", consented.device_id, lookups.DEVICE_PER_HOUR, ago="1 minute")
    await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("lookups", False)]})
    await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("lookups", True)]})
    assert (await post(consented.device_token, phone_body("again"))).status_code == 429


async def test_other_purposes_and_other_people_are_not_scrubbed(consented: World) -> None:
    assert (await post(consented.device_token, phone_body("mine"))).status_code == 200
    assert (await post(consented.guardian_token, phone_body("theirs"))).status_code == 200
    await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("drills", False)]})
    assert all(
        r.subject_hmac != "0" * 64 for r in await verifications(consented.family_id)
    )  # đổi mục đích khác: không đụng
    await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("lookups", False)]})
    rows = {r.actor: r for r in await verifications(consented.family_id)}
    assert rows["device"].subject_hmac == "0" * 64
    assert rows["guardian"].subject_hmac != "0" * 64 and rows["guardian"].last3 == "123"  # người khác giữ nguyên


async def test_granting_lookups_does_not_scrub(consented: World) -> None:
    assert (await post(consented.device_token, phone_body("keep"))).status_code == 200
    await call("POST", "/v1/consents", token=consented.device_token, json={"items": [item("lookups", True)]})
    assert all(r.subject_hmac != "0" * 64 for r in await own_rows(consented))


# --- nâng mức sự cố (FR-006) -------------------------------------------------------------------------------------


async def test_dangerous_lookup_raises_the_incident_to_critical(consented: World) -> None:
    body = (await post(consented.device_token, phone_body("high", incident_id=str(consented.incident_id)))).json()
    assert body["incident_level"] == "critical"
    assert valid_result(body) == []
    assert await level_of(consented.incident_id) == ("critical", 2)
    rows = await verifications(consented.family_id)
    assert [r.incident_id for r in rows] == [consented.incident_id]


async def test_warning_raises_to_high_and_unknown_changes_nothing(consented: World) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update incidents set level = 'medium', rule_floor = 'medium' where id = :i"),
            {"i": consented.incident_id},
        )
    unknown = (
        await post(consented.guardian_token, phone_body("khong-co", incident_id=str(consented.incident_id)))
    ).json()
    assert unknown["incident_level"] == "medium"
    assert await level_of(consented.incident_id) == ("medium", 1)
    warning = (
        await post(consented.guardian_token, phone_body("low", last3="456", incident_id=str(consented.incident_id)))
    ).json()
    assert warning["incident_level"] == "high"
    assert await level_of(consented.incident_id) == ("high", 2)


async def test_a_weaker_result_never_lowers_the_incident(consented: World) -> None:
    await post(consented.device_token, phone_body("high", incident_id=str(consented.incident_id)))
    assert await level_of(consented.incident_id) == ("critical", 2)
    for label, last3 in (("low", "456"), ("khong-co", "123")):
        body = (
            await post(consented.guardian_token, phone_body(label, last3=last3, incident_id=str(consented.incident_id)))
        ).json()
        assert body["incident_level"] == "critical"
    assert await level_of(consented.incident_id) == ("critical", 2)


async def test_a_decided_incident_is_left_alone(consented: World) -> None:
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update incidents set state = 'resolved_safe', outcome = 'safe', closed_at = now() where id = :i"),
            {"i": consented.incident_id},
        )
    body = (await post(consented.device_token, phone_body("high", incident_id=str(consented.incident_id)))).json()
    assert body["incident_level"] == "high"
    assert await level_of(consented.incident_id) == ("high", 1)
    assert await evidence_jobs(consented.incident_id) == []


async def test_lookup_without_an_incident_touches_no_incident(consented: World) -> None:
    await post(consented.device_token, phone_body("high"))
    assert await level_of(consented.incident_id) == ("high", 1)
    assert await evidence_jobs(consented.incident_id) == []


# --- tin bằng chứng (FR-006): job graph_resume ------------------------------------------------------------------


async def test_each_dangerous_lookup_by_the_elder_queues_its_own_evidence_job(consented: World) -> None:
    # Khóa theo verification_id: một job bị bỏ (đồ thị chưa chờ) không đốt khóa của các lần tra sau.
    first = (await post(consented.device_token, phone_body("high", incident_id=str(consented.incident_id)))).json()
    second = (await post(consented.device_token, url_body(incident_id=str(consented.incident_id)))).json()
    jobs = await evidence_jobs(consented.incident_id)
    assert {job.idempotency_key for job in jobs} == {
        f"{consented.incident_id}:evidence:{first['verification_id']}",
        f"{consented.incident_id}:evidence:{second['verification_id']}",
    }
    for job in jobs:
        assert job.kind == "graph_resume"
        assert job.payload["thread_id"] == str(consented.incident_id)
        assert job.payload["expect"] == "await_guardian"
        assert job.payload["value"] == {"evidence": job.idempotency_key.rsplit(":", 1)[1]}


async def test_no_evidence_job_when_the_guardian_looked_it_up(consented: World) -> None:
    await post(consented.guardian_token, phone_body("high", incident_id=str(consented.incident_id)))
    assert await level_of(consented.incident_id) == ("critical", 2)  # vẫn nâng mức
    assert await evidence_jobs(consented.incident_id) == []


async def test_no_evidence_job_for_warnings_or_unknown_results(consented: World) -> None:
    await post(consented.device_token, phone_body("low", last3="456", incident_id=str(consented.incident_id)))
    await post(consented.device_token, phone_body("khong-co", incident_id=str(consented.incident_id)))
    assert await evidence_jobs(consented.incident_id) == []


# --- riêng tư (SC-002) -------------------------------------------------------------------------------------------


async def test_nothing_identifying_reaches_the_database_the_jobs_or_the_logs(
    consented: World, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    h1 = fake_h1("high")
    await post(consented.device_token, phone_body("high", incident_id=str(consented.incident_id)))
    await post(consented.device_token, url_body(incident_id=str(consented.incident_id)))
    await post(consented.guardian_token, phone_body("khong-co"))
    await post(consented.guardian_token, {"kind": "phone", "via": "typed", "h1": "0900000123", "last3": "123"})
    async with get_sessionmaker()() as session:
        dumps = [
            "\n".join(await session.scalars(text(query), {"f": consented.family_id}))
            for query in (
                "select t::text from verifications t where family_id = :f",
                "select t::text from incidents t where family_id = :f",
            )
        ]
        dumps.append(
            "\n".join(
                await session.scalars(
                    text("select payload::text from jobs where idempotency_key like :k"),
                    {"k": f"{consented.incident_id}:%"},
                )
            )
        )
    blob = "\n".join(dumps) + "\n" + caplog.text
    hmac_value = hmac_h1(h1)[1]
    host_digest = hashlib.sha256(b"hoicon:url:v1:" + SECRET_HOST.encode()).hexdigest()
    for needle in (h1, host_digest, SECRET_HOST, "matkhau", "9876543210", "0900000123", "otp=", "sdt="):
        assert needle not in blob, needle
    # HMAC của chủ thể chỉ nằm ở `verifications.subject_hmac`: không ở `incidents`, `jobs` hay log
    assert hmac_value in dumps[0]
    assert hmac_value not in "\n".join(dumps[1:]) + caplog.text


async def test_response_never_contains_identifiers(consented: World) -> None:
    for body in (phone_body("high"), url_body()):
        resp = await post(consented.device_token, body)
        assert resp.status_code == 200
        text_out = resp.text
        for needle in (fake_h1("high"), hmac_h1(fake_h1("high"))[1], SECRET_HOST, "matkhau", "subject_hmac", "h1"):
            assert needle not in text_out, needle


# --- độ trễ (SC-001) ---------------------------------------------------------------------------------------------


async def test_lookup_latency_p95(consented: World) -> None:
    """Mục tiêu p95 ≤ 300 ms (n ≥ 50, Postgres dev, trong tiến trình). Người giám hộ 60/giờ ⇒ đủ cho 50 lần."""
    await post(consented.guardian_token, phone_body("warm-up"))
    samples: list[float] = []
    for index in range(50):
        started = time.perf_counter()
        resp = await post(consented.guardian_token, phone_body("high" if index % 2 else f"miss-{index}"))
        samples.append((time.perf_counter() - started) * 1000)
        assert resp.status_code == 200
    p95 = sorted(samples)[int(0.95 * len(samples)) - 1]
    print(f"\nPOST /v1/lookups p95 = {p95:.1f} ms (n=50)")
    assert p95 <= 300


# --- sự cố của người khác trong cùng nhà (review 026 #8) ---------------------------------------------------------


async def test_device_cannot_attach_a_lookup_to_another_members_incident(consented: World) -> None:
    async with get_sessionmaker().begin() as session:
        sibling = Member(family_id=consented.family_id, role="protected")
        session.add(sibling)
        await session.flush()
        theirs = Incident(
            family_id=consented.family_id, member_id=sibling.id, level="high", rule_floor="high", is_demo=True
        )
        session.add(theirs)
        await session.flush()
        sibling_incident = theirs.id
    resp = await post(consented.device_token, phone_body("high", incident_id=str(sibling_incident)))
    assert resp.status_code == 404
    assert (await level_of(sibling_incident))[0] == "high"  # không bị nâng
    assert (
        await post(consented.guardian_token, phone_body("high", incident_id=str(sibling_incident)))
    ).status_code == 200
