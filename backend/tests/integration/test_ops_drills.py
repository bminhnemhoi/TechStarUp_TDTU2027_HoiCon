"""Spec 028 FR-007: lệnh ops `schedule`/`list`/`cancel` — dùng chung `DrillService`, chỉ in id + trạng thái."""

import argparse
import re
import secrets
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest
from consent_support import SHA, purge_family
from sqlalchemy import func, select

from hoicon.config import get_settings
from hoicon.db.models import Consent, Drill, Family, Member
from hoicon.db.session import get_sessionmaker
from hoicon.ops import drills as ops

pytestmark = pytest.mark.integration

SCRIPT = "drill_police_safe_account"


@pytest.fixture
async def family(require_db: None) -> AsyncGenerator[dict[str, UUID]]:
    async with get_sessionmaker().begin() as session:
        fam = Family(display_name=f"test-028-ops-{secrets.token_hex(3)}", region="nam", is_demo=True)
        session.add(fam)
        await session.flush()
        elder = Member(family_id=fam.id, role="protected", alias="Bà Tư")
        session.add(elder)
        await session.flush()
        session.add(
            Consent(
                family_id=fam.id,
                member_id=elder.id,
                purpose="drills",
                granted=True,
                consent_version="v1.0",
                text_sha256=SHA,
                channel="app",
            )
        )
        ids = {"family": fam.id, "member": elder.id}
    yield ids
    await purge_family(ids["family"])


def parse(*argv: str) -> argparse.Namespace:
    return ops.build_parser().parse_args(list(argv))


async def count(family_id: UUID) -> int:
    async with get_sessionmaker()() as session:
        return await session.scalar(select(func.count()).select_from(Drill).where(Drill.family_id == family_id)) or 0


async def test_schedule_now_creates_a_drill_that_is_offered_right_away(
    family: dict[str, UUID], capsys: pytest.CaptureFixture[str]
) -> None:
    code = await ops.execute(
        parse("schedule", "--family", str(family["family"]), "--at", "now", "--minutes", "30", "--script", SCRIPT)
    )
    out = capsys.readouterr().out
    assert code == 0 and "Đã đặt lịch" in out
    async with get_sessionmaker()() as session:
        drill = (await session.scalars(select(Drill).where(Drill.family_id == family["family"]))).one()
    assert drill.scheduled_by == "ops" and drill.status == "scheduled" and drill.script_id == SCRIPT
    assert drill.member_id == family["member"]  # gia đình chỉ có một người cao tuổi ⇒ tự chọn
    assert str(drill.id) in out and "scheduled" in out
    assert drill.window_end - drill.window_start == timedelta(minutes=30)
    assert drill.window_end > datetime.now(UTC)


async def test_output_has_no_name_alias_or_phone(family: dict[str, UUID], capsys: pytest.CaptureFixture[str]) -> None:
    await ops.execute(
        parse("schedule", "--family", str(family["family"]), "--at", "now", "--minutes", "60", "--script", SCRIPT)
    )
    await ops.execute(parse("list", "--family", str(family["family"])))
    out = capsys.readouterr().out
    assert "Bà Tư" not in out and "Tư" not in out
    # UUID v7 (id bài) có thể ngẫu nhiên chứa ≥ 9 chữ số liền nhau ⇒ bỏ UUID trước khi dò số điện thoại (hết chập chờn)
    without_ids = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<id>", out)
    assert not re.search(r"\d{9,}", without_ids)


async def test_list_shows_the_drills_newest_first(family: dict[str, UUID], capsys: pytest.CaptureFixture[str]) -> None:
    base = datetime.now(UTC) + timedelta(days=2)
    for i in range(2):
        at = (base + timedelta(hours=3 * i)).isoformat()
        assert (
            await ops.execute(
                parse("schedule", "--family", str(family["family"]), "--at", at, "--minutes", "60", "--script", SCRIPT)
            )
            == 0
        )
    capsys.readouterr()
    assert await ops.execute(parse("list", "--family", str(family["family"]))) == 0
    out = capsys.readouterr().out
    assert out.count(" · scheduled · ") == 2 and "Tổng: 2 bài" in out


async def test_a_refusal_prints_the_code_and_changes_nothing(
    family: dict[str, UUID], capsys: pytest.CaptureFixture[str]
) -> None:
    code = await ops.execute(
        parse(
            "schedule",
            "--family",
            str(family["family"]),
            "--at",
            "now",
            "--minutes",
            "60",
            "--script",
            "drill_khong_co",
        )
    )
    out = capsys.readouterr().out
    assert code == 2 and "script_unknown" in out
    assert await count(family["family"]) == 0


