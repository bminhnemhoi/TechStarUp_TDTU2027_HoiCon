"""Spec 032 FR-004/005/008: job `coach_weekly` — nội dung tất định, opt-out theo người, một tin mỗi tuần."""

import json
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from coach_support import NOW, payload_text, purge, seed_family, vn_utc, watch_jobs
from sqlalchemy import select

from hoicon.agents.texts import AI_DISCLOSURE
from hoicon.db.models import AgentRun, AgentStep, Drill, Incident
from hoicon.db.session import get_sessionmaker
from hoicon.services import coach_service

pytestmark = pytest.mark.integration

SUNDAY_EVENING = vn_utc(19, 5, day=25)  # Chủ nhật 25/10/2026 19:05 giờ VN
WEEK = "2026-W43"


@pytest.fixture
async def worlds() -> AsyncIterator[list[SimpleNamespace]]:
    made: list[SimpleNamespace] = []
    yield made
    for w in made:
        await purge(w)


async def make(worlds: list[SimpleNamespace], **kwargs: object) -> SimpleNamespace:
    w = await seed_family(last_heartbeat=SUNDAY_EVENING - timedelta(minutes=5), **kwargs)
    worlds.append(w)
    return w


async def run(w: SimpleNamespace, tips: list[str] | None = None) -> int:
    return await coach_service.run_coach_weekly(
        get_sessionmaker(), now=SUNDAY_EVENING, tips=tips or [], family_id=w.family
    )


def weekly(jobs: list) -> list:
    return [j for j in jobs if j.idempotency_key.startswith("weekly:")]


async def add_incident(
    w: SimpleNamespace, *, state: str, drill: bool = False, demo: bool = False, days_ago: int = 2
) -> None:
    async with get_sessionmaker().begin() as session:
        incident = Incident(
            family_id=w.family,
            member_id=w.protected,
            state=state,
            level="high",
            rule_floor="high",
            opened_at=SUNDAY_EVENING - timedelta(days=days_ago),
            is_drill=drill,
            drill_id=w.protected if drill else None,
        )
        incident.is_demo = demo
        if state in ("resolved_safe", "closed"):
            incident.closed_at = SUNDAY_EVENING - timedelta(days=1)
        session.add(incident)


async def add_drill(w: SimpleNamespace, status: str = "passed") -> None:
    start = SUNDAY_EVENING - timedelta(days=1)
    async with get_sessionmaker().begin() as session:
        session.add(
            Drill(
                family_id=w.family,
                member_id=w.protected,
                scheduled_by="ops",
                script_id="drill_bank_card_locked",
                window_start=start,
                window_end=start + timedelta(hours=2),
                status=status,
                **(
                    {"score": 3, "offered_at": start, "started_at": start, "completed_at": start}
                    if status in ("passed", "failed")
                    else {}
                ),
            )
        )


async def test_the_digest_counts_real_incidents_coverage_and_drills(require_db: None, worlds: list) -> None:
    w = await make(worlds)
    await add_incident(w, state="resolved_safe")
    await add_incident(w, state="case_open")
    await add_incident(w, state="resolved_safe", drill=True)  # diễn tập: không đếm
    await add_incident(w, state="resolved_safe", demo=True)  # demo: không đếm
    await add_incident(w, state="resolved_safe", days_ago=9)  # ngoài 7 ngày: không đếm
    await add_drill(w)
    await add_drill(w, status="aborted")  # chưa làm xong: không đếm
    assert await run(w) == 2
    jobs = weekly(await watch_jobs(w, "weekly"))
    assert {j.payload["member_id"] for j in jobs} == {str(w.guardian1), str(w.guardian2)}
    text = payload_text(jobs[0])
    assert (
        text.startswith(AI_DISCLOSURE)
        and "đã nhắc Mẹ dừng lại 2 lần, trong đó 1 lần đã có người nhà xử lý xong" in text
    )
    assert "đã làm 1 bài luyện tập" in text and "Nhắn TẮT TIN TUẦN" in text
    assert "an toàn" not in text.lower()
    for job in jobs:
        assert job.payload["urgent"] is False and job.payload["quota_class"] == "digest"
        assert job.payload["is_demo"] is False and job.payload["is_drill"] is False
        assert job.payload["protected_member_id"] == str(w.protected)  # spec 037: cổng đồng ý lúc gửi cần biết


async def test_a_quiet_week_still_states_the_coverage_without_saying_safe(require_db: None, worlds: list) -> None:
    w = await make(worlds)
    assert await run(w) == 2
    text = payload_text(weekly(await watch_jobs(w, "weekly"))[0])
    assert "không thấy dấu hiệu đáng ngờ nào" in text and "an toàn" not in text.lower()
    assert "khoảng" in text or "chưa đủ dữ liệu" in text


