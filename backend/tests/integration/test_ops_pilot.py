"""Spec 029 FR-004 (T006/T007): `ops pilot enroll | report | gate-m2`."""

import json
import re
import secrets
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import select

from hoicon.db.ids import new_id
from hoicon.db.models import Consent, Device, DeviceHeartbeat, Family, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.ops import pilot

pytestmark = pytest.mark.integration

NOW = datetime(2026, 12, 14, 3, 0, tzinfo=UTC)  # đúng mốc 15 phút
DAY_SLOTS = 96
SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
MEMBER_ALIAS = "Bà Tám Thử Nghiệm"  # bí danh thành viên: KHÔNG được lọt ra báo cáo


def validator() -> Draft202012Validator:
    docs = [json.loads(p.read_text("utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = json.loads((SCHEMAS / "pilot_report.v1.json").read_text("utf-8"))
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


Make = Callable[..., Any]


@pytest.fixture
async def make_family(require_db: None) -> AsyncGenerator[Make]:
    """Dựng gia đình thí điểm (plan=pilot) có một người được bảo vệ (bí danh + HMAC Zalo giả) và một thiết bị."""
    created: list[UUID] = []

    async def make(
        *,
        plan: str = "pilot",
        demo: bool = False,
        created_ago: timedelta = timedelta(days=30),
        revoked_ago: timedelta | None = None,
        slots_seen: int = 0,
        protected: bool = True,
        research: bool | None = True,
    ) -> dict[str, Any]:
        """`research`: True = đã đồng ý `pilot_research`; False = đã rút; None = chưa từng trả lời."""
        async with get_sessionmaker().begin() as session:
            hmac = secrets.token_hex(32)  # giả, duy nhất mỗi thành viên
            fam = Family(display_name=f"test-029-{secrets.token_hex(3)}", region="nam", plan=plan, is_demo=demo)
            session.add(fam)
            await session.flush()
            member = Member(
                family_id=fam.id,
                role="protected",
                alias=MEMBER_ALIAS,
                zalo_bot_id="bot-test",
                zalo_user_hmac=hmac,
                zalo_hmac_kid=1,
                zalo_chat_enc="enc",
            )
            session.add(member)
            await session.flush()
            if research is not None:
                session.add(
                    Consent(
                        family_id=fam.id,
                        member_id=member.id,
                        purpose="pilot_research",
                        granted=research,
                        consent_version="v1.0",
                        text_sha256=SHA,
                        channel="app",
                    )
                )
            device = Device(
                family_id=fam.id,
                member_id=member.id,
                app_version="0.3.0",
                rules_version="r1",
                device_secret_hash=secrets.token_hex(32),
                created_at=NOW - created_ago,
                revoked_at=None if revoked_ago is None else NOW - revoked_ago,
                permission_state={"call_screening_role": True, "usage_access": True, "battery_unrestricted": False},
            )
            session.add(device)
            await session.flush()
            # `slots_seen` khung gần nhất trước `NOW` (hoặc trước lúc thu hồi)
            end = NOW if revoked_ago is None else NOW - revoked_ago
            last = int(end.timestamp()) // 900
            session.add_all(
                DeviceHeartbeat(
                    device_id=device.id, slot=datetime.fromtimestamp((last - i - 1) * 900, tz=UTC), protected=protected
                )
                for i in range(slots_seen)
            )
            ids = {"family": fam.id, "member": member.id, "device": device.id, "name": fam.display_name, "hmac": hmac}
        created.append(fam.id)
        return ids

    yield make
    for family_id in created:
        await purge_family(family_id)


def one(report: dict[str, Any], name: str) -> dict[str, Any]:
    (family,) = [f for f in report["families"] if f["alias"] == name]
    return family


async def report_for(days: int = 1) -> dict[str, Any]:
    return await pilot.build_report(get_sessionmaker(), days, now=NOW)


# --- độ phủ: 100% / 50% / 0% -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(("seen", "expected_cov"), [(DAY_SLOTS, 1.0), (DAY_SLOTS // 2, 0.5), (0, 0.0)])
async def test_coverage_is_slots_seen_over_slots_expected(make_family: Make, seen: int, expected_cov: float) -> None:
    ids = await make_family(slots_seen=seen)
    (device,) = one(await report_for(), ids["name"])["devices"]
    assert device["coverage"] == expected_cov
    assert (device["slots_expected"], device["slots_seen"]) == (DAY_SLOTS, seen)
    assert device["device"] == str(ids["device"])[:8]


async def test_a_device_paired_mid_period_is_measured_from_its_own_start(make_family: Make) -> None:
    """Ghép đôi 12 giờ trước, đủ heartbeat từ lúc đó ⇒ 100% (mẫu số 48 khung, không phải 96)."""
    ids = await make_family(created_ago=timedelta(hours=12), slots_seen=48)
    (device,) = one(await report_for(), ids["name"])["devices"]
    assert (device["slots_expected"], device["coverage"]) == (48, 1.0)


async def test_a_device_with_no_full_slot_yet_has_no_coverage_instead_of_zero(make_family: Make) -> None:
    ids = await make_family(created_ago=timedelta(minutes=5))
    (device,) = one(await report_for(), ids["name"])["devices"]
    assert device["coverage"] is None and device["protected_ratio"] is None and device["slots_expected"] == 0


async def test_a_revoked_device_is_measured_only_until_it_was_revoked(make_family: Make) -> None:
    ids = await make_family(revoked_ago=timedelta(hours=12), slots_seen=48)
    (device,) = one(await report_for(), ids["name"])["devices"]
    assert device["revoked"] is True and (device["slots_expected"], device["coverage"]) == (48, 1.0)


async def test_a_device_revoked_before_the_period_is_left_out(make_family: Make) -> None:
    ids = await make_family(revoked_ago=timedelta(days=5), slots_seen=10)
    assert one(await report_for(days=1), ids["name"])["devices"] == []


async def test_protected_ratio_and_permissions_off(make_family: Make) -> None:
    ids = await make_family(slots_seen=DAY_SLOTS, protected=False)
    (device,) = one(await report_for(), ids["name"])["devices"]
    assert device["protected_ratio"] == 0.0 and device["permissions_off"] == ["battery_unrestricted"]


async def test_only_pilot_families_that_are_not_demo_are_reported(make_family: Make) -> None:
    free = await make_family(plan="free")
    demo = await make_family(demo=True)
    pilot_family = await make_family()
    names = {f["alias"] for f in (await report_for())["families"]}
    assert pilot_family["name"] in names and free["name"] not in names and demo["name"] not in names


async def test_incidents_and_false_alarms_count_only_real_ones_in_the_period(make_family: Make) -> None:
    ids = await make_family()

    def inc(**changes: Any) -> Incident:
        base: dict[str, Any] = {
            "id": new_id(), "family_id": ids["family"], "member_id": ids["member"], "device_id": ids["device"],
            "level": "high", "rule_floor": "high", "state": "detected", "opened_at": NOW - timedelta(hours=1),
        }  # fmt: skip
        return Incident(**{**base, **changes})

    closed = {"closed_at": NOW - timedelta(minutes=30)}
    async with get_sessionmaker().begin() as session:
        session.add_all(
            [
                inc(),
                inc(state="resolved_false_alarm", **closed),
                inc(state="resolved_safe", **closed),
                inc(is_demo=True),  # demo: không tính
                inc(is_drill=True, drill_id=new_id()),  # diễn tập: không tính
                inc(opened_at=NOW - timedelta(days=3)),  # ngoài kỳ 1 ngày
            ]
        )
    family = one(await report_for(days=1), ids["name"])
    assert (family["incidents"], family["false_alarms"]) == (3, 1)


# --- hợp đồng + không PII --------------------------------------------------------------------------------------------


async def test_the_json_report_matches_pilot_report_v1(make_family: Make) -> None:
    await make_family(slots_seen=DAY_SLOTS)
    await make_family(created_ago=timedelta(minutes=1))  # coverage null vẫn khớp hợp đồng
    report = await report_for()
    assert not list(validator().iter_errors(json.loads(json.dumps(report))))


async def test_no_output_carries_member_names_hmacs_or_phone_like_numbers(
    make_family: Make, capsys: pytest.CaptureFixture[str]
) -> None:
    ids = await make_family(slots_seen=10)
    for argv in (["report", "--days", "1"], ["report", "--days", "1", "--json"], ["gate-m2", "--days", "1"]):
        await pilot.execute(pilot.build_parser().parse_args(argv))
    out = capsys.readouterr().out
    assert MEMBER_ALIAS not in out and ids["hmac"] not in out and "enc" not in out.split()
    assert not re.search(r"\d{8,}", out)  # không dãy chữ số dài như số điện thoại/tài khoản
    ids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}", out)
    assert ids == []  # không có UUID đầy đủ


# --- enroll ----------------------------------------------------------------------------------------------------------


async def plan_of(family_id: UUID) -> str:
    async with get_sessionmaker()() as session:
        return (await session.scalars(select(Family.plan).where(Family.id == family_id))).one()


async def run(*argv: str) -> int:
    return await pilot.execute(pilot.build_parser().parse_args(list(argv)))


async def test_enroll_without_confirm_adult_is_refused_and_changes_nothing(
    make_family: Make, capsys: pytest.CaptureFixture[str]
) -> None:
    ids = await make_family(plan="free")
    assert await run("enroll", "--family", str(ids["family"])) == 2
    assert "--confirm-adult" in capsys.readouterr().out and await plan_of(ids["family"]) == "free"


async def test_enroll_with_confirm_adult_sets_the_pilot_plan_and_is_idempotent(make_family: Make) -> None:
    ids = await make_family(plan="free")
    assert await run("enroll", "--family", str(ids["family"]), "--confirm-adult") == 0
    assert await plan_of(ids["family"]) == "pilot"
    assert await run("enroll", "--family", str(ids["family"]), "--confirm-adult") == 0
    assert await plan_of(ids["family"]) == "pilot"


async def test_enroll_refuses_demo_and_unknown_families(make_family: Make) -> None:
    demo = await make_family(plan="free", demo=True)
    assert await run("enroll", "--family", str(demo["family"]), "--confirm-adult") == 2
    assert await plan_of(demo["family"]) == "free"
    assert await run("enroll", "--family", str(new_id()), "--confirm-adult") == 2


def test_the_adult_confirmation_is_required_by_the_library_function_too() -> None:
    import asyncio

    with pytest.raises(pilot.EnrollError):
        asyncio.run(pilot.enroll(None, new_id(), confirm_adult=False))  # type: ignore[arg-type]


# --- gate-m2 ---------------------------------------------------------------------------------------------------------


def report_with(families: int, seen: int, expected: int = 100) -> dict[str, Any]:
    device = {"slots_expected": expected, "slots_seen": seen, "coverage": seen / expected}
    return {"days": 7, "families": [{"alias": f"G{i}", "devices": [device]} for i in range(families)]}


def status_of(criteria: list[pilot.Criterion], name_part: str) -> str:
    (match,) = [c for c in criteria if name_part in c.name]
    return match.status


def gate(report: dict[str, Any], **manual: Any) -> list[pilot.Criterion]:
    args: dict[str, Any] = {
        "crash_free": 99.5,
        "crash_source": "Play vitals, n=40",
        "real_devices": 1,
        "no_high_findings": True,
    }
    return pilot.evaluate_gate(report, **{**args, **manual})


def test_gate_passes_when_every_criterion_is_met() -> None:
    criteria = gate(report_with(5, 95))
    assert all(c.status == pilot.OK for c in criteria)


@pytest.mark.parametrize(("seen", "verdict"), [(90, pilot.OK), (89, pilot.FAIL)])
def test_the_coverage_threshold_is_90_percent(seen: int, verdict: str) -> None:
    assert status_of(gate(report_with(5, seen)), "Độ phủ") == verdict


def test_fewer_than_five_families_fail() -> None:
    assert status_of(gate(report_with(4, 100)), "gia đình") == pilot.FAIL


def test_manual_criteria_without_a_number_are_never_counted_as_passed() -> None:
    criteria = gate(report_with(5, 100), crash_free=None, crash_source=None, real_devices=None, no_high_findings=False)
    assert [c.status for c in criteria if c.manual] == [pilot.MISSING, pilot.MISSING, pilot.MISSING]
    assert all(c.manual for c in criteria if "Crash" in c.name or "máy thật" in c.name or "High" in c.name)
    assert (
        status_of(gate(report_with(5, 100), crash_source=None), "Crash") == pilot.MISSING
    )  # thiếu nguồn cũng không đạt


def test_a_low_crash_free_number_fails() -> None:
    assert status_of(gate(report_with(5, 100), crash_free=98.9), "Crash") == pilot.FAIL


def test_no_devices_yet_means_no_coverage_number() -> None:
    assert status_of(gate({"days": 7, "families": []}), "Độ phủ") == pilot.MISSING


async def test_the_gate_command_exit_code_and_manual_marks(
    make_family: Make, capsys: pytest.CaptureFixture[str]
) -> None:
    await make_family(slots_seen=10)
    code = await run("gate-m2", "--days", "1")
    out = capsys.readouterr().out
    assert code == 1 and "CHƯA ĐẠT" in out and out.count("NHẬP TAY") == 3 and "CHƯA CÓ SỐ" in out
