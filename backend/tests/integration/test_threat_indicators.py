"""Spec 003 US1: danh sách đe dọa nằm trong Postgres dạng HMAC (ADR-006) — nạp idempotent, tra cứu, không có h1."""

import hashlib
import json
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, select, text

from hoicon.config import get_settings
from hoicon.db.models import ThreatIndicator
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_h1
from hoicon.mcp_servers.threat import lookup_h1
from hoicon.ops import threat_list

pytestmark = pytest.mark.integration

VERSION = "test-spec003"
DEMO_H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"


def fake_h1(label: str) -> str:
    """h1 GIẢ (băm một nhãn tùy ý, không liên quan số điện thoại nào)."""
    return hashlib.sha256(f"fixture:{label}".encode()).hexdigest()


def seed_doc(*indicators: dict[str, Any], is_demo: bool = True) -> dict[str, Any]:
    return {"version": VERSION, "is_demo": is_demo, "indicators": list(indicators)}


def indicator(label: str, **extra: Any) -> dict[str, Any]:
    return {"h1": fake_h1(label), "source": "fixture", "confidence": 0.8, **extra}


@pytest.fixture(autouse=True)
async def clean(require_db: None, fake_pepper: None) -> AsyncGenerator[None]:
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == VERSION))


async def rows() -> list[ThreatIndicator]:
    async with get_sessionmaker()() as session:
        return list(await session.scalars(select(ThreatIndicator).where(ThreatIndicator.list_version == VERSION)))


async def test_load_is_idempotent_and_stores_only_the_hmac() -> None:
    doc = seed_doc(indicator("a", last3="002", tactic="impersonation_authority"))
    assert await threat_list.load_seed(get_sessionmaker(), doc, env="dev") == (1, 0)
    assert await threat_list.load_seed(get_sessionmaker(), doc, env="dev") == (0, 1)
    (row,) = await rows()
    assert row.value_hmac == hmac_h1(fake_h1("a"))[1] and row.value_kid == 1 and row.is_demo is True
    assert (row.last3, row.tactic, row.kind) == ("002", "impersonation_authority", "phone")


async def test_reload_updates_source_confidence_and_last_seen() -> None:
    await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a")), env="dev")
    (before,) = await rows()
    changed = indicator("a", tactic="fake_delivery") | {"confidence": 0.5, "source": "fixture-2"}
    await threat_list.load_seed(get_sessionmaker(), seed_doc(changed), env="dev")
    (after,) = await rows()
    assert (after.source, float(after.confidence), after.tactic) == ("fixture-2", 0.5, "fake_delivery")
    assert after.last_seen >= before.last_seen and after.first_seen == before.first_seen


async def test_no_byte_of_the_table_contains_an_h1() -> None:
    await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a"), indicator("b")), env="dev")
    async with get_sessionmaker()() as session:
        dump = "\n".join(await session.scalars(text("select t::text from threat_indicators t")))
    assert fake_h1("a") not in dump and fake_h1("b") not in dump


async def test_invalid_batch_is_rejected_whole() -> None:
    bad = seed_doc(indicator("ok"), {"h1": "0900000002", "source": "fixture", "confidence": 0.8})
    with pytest.raises(threat_list.SeedError):
        await threat_list.load_seed(get_sessionmaker(), bad, env="dev")
    too_sure = seed_doc(indicator("ok"), indicator("x", confidence=1.5))
    with pytest.raises(threat_list.SeedError):
        await threat_list.load_seed(get_sessionmaker(), too_sure, env="dev")
    assert await rows() == []  # dòng hợp lệ đứng TRƯỚC dòng hỏng cũng không được ghi


@pytest.mark.parametrize("extra", [{"last3": "0021"}, {"tactic": ""}, {"expires_at": "không phải ngày"}])
async def test_malformed_optional_fields_are_rejected(extra: dict[str, Any]) -> None:
    with pytest.raises(threat_list.SeedError):
        await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a", **extra)), env="dev")
    assert await rows() == []


@pytest.mark.parametrize("env", ["prod", "production", " PROD "])
async def test_demo_seed_is_refused_in_production(env: str) -> None:
    with pytest.raises(threat_list.SeedError, match="demo"):
        await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a")), env=env)
    assert await rows() == []
    # tệp không demo thì nạp được ở prod
    assert await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a"), is_demo=False), env=env) == (1, 0)


async def test_cli_prints_only_counts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(seed_doc(indicator("a"))), encoding="utf-8")
    assert await threat_list.run(path) == 0
    out = capsys.readouterr().out
    assert "thêm 1" in out and "cập nhật 0" in out
    assert fake_h1("a") not in out and hmac_h1(fake_h1("a"))[1] not in out
    assert await threat_list.run(path) == 0
    assert "thêm 0" in capsys.readouterr().out
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    assert await threat_list.run(path) == 2  # seed demo ở prod
    assert "từ chối" in capsys.readouterr().out.lower()


