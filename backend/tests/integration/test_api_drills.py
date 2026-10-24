"""Spec 028 (FR-004..FR-007, SC-001, SC-003, SC-006): `DrillService`, `GET /v1/drills/offer`, `POST .../result`.

Mọi định danh/số trong test là HƯ CẤU. Kịch bản là 3 tệp thật trong `data/drills` (chưa duyệt: dev/test chạy được).
"""

import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, call, pair_device, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import func, select, text

from hoicon.agents.texts import AI_DISCLOSURE, DRILL_LABEL
from hoicon.api.routers import drills as drills_router
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Drill, Family, Job, Member
from hoicon.db.session import get_sessionmaker
from hoicon.domain import drill as dr
from hoicon.eval.checks import PANIC_PHRASES
from hoicon.services.drill_service import (
    ALLOWED,
    DrillRefused,
    DrillService,
    InvalidDrillTransition,
)

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
SRC = Path(__file__).resolve().parents[2] / "src" / "hoicon"
SOURCES = ("domain/drill.py", "services/drill_service.py", "api/routers/drills.py", "ops/drills.py")
SCRIPT_ID = "drill_bank_card_locked"
SCRIPT = dr.get_script(SCRIPT_ID) or {}


def _offer_validator() -> Draft202012Validator:
    resources = []
    for path in SCHEMAS.glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    schema = json.loads((SCHEMAS / "drill_offer.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=Registry().with_resources(resources), format_checker=FormatChecker())


OFFER = _offer_validator()


def right(script_id: str = SCRIPT_ID) -> list[dict[str, Any]]:
    script = dr.get_script(script_id) or {}
    return [
        {"step": i, "choice_id": next(c["id"] for c in step["choices"] if c["correct"])}
        for i, step in enumerate(script["steps"])
    ]


def wrong_at(index: int, script_id: str = SCRIPT_ID) -> list[dict[str, Any]]:
    answers = right(script_id)
    script = dr.get_script(script_id) or {}
    answers[index] = {
        "step": index,
        "choice_id": next(c["id"] for c in script["steps"][index]["choices"] if not c["correct"]),
    }
    return answers


@dataclass
class World:
    family_id: UUID
    member_id: UUID  # người cao tuổi của thiết bị
    token: str
    guardian_id: UUID
    sibling_id: UUID  # người cao tuổi khác cùng nhà
    other_family_id: UUID
    other_member_id: UUID


async def grant(member_id: UUID, family_id: UUID, *, granted: bool = True, purpose: str = "drills") -> None:
    async with get_sessionmaker().begin() as session:
        session.add(
            Consent(
                family_id=family_id,
                member_id=member_id,
                purpose=purpose,
                granted=granted,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )


@pytest.fixture
async def world(device_world: Any) -> AsyncGenerator[World]:
    drills_router.reset_limits()
    paired = await pair_device(device_world.code)
    me = (await call("GET", "/v1/devices/me", token=paired["access_token"])).json()["device"]
    family_id = UUID(me["family_id"])
    async with get_sessionmaker().begin() as session:
        guardian = Member(family_id=family_id, role="guardian", guardian_rank=1, alias="Con")
        sibling = Member(family_id=family_id, role="protected", alias="Bà")
        other = Family(display_name="test-028-other", region="nam", is_demo=True)
        session.add_all([guardian, sibling, other])
        await session.flush()
        other_member = Member(family_id=other.id, role="protected")
        session.add(other_member)
        await session.flush()
        ids = (guardian.id, sibling.id, other.id, other_member.id)
        elder = await session.get(Member, UUID(me["member_id"]))
        assert elder is not None
        elder.alias = "Mẹ"
    await grant(UUID(me["member_id"]), family_id)
    yield World(
        family_id=family_id,
        member_id=UUID(me["member_id"]),
        token=paired["access_token"],
        guardian_id=ids[0],
        sibling_id=ids[1],
        other_family_id=ids[2],
        other_member_id=ids[3],
    )
    await purge_family(ids[2])
    drills_router.reset_limits()


def utc_now() -> datetime:
    return datetime.now(UTC)


async def make_drill(
    family_id: UUID,
    member_id: UUID,
    *,
    start: timedelta = timedelta(minutes=-10),
    length: timedelta = timedelta(minutes=60),
    **changes: Any,
) -> UUID:
    """Chèn thẳng một bài (bỏ qua `schedule`) để dựng mọi trạng thái; cửa sổ tính từ BÂY GIỜ."""
    now = utc_now()
    values: dict[str, Any] = {
        "id": new_id(),
        "family_id": family_id,
        "member_id": member_id,
        "scheduled_by": "ops",
        "script_id": SCRIPT_ID,
        "window_start": now + start,
        "window_end": now + start + length,
        "is_demo": True,
    }
    values.update(changes)
    async with get_sessionmaker().begin() as session:
        session.add(Drill(**values))
    return values["id"]


async def row(drill_id: UUID) -> Drill:
    async with get_sessionmaker()() as session:
        found = await session.get(Drill, drill_id)
    assert found is not None
    return found


async def debrief_jobs(drill_id: UUID) -> list[Job]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(Job).where(Job.idempotency_key == f"{drill_id}:msg:debrief")))


async def offer(w: World) -> Any:
    return await call("GET", "/v1/drills/offer", token=w.token)


async def result(w: World, drill_id: UUID | str, body: dict[str, Any]) -> Any:
    return await call("POST", f"/v1/drills/{drill_id}/result", token=w.token, json={"drill_id": str(drill_id), **body})


# --- schedule (FR-004, SC-003) --------------------------------------------------------------------------------------


async def schedule(w: World, **changes: Any) -> Drill:
    now = utc_now()
    args: dict[str, Any] = {
        "family_id": w.family_id,
        "member_id": w.member_id,
        "window_start": now + timedelta(hours=1),
        "window_end": now + timedelta(hours=2),
        "script_id": SCRIPT_ID,
        "by": "ops",
    }
    args.update(changes)
    async with get_sessionmaker().begin() as session:
        return await DrillService.schedule(session, **args)


async def test_schedule_creates_a_scheduled_drill_and_an_expire_timer(world: World) -> None:
    drill = await schedule(world)
    saved = await row(drill.id)
    assert saved.status == "scheduled"
    assert saved.scheduled_by == "ops" and saved.script_id == SCRIPT_ID
    assert saved.is_demo is True  # gia đình demo ⇒ bài demo (luật 8)
    async with get_sessionmaker()() as session:
        timer = await session.scalar(select(Job).where(Job.idempotency_key == f"{drill.id}:expire"))
    assert timer is not None and timer.kind == "drill_expire"
    assert timer.payload == {"drill_id": str(drill.id)}  # chỉ id, không PII


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"script_id": "drill_khong_co"}, "script_unknown"),
        ({"window_start": "past"}, "window_past"),
        ({"window_end": "short"}, "window_too_short"),
        ({"window_end": "long"}, "window_too_long"),
        ({"member_id": "missing"}, "member_not_found"),
        ({"member_id": "guardian"}, "member_not_found"),
        ({"member_id": "other_family"}, "member_not_found"),
    ],
    ids=lambda v: v if isinstance(v, str) else next(iter(v.values())) if isinstance(v, dict) else str(v),
)
async def test_schedule_refuses_bad_input(world: World, changes: dict[str, Any], code: str) -> None:
    now = utc_now()
    resolved: dict[str, Any] = {}
    for key, value in changes.items():
        if value == "past":
            resolved["window_start"] = now - timedelta(hours=3)
            resolved["window_end"] = now - timedelta(hours=2)
        elif value == "short":
            resolved["window_end"] = now + timedelta(hours=1, minutes=29)
        elif value == "long":
            resolved["window_end"] = now + timedelta(hours=5, minutes=1)
        elif value == "missing":
            resolved[key] = new_id()
        elif value == "guardian":
            resolved[key] = world.guardian_id
        elif value == "other_family":
            resolved[key] = world.other_member_id
        else:
            resolved[key] = value
    with pytest.raises(DrillRefused) as caught:
        await schedule(world, **resolved)
    assert caught.value.code == code
    async with get_sessionmaker()() as session:
        count = await session.scalar(select(func.count()).select_from(Drill).where(Drill.family_id == world.family_id))
    assert count == 0  # từ chối ⇒ không ghi gì