async def test_consent_missing_is_refused(capsys: pytest.CaptureFixture[str], family: dict[str, UUID]) -> None:
    async with get_sessionmaker().begin() as session:
        other = Member(family_id=family["family"], role="protected")
        session.add(other)
        await session.flush()
        other_id = other.id
    code = await ops.execute(
        parse(
            "schedule",
            "--family",
            str(family["family"]),
            "--member",
            str(other_id),
            "--at",
            "now",
            "--minutes",
            "60",
            "--script",
            SCRIPT,
        )
    )
    assert code == 2 and "consent_missing" in capsys.readouterr().out


async def test_two_elders_need_an_explicit_member(family: dict[str, UUID], capsys: pytest.CaptureFixture[str]) -> None:
    async with get_sessionmaker().begin() as session:
        session.add(Member(family_id=family["family"], role="protected"))
    code = await ops.execute(
        parse("schedule", "--family", str(family["family"]), "--at", "now", "--minutes", "60", "--script", SCRIPT)
    )
    assert code == 2 and "--member" in capsys.readouterr().out
    assert await count(family["family"]) == 0


@pytest.mark.parametrize(
    "argv",
    [
        ["schedule", "--family", "khong-phai-uuid", "--at", "now", "--minutes", "60", "--script", SCRIPT],
        ["schedule", "--family", str(UUID(int=1)), "--at", "mai", "--minutes", "60", "--script", SCRIPT],
        [
            "schedule",
            "--family",
            str(UUID(int=1)),
            "--at",
            "2026-10-20T09:00:00",
            "--minutes",
            "60",
            "--script",
            SCRIPT,
        ],
        ["schedule", "--family", str(UUID(int=1)), "--at", "now", "--minutes", "29", "--script", SCRIPT],
        ["schedule", "--family", str(UUID(int=1)), "--at", "now", "--minutes", "241", "--script", SCRIPT],
        ["schedule", "--family", str(UUID(int=1)), "--at", "now", "--minutes", "x", "--script", SCRIPT],
    ],
    ids=["family", "at-word", "at-no-tz", "min-29", "min-241", "min-nan"],
)
def test_bad_arguments_are_rejected_before_touching_the_database(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_:
        ops.build_parser().parse_args(argv)
    assert exit_.value.code == 2


async def test_outside_dev_a_write_needs_confirm_and_still_needs_an_approved_script(
    family: dict[str, UUID], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    try:
        base = ["schedule", "--family", str(family["family"]), "--at", "now", "--minutes", "60", "--script", SCRIPT]
        assert await ops.execute(parse(*base)) == 2
        assert "--confirm" in capsys.readouterr().out
        assert await ops.execute(parse(*base, "--confirm")) == 2  # có --confirm nhưng kịch bản chưa duyệt
        assert "script_not_approved" in capsys.readouterr().out
        assert await count(family["family"]) == 0
        assert await ops.execute(parse("list", "--family", str(family["family"]))) == 0  # đọc thì không cần --confirm
    finally:
        get_settings.cache_clear()


async def test_cancel_before_the_drill_starts(family: dict[str, UUID], capsys: pytest.CaptureFixture[str]) -> None:
    await ops.execute(
        parse("schedule", "--family", str(family["family"]), "--at", "now", "--minutes", "60", "--script", SCRIPT)
    )
    async with get_sessionmaker()() as session:
        drill_id = (await session.scalars(select(Drill.id).where(Drill.family_id == family["family"]))).one()
    capsys.readouterr()
    assert await ops.execute(parse("cancel", "--family", str(family["family"]), "--drill", str(drill_id))) == 0
    assert "Đã hủy" in capsys.readouterr().out
    async with get_sessionmaker()() as session:
        assert (await session.get(Drill, drill_id)).status == "expired"  # type: ignore[union-attr]
    # hủy lần nữa: bài đã ở trạng thái cuối
    assert await ops.execute(parse("cancel", "--family", str(family["family"]), "--drill", str(drill_id))) == 2


async def test_cancel_refuses_a_drill_of_another_family(
    family: dict[str, UUID], capsys: pytest.CaptureFixture[str]
) -> None:
    other = UUID(int=secrets.randbits(120))
    code = await ops.execute(parse("cancel", "--family", str(family["family"]), "--drill", str(other)))
    assert code == 2 and "không thấy" in capsys.readouterr().out


def test_settings_default_is_a_dev_environment_for_the_unit_tests() -> None:
    assert get_settings().env in ("dev", "test", "ci"), "test ops giả định môi trường dev; đặt HOICON_ENV=dev"
    _: Any = None