async def test_a_guardian_who_turned_the_digest_off_gets_nothing_the_other_still_does(
    require_db: None, worlds: list
) -> None:
    w = await make(worlds, digest=(False, True))
    assert await run(w) == 1
    (job,) = weekly(await watch_jobs(w, "weekly"))
    assert job.payload["member_id"] == str(w.guardian2)


async def test_running_twice_in_the_same_week_sends_one_message_per_guardian(require_db: None, worlds: list) -> None:
    w = await make(worlds)
    await run(w)
    assert await run(w) == 0
    assert len(weekly(await watch_jobs(w, "weekly"))) == 2
    async with get_sessionmaker()() as session:
        runs = list(await session.scalars(select(AgentRun).where(AgentRun.thread_id == f"coach:{w.family}:{WEEK}")))
    assert len(runs) == 1 and runs[0].graph == "coach" and runs[0].incident_id is None


async def test_excluded_families_get_nothing(require_db: None, worlds: list) -> None:
    no_device = await seed_family(revoked=True, last_heartbeat=None)  # chỉ có thiết bị đã thu hồi
    no_consent = await seed_family(consent=False, last_heartbeat=SUNDAY_EVENING)
    demo = await seed_family(demo=True, last_heartbeat=SUNDAY_EVENING)
    no_chat = await seed_family(with_chat=False, last_heartbeat=SUNDAY_EVENING)
    worlds.extend([no_device, no_consent, demo, no_chat])
    for w in (no_device, no_consent, demo, no_chat):
        assert await run(w) == 0 and await watch_jobs(w, "weekly") == []


async def test_the_trace_has_collect_compose_send_with_counts_and_no_message_text(
    require_db: None, worlds: list
) -> None:
    w = await make(worlds)
    await add_incident(w, state="resolved_safe")
    await run(w)
    async with get_sessionmaker()() as session:
        run_row = await session.scalar(select(AgentRun).where(AgentRun.thread_id == f"coach:{w.family}:{WEEK}"))
        steps = list(
            await session.scalars(
                select(AgentStep).where(AgentStep.run_id == run_row.id).order_by(AgentStep.at, AgentStep.id)
            )
        )
    assert {s.node for s in steps} == {"collect", "compose", "send"}
    dump = json.dumps([s.output for s in steps], ensure_ascii=False)
    assert "Bản tin tuần" not in dump and AI_DISCLOSURE not in dump and "Mẹ" not in dump
    send = next(s for s in steps if s.node == "send")
    assert send.output == {"queued": 2, "template": "weekly_digest"}


async def test_tips_appear_in_dev_and_in_prod_only_when_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    file = tmp_path / "tips.vi.yaml"
    file.write_text(
        "approved: false\ntips:\n  - id: a\n    text_vi: Một mẹo.\n  - id: b\n    text_vi: Mẹo hai.\n", "utf-8"
    )
    monkeypatch.setattr(coach_service, "TIPS_FILE", file)
    assert coach_service.load_tips(prod=False) == ["Một mẹo.", "Mẹo hai."]
    assert coach_service.load_tips(prod=True) == []  # chưa duyệt ⇒ bản prod bỏ dòng mẹo
    file.write_text(file.read_text("utf-8").replace("approved: false", "approved: true"), "utf-8")
    assert coach_service.load_tips(prod=True) == ["Một mẹo.", "Mẹo hai."]
    assert coach_service.tip_for(SUNDAY_EVENING, ["x", "y"]) in ("x", "y")
    assert coach_service.tip_for(SUNDAY_EVENING, []) is None


async def test_the_real_tips_file_is_pending_approval_and_clean() -> None:
    import re

    import yaml

    doc = yaml.safe_load(coach_service.TIPS_FILE.read_text("utf-8"))
    assert doc["approved"] is False and len(doc["tips"]) >= 3
    for tip in doc["tips"]:
        assert not re.search(r"\d{3,}|https?://|an toàn", tip["text_vi"]), tip["id"]


async def test_the_tip_line_is_included_when_a_tip_is_given(require_db: None, worlds: list) -> None:
    w = await make(worlds)
    await run(w, tips=["Cúp máy rồi gọi lại số đã lưu."])
    text = payload_text(weekly(await watch_jobs(w, "weekly"))[0])
    assert "Mẹo tuần này: Cúp máy rồi gọi lại số đã lưu." in text


def test_the_weekly_job_runs_on_sunday_at_seven_pm_vietnam_time() -> None:
    monday = vn_utc(9, day=19)
    run_at = coach_service.weekly_run_at(monday)
    assert (run_at.weekday(), run_at.hour, run_at.minute) == (6, 19, 0) and run_at.day == 25
    assert coach_service.iso_week(SUNDAY_EVENING) == WEEK and NOW.weekday() == 1