async def test_schedule_needs_the_drills_consent(world: World) -> None:
    await grant(world.sibling_id, world.family_id, purpose="guardian_alerts")  # mục đích khác không thay được
    with pytest.raises(DrillRefused) as caught:
        await schedule(world, member_id=world.sibling_id)
    assert caught.value.code == "consent_missing"


async def test_schedule_refuses_after_the_consent_is_withdrawn(world: World) -> None:
    await grant(world.member_id, world.family_id, granted=False)
    with pytest.raises(DrillRefused) as caught:
        await schedule(world)
    assert caught.value.code == "consent_missing"


async def test_schedule_allows_two_a_month_and_refuses_the_third(world: World) -> None:
    base = utc_now() + timedelta(days=2)
    # Hai bài trong cùng tháng dương lịch (giờ VN) của `base`.
    for i in range(2):
        await schedule(world, window_start=base + timedelta(hours=3 * i), window_end=base + timedelta(hours=3 * i + 1))
    with pytest.raises(DrillRefused) as caught:
        await schedule(world, window_start=base + timedelta(hours=7), window_end=base + timedelta(hours=8))
    assert caught.value.code == "monthly_limit"


async def test_monthly_limit_counts_the_month_in_vietnam_time_and_is_per_family(world: World) -> None:
    await grant(world.sibling_id, world.family_id)
    # 31/12 17:30 UTC đã là 01/01 00:30 giờ VN: thuộc tháng 1, không phải tháng 12.
    year = utc_now().year + 1
    late_dec = datetime(year, 12, 31, 17, 30, tzinfo=UTC)
    early_jan = datetime(year + 1, 1, 1, 0, 30, tzinfo=UTC)
    await schedule(world, window_start=late_dec - timedelta(hours=3), window_end=late_dec - timedelta(hours=2))
    await schedule(world, window_start=late_dec, window_end=late_dec + timedelta(hours=1))
    # Cả hai bài trên: bài 1 (14:30Z = 21:30 VN, 31/12), bài 2 (01/01 00:30 VN). Tháng 12 mới có 1 bài ⇒ còn chỗ.
    await schedule(world, window_start=late_dec - timedelta(hours=6), window_end=late_dec - timedelta(hours=5))
    with pytest.raises(DrillRefused) as caught:  # tháng 12 đã đủ 2 (của CẢ nhà, dù người cao tuổi khác)
        await schedule(
            world,
            member_id=world.sibling_id,
            window_start=late_dec - timedelta(hours=9),
            window_end=late_dec - timedelta(hours=8),
        )
    assert caught.value.code == "monthly_limit"
    # Tháng 1 mới có 1 bài ⇒ vẫn đặt được thêm 1.
    await schedule(world, window_start=early_jan + timedelta(hours=5), window_end=early_jan + timedelta(hours=6))


