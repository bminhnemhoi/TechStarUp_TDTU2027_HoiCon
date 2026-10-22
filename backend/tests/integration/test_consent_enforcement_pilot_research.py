# ruff: noqa: F811
"""Spec 011 FR-006 / SC-006 (T014): `pilot_research` được thực thi. Heartbeat của người chưa (hoặc không còn) đồng ý vẫn
được nhận (bảo vệ cần nó) nhưng không vào báo cáo thí điểm; số gộp theo nhóm ẩn khi dưới 3 gia đình."""

import secrets
from datetime import timedelta

import pytest
from consent_support import SHA
from test_ops_pilot import DAY_SLOTS, NOW, Make, make_family, one, report_for  # noqa: F401 (make_family là fixture)

from hoicon.db.models import Consent, Device, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.ops import pilot
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration


# --- Đồng ý `pilot_research` (spec 011 FR-006, T014) ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_consent_cache() -> None:
    consent_gate.reset_cache()


@pytest.mark.parametrize("research", [None, False])
async def test_a_family_without_research_consent_is_not_in_the_report(make_family: Make, research: bool | None) -> None:
    ids = await make_family(slots_seen=DAY_SLOTS, research=research)
    assert ids["name"] not in [f["alias"] for f in (await report_for())["families"]]


async def test_only_the_consenting_devices_of_a_family_are_reported(make_family: Make) -> None:
    ids = await make_family(slots_seen=DAY_SLOTS)
    async with get_sessionmaker().begin() as session:
        other = Member(family_id=ids["family"], role="protected", alias="Ông Hai Thử Nghiệm")
        session.add(other)
        await session.flush()
        session.add(
            Device(
                family_id=ids["family"],
                member_id=other.id,
                app_version="0.3.0",
                rules_version="r1",
                device_secret_hash=secrets.token_hex(32),
                created_at=NOW - timedelta(days=30),
            )
        )
    family = one(await report_for(), ids["name"])
    assert [d["device"] for d in family["devices"]] == [str(ids["device"])[:8]]


async def test_incidents_of_a_member_who_did_not_consent_are_not_counted(make_family: Make) -> None:
    yes = await make_family(slots_seen=DAY_SLOTS)
    async with get_sessionmaker().begin() as session:
        session.add(
            Incident(
                family_id=yes["family"],
                member_id=yes["member"],
                device_id=yes["device"],
                state="resolved_false_alarm",
                level="high",
                rule_floor="high",
                opened_at=NOW - timedelta(hours=2),
                closed_at=NOW - timedelta(hours=1),
                outcome="false_alarm",
            )
        )
    assert one(await report_for(), yes["name"])["incidents"] == 1
    async with get_sessionmaker().begin() as session:  # rút đồng ý ⇒ nhà biến khỏi báo cáo
        session.add(
            Consent(
                family_id=yes["family"],
                member_id=yes["member"],
                purpose="pilot_research",
                granted=False,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
    consent_gate.reset_cache()
    assert yes["name"] not in [f["alias"] for f in (await report_for())["families"]]


async def test_the_pooled_coverage_is_hidden_below_three_families(make_family: Make) -> None:
    await make_family(slots_seen=DAY_SLOTS)
    await make_family(slots_seen=DAY_SLOTS)
    report = await report_for()
    own = [f for f in report["families"] if f["alias"].startswith("test-029-")]
    few = {**report, "families": own[:2]}
    criteria = {
        c.name: c
        for c in pilot.evaluate_gate(few, crash_free=None, crash_source=None, real_devices=None, no_high_findings=False)
    }
    coverage = criteria["Độ phủ heartbeat ≥ 90%"]
    assert coverage.status == pilot.MISSING and "ẩn" in coverage.detail and "%" not in coverage.detail