async def test_cli_rejects_unreadable_or_broken_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert await threat_list.run(tmp_path / "khong-co.json") == 2
    broken = tmp_path / "broken.json"
    broken.write_text("{nội dung hỏng chứa 0900000002", encoding="utf-8")
    assert await threat_list.run(broken) == 2
    out = capsys.readouterr().out
    assert "không đọc được" in out
    assert "nội dung hỏng" not in out and "0900000002" not in out  # không lặp lại nội dung tệp


async def test_lookup_flagged_unknown_and_expired() -> None:
    sessions = get_sessionmaker()
    past, future = datetime.now(UTC) - timedelta(days=1), datetime.now(UTC) + timedelta(days=1)
    doc = seed_doc(
        indicator("hit", tactic="fake_delivery") | {"confidence": 0.7},
        indicator("old", expires_at=past.isoformat()),
        indicator("fresh", expires_at=future.isoformat()),
    )
    await threat_list.load_seed(sessions, doc, env="dev")
    hit = await lookup_h1(sessions, fake_h1("hit"))
    assert hit.verdict == "flagged" and hit.source == "fixture" and hit.confidence == 0.7
    assert hit.tactic == "fake_delivery" and hit.list_version == VERSION
    assert (await lookup_h1(sessions, fake_h1("fresh"))).verdict == "flagged"
    assert (await lookup_h1(sessions, fake_h1("old"))).verdict == "unknown"  # quá hạn
    assert (await lookup_h1(sessions, fake_h1("never-loaded"))).verdict == "unknown"


async def test_lookup_rejects_raw_numbers() -> None:
    with pytest.raises(ValueError, match="h1"):
        await lookup_h1(get_sessionmaker(), "0900000002")


async def test_row_loaded_under_old_kid_is_found_after_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a")), env="dev")  # kid 1
    monkeypatch.setenv("HOICON_PHONE_PEPPER_2", "22" * 32)
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "2")
    get_settings.cache_clear()
    assert (await lookup_h1(get_sessionmaker(), fake_h1("a"))).verdict == "flagged"
    await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("b")), env="dev")  # nạp dùng kid hiện hành
    assert {r.value_kid for r in await rows()} == {1, 2}


async def test_demo_seed_file_loads_and_matches_the_known_demo_caller(seeded_threat: dict[str, Any]) -> None:
    verdict = await lookup_h1(get_sessionmaker(), DEMO_H1)
    assert verdict.verdict == "flagged" and verdict.list_version == seeded_threat["version"]
    async with get_sessionmaker()() as session:
        demo_rows = (await session.scalars(select(ThreatIndicator).where(ThreatIndicator.is_demo))).all()
        dump = "\n".join(await session.scalars(text("select t::text from threat_indicators t")))
    assert demo_rows and DEMO_H1 not in dump  # SC-001


async def test_lookup_p95() -> None:
    """SC-005: mục tiêu p95 ≤ 20 ms; test chỉ chặn ở 100 ms (máy dev có lúc bị swap), số thật xem evidence.md."""
    sessions = get_sessionmaker()
    await threat_list.load_seed(sessions, seed_doc(indicator("hit")), env="dev")
    await lookup_h1(sessions, fake_h1("hit"))  # khởi động kết nối
    samples: list[float] = []
    for i in range(200):
        label = "hit" if i % 2 else f"miss-{i}"
        started = time.perf_counter()
        await lookup_h1(sessions, fake_h1(label))
        samples.append((time.perf_counter() - started) * 1000)
    p95 = sorted(samples)[int(0.95 * len(samples)) - 1]
    print(f"\nlookup_h1 p95 = {p95:.2f} ms (n=200)")
    assert p95 <= 100


@pytest.mark.parametrize("env", ["staging", "", "Production ", "live"])
async def test_demo_seed_is_only_allowed_in_known_non_production_envs(env: str) -> None:
    """Danh sách trắng (dev/test/ci): quên đặt HOICON_ENV=prod hoặc đặt tên lạ vẫn không nạp được dữ liệu demo."""
    with pytest.raises(threat_list.SeedError, match="demo"):
        await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a")), env=env)
    assert await rows() == []


@pytest.mark.parametrize("env", ["dev", "test", "ci", " DEV "])
async def test_demo_seed_loads_in_dev_test_and_ci(env: str) -> None:
    assert await threat_list.load_seed(get_sessionmaker(), seed_doc(indicator("a")), env=env) == (1, 0)


async def test_h1_with_a_trailing_newline_is_not_accepted() -> None:
    with pytest.raises(ValueError, match="h1"):
        await lookup_h1(get_sessionmaker(), fake_h1("a") + "\n")
    with pytest.raises(threat_list.SeedError):
        await threat_list.load_seed(
            get_sessionmaker(), seed_doc({**indicator("a"), "h1": fake_h1("a") + "\n"}), env="dev"
        )
    with pytest.raises(ValueError):
        hmac_h1(fake_h1("a") + "\n")