async def test_a_cancelled_unoffered_drill_does_not_use_up_the_month(world: World) -> None:
    base = utc_now() + timedelta(days=3)
    first = await schedule(world, window_start=base, window_end=base + timedelta(hours=1))
    await schedule(world, window_start=base + timedelta(hours=3), window_end=base + timedelta(hours=4))
    async with get_sessionmaker().begin() as session:
        await DrillService.cancel(session, family_id=world.family_id, drill_id=first.id)
    await schedule(world, window_start=base + timedelta(hours=6), window_end=base + timedelta(hours=7))


async def test_an_offered_then_declined_drill_still_counts_for_the_month(world: World) -> None:
    base = utc_now() + timedelta(days=4)
    for i in range(2):
        await make_drill(
            world.family_id,
            world.member_id,
            start=timedelta(days=4, hours=3 * i),
            length=timedelta(hours=1),
            status="declined",
            offered_at=utc_now(),
        )
    with pytest.raises(DrillRefused) as caught:
        await schedule(world, window_start=base + timedelta(hours=8), window_end=base + timedelta(hours=9))
    assert caught.value.code == "monthly_limit"


async def test_schedule_refuses_overlapping_windows_for_the_same_elder(world: World) -> None:
    start = utc_now() + timedelta(days=1)
    await schedule(world, window_start=start, window_end=start + timedelta(hours=2))
    with pytest.raises(DrillRefused) as caught:
        await schedule(world, window_start=start + timedelta(hours=1), window_end=start + timedelta(hours=3))
    assert caught.value.code == "window_overlaps"


async def test_unapproved_script_is_refused_outside_dev_and_allowed_in_dev(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert (dr.get_script(SCRIPT_ID) or {})["approved"] is False
    await schedule(world)  # dev/test: được
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        with pytest.raises(DrillRefused) as caught:
            await schedule(
                world, window_start=utc_now() + timedelta(days=5), window_end=utc_now() + timedelta(days=5, hours=1)
            )
        assert caught.value.code == "script_not_approved"
    finally:
        get_settings.cache_clear()


# --- offer (FR-005) -------------------------------------------------------------------------------------------------


async def test_offer_is_null_when_nothing_is_scheduled(world: World) -> None:
    resp = await offer(world)
    assert resp.status_code == 200 and resp.json() == {"drill": None}
    assert list(OFFER.iter_errors(resp.json())) == []


async def test_offer_returns_the_drill_inside_its_window_and_marks_it_offered(world: World) -> None:
    drill_id = await make_drill(world.family_id, world.member_id)
    resp = await offer(world)
    assert resp.status_code == 200
    body = resp.json()
    assert [e.message for e in OFFER.iter_errors(body)] == []
    assert body["drill"]["drill_id"] == str(drill_id) and body["drill"]["is_drill"] is True
    assert body["drill"]["script"]["id"] == SCRIPT_ID
    saved = await row(drill_id)
    assert saved.status == "offered" and saved.offered_at is not None
    again = (await offer(world)).json()  # hỏi lại (chưa trả lời) ⇒ vẫn là bài đó, trạng thái không đổi
    assert again["drill"]["drill_id"] == str(drill_id)
    assert (await row(drill_id)).status == "offered"


@pytest.mark.parametrize(
    "when",
    [timedelta(minutes=30), timedelta(hours=-3)],
    ids=["window-not-started", "window-over"],
)
async def test_offer_is_null_outside_the_window(world: World, when: timedelta) -> None:
    drill_id = await make_drill(world.family_id, world.member_id, start=when, length=timedelta(minutes=60))
    assert (await offer(world)).json() == {"drill": None}
    assert (await row(drill_id)).status == "scheduled"


@pytest.mark.parametrize("status", ["declined", "aborted", "passed", "failed", "expired"])
async def test_offer_never_returns_a_finished_drill(world: World, status: str) -> None:
    extra: dict[str, Any] = {"status": status}
    if status in ("passed", "failed"):
        extra["score"] = 1
    await make_drill(world.family_id, world.member_id, **extra)
    assert (await offer(world)).json() == {"drill": None}


async def test_offer_needs_the_consent_and_stops_when_it_is_withdrawn(world: World) -> None:
    drill_id = await make_drill(world.family_id, world.member_id)
    await grant(world.member_id, world.family_id, granted=False)
    assert (await offer(world)).json() == {"drill": None}
    assert (await row(drill_id)).status == "scheduled"  # không có đồng ý ⇒ không "đã mời"


async def test_offer_never_returns_another_elders_or_familys_drill(world: World) -> None:
    await make_drill(world.family_id, world.sibling_id)
    await make_drill(world.other_family_id, world.other_member_id)
    assert (await offer(world)).json() == {"drill": None}


async def test_offer_withholds_an_unapproved_script_outside_dev(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    await make_drill(world.family_id, world.member_id)
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        assert (await offer(world)).json() == {"drill": None}
    finally:
        get_settings.cache_clear()


async def test_offer_needs_a_device_token(world: World) -> None:
    assert (await call("GET", "/v1/drills/offer")).status_code == 401
    assert (await call("GET", "/v1/drills/offer", token="khong-hop-le")).status_code == 401


async def test_offer_is_limited_to_30_an_hour_per_device(world: World) -> None:
    for _ in range(30):
        assert (await offer(world)).status_code == 200
    resp = await offer(world)
    assert resp.status_code == 429 and int(resp.headers["retry-after"]) >= 1


# --- result (FR-004, FR-005, FR-006, SC-001, SC-003, SC-006) ---------------------------------------------------------


async def offered(w: World, **changes: Any) -> UUID:
    return await make_drill(w.family_id, w.member_id, status="offered", offered_at=utc_now(), **changes)


async def test_completed_all_right_is_graded_passed_with_one_debrief(world: World) -> None:
    drill_id = await offered(world)
    resp = await result(
        world,
        drill_id,
        {
            "status": "completed",
            "answers": right(),
            "started_at": "2026-10-20T09:00:00.123Z",
            "completed_at": "2026-10-20T09:03:00Z",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"drill_id": str(drill_id), "status": "passed", "score": len(SCRIPT["steps"])}
    saved = await row(drill_id)
    assert saved.status == "passed" and saved.score == len(SCRIPT["steps"])
    assert saved.answers == right()
    assert saved.started_at is not None and saved.completed_at is not None
    jobs = await debrief_jobs(drill_id)
    assert len(jobs) == 1 and jobs[0].kind == "notify_guardian"
    payload = jobs[0].payload
    assert payload["is_drill"] is True and payload["is_demo"] is True
    assert payload["family_id"] == str(world.family_id) and payload["guardian_rank"] == 1
    assert payload["template"] == "debrief"
    text_ = payload["text"]
    assert text_.startswith(AI_DISCLOSURE) and DRILL_LABEL in text_  # SC-001
    assert "Mẹ" in text_  # xưng hô, không tên thật
    assert not any(p in text_.lower() for p in PANIC_PHRASES)
    assert (await row(drill_id)).debriefed_at is None  # chỉ đánh dấu khi tin ĐÃ gửi, không phải khi xếp job


async def test_one_wrong_step_is_failed_and_the_debrief_says_so(world: World) -> None:
    drill_id = await offered(world)
    resp = await result(world, drill_id, {"status": "completed", "answers": wrong_at(1)})
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed" and resp.json()["score"] == len(SCRIPT["steps"]) - 1
    saved = await row(drill_id)
    assert saved.status == "failed"
    (job,) = await debrief_jobs(drill_id)
    assert job.payload["text"].startswith(AI_DISCLOSURE) and DRILL_LABEL in job.payload["text"]
    passed_text = dr.red_flags(SCRIPT)[0]
    assert passed_text in job.payload["text"]  # dấu hiệu lừa đảo của bài có trong tin


async def test_the_result_can_arrive_after_the_window_if_the_drill_is_not_yet_expired(world: World) -> None:
    """Gửi sau khi mất mạng (WorkManager): quá `window_end` nhưng chưa bị job hết hạn thì vẫn nhận."""
    drill_id = await offered(world, start=timedelta(minutes=-90), length=timedelta(minutes=60))
    assert (await result(world, drill_id, {"status": "completed", "answers": right()})).status_code == 200
    assert (await row(drill_id)).status == "passed"


async def test_declined_is_recorded_and_sends_nothing(world: World) -> None:
    drill_id = await offered(world)
    resp = await result(world, drill_id, {"status": "declined", "answers": []})
    assert resp.status_code == 200 and resp.json() == {"drill_id": str(drill_id), "status": "declined", "score": None}
    assert (await row(drill_id)).status == "declined"
    assert await debrief_jobs(drill_id) == []
    assert (await offer(world)).json() == {"drill": None}  # "Để lúc khác" ⇒ không nhắc lại trong khung đó


async def test_aborted_keeps_the_partial_answers_and_sends_a_gentle_debrief(world: World) -> None:
    drill_id = await offered(world)
    resp = await result(world, drill_id, {"status": "aborted", "answers": right()[:1]})
    assert resp.status_code == 200 and resp.json()["status"] == "aborted" and resp.json()["score"] is None
    saved = await row(drill_id)
    assert saved.status == "aborted" and saved.answers == right()[:1] and saved.score is None
    (job,) = await debrief_jobs(drill_id)
    assert job.payload["text"].startswith(AI_DISCLOSURE) and DRILL_LABEL in job.payload["text"]


async def test_aborted_with_no_answers_straight_from_the_invitation_is_fine(world: World) -> None:
    drill_id = await offered(world)  # cuộc gọi thật đến lúc đang ở màn lời mời
    assert (await result(world, drill_id, {"status": "aborted", "answers": []})).status_code == 200
    assert (await row(drill_id)).status == "aborted"


async def test_sending_the_same_result_twice_is_200_and_changes_nothing(world: World) -> None:
    drill_id = await offered(world)
    body = {"status": "completed", "answers": right()}
    first = await result(world, drill_id, body)
    second = await result(world, drill_id, body)
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    assert len(await debrief_jobs(drill_id)) == 1


async def test_declined_twice_and_aborted_twice_are_idempotent(world: World) -> None:
    declined, aborted = (
        await offered(world),
        await make_drill(
            world.family_id,
            world.member_id,
            start=timedelta(hours=3),
            status="offered",
            offered_at=utc_now(),
        ),
    )
    for drill_id, body in (
        (declined, {"status": "declined", "answers": []}),
        (aborted, {"status": "aborted", "answers": right()[:2]}),
    ):
        assert (await result(world, drill_id, body)).status_code == 200
        assert (await result(world, drill_id, body)).status_code == 200


@pytest.mark.parametrize(
    "second",
    [
        {"status": "declined", "answers": []},
        {"status": "aborted", "answers": []},
        {"status": "completed", "answers": "wrong"},
    ],
    ids=["declined-after-passed", "aborted-after-passed", "different-answers"],
)
async def test_sending_a_different_result_is_409_and_keeps_the_first(world: World, second: dict[str, Any]) -> None:
    drill_id = await offered(world)
    assert (await result(world, drill_id, {"status": "completed", "answers": right()})).status_code == 200
    if second["answers"] == "wrong":
        second = {"status": "completed", "answers": wrong_at(0)}
    resp = await result(world, drill_id, second)
    assert resp.status_code == 409
    saved = await row(drill_id)
    assert saved.status == "passed" and saved.answers == right()
    assert len(await debrief_jobs(drill_id)) == 1


async def test_another_family_or_another_elder_gets_404_and_nothing_changes(world: World) -> None:
    theirs = await make_drill(world.other_family_id, world.other_member_id, status="offered", offered_at=utc_now())
    sibling = await make_drill(world.family_id, world.sibling_id, status="offered", offered_at=utc_now())
    unknown = new_id()
    for drill_id in (theirs, sibling, unknown):
        resp = await result(world, drill_id, {"status": "declined", "answers": []})
        assert resp.status_code == 404, drill_id
    assert (await row(theirs)).status == "offered" and (await row(sibling)).status == "offered"


async def test_a_malformed_id_is_rejected(world: World) -> None:
    resp = await call(
        "POST",
        "/v1/drills/khong-phai-uuid/result",
        token=world.token,
        json={"drill_id": "khong-phai-uuid", "status": "declined", "answers": []},
    )
    assert resp.status_code in (404, 422)


async def test_the_body_id_must_match_the_path(world: World) -> None:
    drill_id, other = await offered(world), new_id()
    resp = await call(
        "POST",
        f"/v1/drills/{drill_id}/result",
        token=world.token,
        json={"drill_id": str(other), "status": "declined", "answers": []},
    )
    assert resp.status_code == 422
    assert (await row(drill_id)).status == "offered"


@pytest.mark.parametrize("status", ["scheduled", "expired", "declined"])
async def test_a_result_for_a_drill_in_the_wrong_state_is_409(world: World, status: str) -> None:
    drill_id = await make_drill(world.family_id, world.member_id, status=status)
    resp = await result(world, drill_id, {"status": "completed", "answers": right()})
    assert resp.status_code == 409
    assert (await row(drill_id)).status == status
    assert await debrief_jobs(drill_id) == []


@pytest.mark.parametrize(
    "body",
    [
        {"status": "completed", "answers": [{"step": 0, "choice_id": "z"}, *right()[1:]]},  # mã lạ
        {"status": "completed", "answers": right()[::-1]},  # sai thứ tự
        {"status": "completed", "answers": right()[:-1]},  # thiếu bước
        {"status": "aborted", "answers": [{"step": 1, "choice_id": "a"}]},  # tiền tố không bắt đầu từ bước 0
        {"status": "declined", "answers": right()[:1]},  # từ chối mà có câu trả lời
    ],
    ids=["unknown-code", "order", "missing-step", "bad-prefix", "declined-with-answers"],
)
async def test_invalid_answers_are_422_and_leave_the_drill_untouched(world: World, body: dict[str, Any]) -> None:
    drill_id = await offered(world)
    resp = await result(world, drill_id, body)
    assert resp.status_code == 422
    saved = await row(drill_id)
    assert saved.status == "offered" and saved.answers is None and saved.score is None
    assert await debrief_jobs(drill_id) == []


@pytest.mark.parametrize(
    "extra",
    [
        {"note": "bác thấy lạ"},  # văn bản tự do bị cấm
        {"score": 99},  # máy không được tự chấm
        {"status": "passed"},  # chỉ máy chủ quyết passed/failed
        {"is_drill": False},
    ],
    ids=["note", "score", "passed", "is_drill"],
)
async def test_the_body_cannot_carry_free_text_or_a_score(world: World, extra: dict[str, Any]) -> None:
    drill_id = await offered(world)
    body = {"status": "completed", "answers": right(), **extra}
    resp = await result(world, drill_id, body)
    assert resp.status_code == 422
    assert (await row(drill_id)).status == "offered"


async def test_an_answer_item_cannot_carry_extra_fields(world: World) -> None:
    drill_id = await offered(world)
    noisy = [{**a, "note": "x"} for a in right()]
    assert (await result(world, drill_id, {"status": "completed", "answers": noisy})).status_code == 422


async def test_the_server_regrades_and_never_trusts_a_claimed_result(world: World) -> None:
    """Máy báo `completed` với đáp án sai: máy chủ tự chấm `failed` dù máy muốn gì."""
    drill_id = await offered(world)
    resp = await result(world, drill_id, {"status": "completed", "answers": wrong_at(0)})
    assert resp.json()["status"] == "failed"


async def test_result_needs_a_device_token(world: World) -> None:
    drill_id = await offered(world)
    resp = await call(
        "POST", f"/v1/drills/{drill_id}/result", json={"drill_id": str(drill_id), "status": "declined", "answers": []}
    )
    assert resp.status_code == 401


async def test_no_stored_value_is_free_text_and_no_llm_is_involved(world: World) -> None:
    drill_id = await offered(world)
    await result(world, drill_id, {"status": "completed", "answers": right()})
    async with get_sessionmaker()() as session:
        dump = (
            await session.execute(text("select row_to_json(d)::text from drills d where d.id = :i"), {"i": drill_id})
        ).scalar_one()
    assert "bác" not in dump and "note" not in dump
    # SC-006: mã mới không đi qua llm_router.
    for rel in SOURCES:
        assert "llm_router" not in (SRC / rel).read_text(encoding="utf-8"), rel


async def test_the_debrief_is_not_sent_to_a_real_family_for_a_demo_drill_or_vice_versa(world: World) -> None:
    """Cờ `is_demo` của job theo gia đình của bài (luật 8: không lẫn demo với thật)."""
    drill_id = await offered(world, is_demo=False)
    await result(world, drill_id, {"status": "completed", "answers": right()})
    (job,) = await debrief_jobs(drill_id)
    assert job.payload["is_demo"] is False  # `send_to_guardian` sẽ chặn vì gia đình test là demo


# --- expire, cancel, bảng cạnh ---------------------------------------------------------------------------------------


async def test_expire_closes_overdue_drills_and_only_those(world: World) -> None:
    long_ago = dict(start=timedelta(hours=-6), length=timedelta(hours=1))
    scheduled_late = await make_drill(world.family_id, world.member_id, **long_ago)
    offered_late = await make_drill(
        world.family_id,
        world.member_id,
        status="offered",
        offered_at=utc_now(),
        start=timedelta(hours=-9),
        length=timedelta(hours=1),
    )
    in_progress_late = await make_drill(
        world.family_id, world.sibling_id, status="in_progress", started_at=utc_now(), **long_ago
    )
    # còn trong thời gian ân hạn 1 giờ sau window_end: chưa hết hạn.
    grace = await make_drill(
        world.family_id,
        world.sibling_id,
        status="offered",
        offered_at=utc_now(),
        start=timedelta(minutes=-90),
        length=timedelta(minutes=45),
    )
    live = await make_drill(
        world.family_id, world.sibling_id, start=timedelta(hours=-8), length=timedelta(hours=1), status="declined"
    )
    future = await make_drill(world.family_id, world.sibling_id, start=timedelta(days=2))
    async with get_sessionmaker().begin() as session:
        closed = await DrillService.expire(session, now=utc_now())
    assert closed >= 3
    assert (await row(scheduled_late)).status == "expired"
    assert (await row(offered_late)).status == "expired"
    assert (await row(in_progress_late)).status == "expired"
    assert (await row(grace)).status == "offered"
    assert (await row(live)).status == "declined"  # trạng thái cuối không bị đụng
    assert (await row(future)).status == "scheduled"
    assert await debrief_jobs(offered_late) == []  # hết hạn ⇒ không gửi tin


async def test_a_result_after_expiry_is_409(world: World) -> None:
    drill_id = await offered(world, start=timedelta(hours=-6), length=timedelta(hours=1))
    async with get_sessionmaker().begin() as session:
        await DrillService.expire(session, now=utc_now())
    assert (await row(drill_id)).status == "expired"
    assert (await result(world, drill_id, {"status": "completed", "answers": right()})).status_code == 409


async def test_cancel_only_works_before_the_drill_has_started(world: World) -> None:
    ok = await make_drill(world.family_id, world.member_id)
    started = await make_drill(world.family_id, world.sibling_id, status="in_progress", started_at=utc_now())
    async with get_sessionmaker().begin() as session:
        await DrillService.cancel(session, family_id=world.family_id, drill_id=ok)
    assert (await row(ok)).status == "expired"
    with pytest.raises(InvalidDrillTransition):
        async with get_sessionmaker().begin() as session:
            await DrillService.cancel(session, family_id=world.family_id, drill_id=started)
    from hoicon.services.drill_service import DrillNotFound

    with pytest.raises(DrillNotFound):
        async with get_sessionmaker().begin() as session:
            await DrillService.cancel(session, family_id=world.other_family_id, drill_id=ok)


def test_the_transition_table_has_no_edge_out_of_a_final_state() -> None:
    final = {"passed", "failed", "aborted", "declined", "expired"}
    assert set(ALLOWED) == {"scheduled", "offered", "in_progress"} | final
    for state in final:
        assert ALLOWED[state] == frozenset(), state
    every_target = set().union(*ALLOWED.values())
    assert every_target <= set(ALLOWED)
    assert "scheduled" not in every_target  # không quay về "đã đặt lịch"


async def test_an_illegal_transition_is_refused_by_the_one_function(world: World) -> None:
    drill_id = await make_drill(world.family_id, world.member_id)
    async with get_sessionmaker().begin() as session:
        drill = await session.get(Drill, drill_id)
        assert drill is not None
        with pytest.raises(InvalidDrillTransition):
            DrillService.advance(drill, "passed")  # scheduled → passed: không có cạnh
        assert drill.status == "scheduled"


# --- Web người giám hộ: POST/GET /v1/guardian/drills (spec 028 FR-011, T021) ------------------------------------------


def _guardian_validator(name: str) -> Draft202012Validator:
    resources = []
    for path in SCHEMAS.glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        resources.append((doc["$id"], Resource.from_contents(doc)))
    schema = json.loads((SCHEMAS / f"{name}.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=Registry().with_resources(resources), format_checker=FormatChecker())


GUARDIAN_LIST = _guardian_validator("guardian_drill_list")
GUARDIAN_REQUEST = _guardian_validator("guardian_drill_request")
GUARDIAN_ORIGIN = {"Origin": "http://localhost:3100"}


def guardian_token(w: World) -> str:
    from hoicon.api.auth import issue_guardian_access_token

    return issue_guardian_access_token(w.guardian_id, w.family_id)


def request_body(w: World, **changes: Any) -> dict[str, Any]:
    start = utc_now() + timedelta(hours=2)
    body = {
        "member_id": str(w.member_id),
        "script_id": SCRIPT_ID,
        "window_start": start.isoformat(),
        "window_end": (start + timedelta(hours=1)).isoformat(),
    }
    return {**body, **changes}


async def schedule_via_api(w: World, body: dict[str, Any], token: str | None = None) -> Any:
    return await call(
        "POST", "/v1/guardian/drills", token=token or guardian_token(w), json=body, headers=GUARDIAN_ORIGIN
    )


async def test_guardian_schedules_a_drill_and_it_shows_in_the_list(world: World) -> None:
    body = request_body(world)
    assert list(GUARDIAN_REQUEST.iter_errors(body)) == []
    res = await schedule_via_api(world, body)
    assert res.status_code == 201, res.text
    created = res.json()
    assert list(GUARDIAN_LIST.iter_errors(created)) == [] and len(created["drills"]) == 1
    item = created["drills"][0]
    assert item["status"] == "scheduled" and item["is_drill"] is True and item["member_alias"] == "Mẹ"
    assert item["script_title"] == SCRIPT["title"] and item["score"] is None
    assert res.headers["cache-control"] == "no-store"
    stored = await row(UUID(item["drill_id"]))
    assert stored.scheduled_by == str(world.guardian_id)  # người đặt lịch được ghi lại
    listing = await call("GET", "/v1/guardian/drills", token=guardian_token(world))
    assert listing.status_code == 200 and list(GUARDIAN_LIST.iter_errors(listing.json())) == []
    assert [d["drill_id"] for d in listing.json()["drills"]] == [item["drill_id"]]


async def test_the_list_is_newest_first_and_never_shows_another_family(world: World) -> None:
    older = await make_drill(world.family_id, world.member_id, start=timedelta(days=-3), status="expired")
    newer = await make_drill(world.family_id, world.member_id, start=timedelta(hours=3))
    await make_drill(world.other_family_id, world.other_member_id)
    ids = [
        d["drill_id"] for d in (await call("GET", "/v1/guardian/drills", token=guardian_token(world))).json()["drills"]
    ]
    assert ids == [str(newer), str(older)]


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"script_id": "drill_khong_co"}, "script_unknown"),
        ({"window_start": "2020-01-01T00:00:00+00:00", "window_end": "2020-01-01T01:00:00+00:00"}, "window_past"),
        ({"member_id": str(new_id())}, "member_not_found"),
    ],
)
async def test_refusals_are_422_with_the_service_code_and_write_nothing(
    world: World, changes: dict[str, Any], code: str
) -> None:
    res = await schedule_via_api(world, request_body(world, **changes))
    assert res.status_code == 422 and res.json() == {"detail": code}
    assert (await call("GET", "/v1/guardian/drills", token=guardian_token(world))).json() == {"drills": []}


async def test_a_member_of_another_family_and_a_missing_consent_are_refused(world: World) -> None:
    res = await schedule_via_api(world, request_body(world, member_id=str(world.other_member_id)))
    assert res.status_code == 422 and res.json() == {"detail": "member_not_found"}
    res = await schedule_via_api(world, request_body(world, member_id=str(world.sibling_id)))  # chưa có đồng ý `drills`
    assert res.status_code == 422 and res.json() == {"detail": "consent_missing"}


async def test_overlap_and_monthly_limit_come_back_as_codes(world: World) -> None:
    assert (await schedule_via_api(world, request_body(world))).status_code == 201
    assert (await schedule_via_api(world, request_body(world))).json() == {"detail": "window_overlaps"}


async def test_guardian_drill_routes_need_a_guardian_session_and_a_valid_body(world: World) -> None:
    assert (await call("GET", "/v1/guardian/drills")).status_code == 401
    assert (
        await call("POST", "/v1/guardian/drills", json=request_body(world), headers=GUARDIAN_ORIGIN)
    ).status_code == 401
    assert (
        await call("GET", "/v1/guardian/drills", token=world.token)
    ).status_code == 401  # JWT thiết bị không phải phiên web
    extra = request_body(world, note="văn bản tự do")
    assert (await schedule_via_api(world, extra)).status_code == 422  # extra="forbid": không trường tự do
    bad_time = request_body(world, window_start="không-phải-giờ")
    assert (await schedule_via_api(world, bad_time)).status_code == 422
