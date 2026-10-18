"""Spec 026 (FR-009, SC-002, SC-004, SC-006): `GET /v1/threat-list` — ảnh chụp bucket k-ẩn danh (ADR-011).

Mọi h1 dưới đây là băm của một nhãn tùy ý (HƯ CẤU), không liên quan số điện thoại nào.
"""

import base64
import hashlib
import json
import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from consent_support import call, pair_device
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import delete, select, text

from hoicon.api.routers import lookups
from hoicon.config import get_settings
from hoicon.db.models import Device, ThreatIndicator
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_h1
from hoicon.domain.threat_bucket import bucket24, shift
from hoicon.ops import threat_list
from hoicon.services import threat_list_service

pytestmark = pytest.mark.integration

SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "schemas" / "threat_list.v1.json").read_text(encoding="utf-8")
)
VERSION = "test-spec026-snapshot"
LABELS = ("alpha", "bravo", "charlie", "delta", "echo")


def fake_h1(label: str) -> str:
    return hashlib.sha256(f"fixture:{label}".encode()).hexdigest()


def indicator(label: str, **extra: Any) -> dict[str, Any]:
    return {"h1": fake_h1(label), "source": "fixture", "confidence": 0.8, "last3": "123", **extra}


def seed(*indicators: dict[str, Any], is_demo: bool = True) -> dict[str, Any]:
    return {"version": VERSION, "is_demo": is_demo, "indicators": list(indicators)}


def valid(doc: Any) -> list[str]:
    return [e.message for e in Draft202012Validator(SCHEMA, format_checker=FormatChecker()).iter_errors(doc)]


def decode(doc: dict[str, Any]) -> list[int]:
    raw = base64.b64decode(doc["buckets_b64"], validate=True)
    assert len(raw) == 3 * doc["count"]
    return [int.from_bytes(raw[i : i + 3], "big") for i in range(0, len(raw), 3)]


def bucket_of(label: str, bits: int = 22) -> int:
    return shift(bucket24(fake_h1(label)), bits)


@pytest.fixture(autouse=True)
async def clean(device_world: Any, fake_data_key: None) -> AsyncGenerator[None]:
    lookups.reset_limits()
    threat_list_service.reset_cache()
    yield
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(ThreatIndicator).where(ThreatIndicator.list_version == VERSION))
    lookups.reset_limits()
    threat_list_service.reset_cache()
    get_settings.cache_clear()


@pytest.fixture
async def token(device_world: Any) -> str:
    return (await pair_device(device_world.code))["access_token"]


async def load(*indicators: dict[str, Any], is_demo: bool = True) -> None:
    await threat_list.load_seed(get_sessionmaker(), seed(*indicators, is_demo=is_demo), env="dev")
    threat_list_service.reset_cache()


async def get(token: str | None, since: str | None = None) -> Any:
    path = "/v1/threat-list" + (f"?since={since}" if since is not None else "")
    return await call("GET", path, token=token)


def test_my_labels_land_in_distinct_buckets() -> None:
    assert len({bucket_of(label) for label in LABELS}) == len(LABELS)


async def test_payload_matches_the_contract_and_lists_sorted_unique_buckets(token: str) -> None:
    await load(*(indicator(label) for label in LABELS))
    resp = await get(token)
    assert resp.status_code == 200, resp.text
    doc = resp.json()
    assert valid(doc) == []
    assert doc["bucket_bits"] == 22
    buckets = decode(doc)
    assert buckets == sorted(set(buckets))
    assert all(0 <= value < 2**22 for value in buckets)
    assert {bucket_of(label) for label in LABELS} <= set(buckets)
    assert doc["count"] == len(buckets)


async def test_response_has_no_h1_hmac_or_last3(token: str) -> None:
    await load(*(indicator(label) for label in LABELS))
    resp = await get(token)
    for label in LABELS:
        assert fake_h1(label) not in resp.text
        assert hmac_h1(fake_h1(label))[1] not in resp.text
    assert set(resp.json()) == {"version", "bucket_bits", "count", "buckets_b64", "generated_at"}
    assert "last3" not in resp.text


async def test_same_since_gets_304_and_other_since_gets_200(token: str) -> None:
    await load(indicator("alpha"))
    version = (await get(token)).json()["version"]
    again = await get(token, since=version)
    assert again.status_code == 304
    assert again.content == b""
    assert (await get(token, since="0" * 16)).status_code == 200
    await load(indicator("alpha"), indicator("bravo"))
    changed = await get(token, since=version)
    assert changed.status_code == 200
    assert changed.json()["version"] != version


@pytest.mark.parametrize("since", ["", "abc", "G" * 16, "0" * 17, "A" * 16])
async def test_malformed_since_is_422(token: str, since: str) -> None:
    assert (await get(token, since=since)).status_code == 422


async def test_version_changes_only_when_the_content_changes(token: str) -> None:
    await load(indicator("alpha"), indicator("bravo"))
    first = (await get(token)).json()
    await load(indicator("alpha"), indicator("bravo"))  # nạp lại ⇒ bản mã mới nhưng cùng bucket
    second = (await get(token)).json()
    assert first["version"] == second["version"]
    assert first["buckets_b64"] == second["buckets_b64"]


async def test_expired_rows_disappear_from_the_snapshot(token: str) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    await load(indicator("alpha"), indicator("bravo", expires_at=past))
    buckets = set(decode((await get(token)).json()))
    assert bucket_of("alpha") in buckets
    assert bucket_of("bravo") not in buckets


async def test_rows_without_bucket_enc_are_not_sent(token: str) -> None:
    await threat_list.load_seed(get_sessionmaker(), seed(indicator("alpha")), env="dev", with_bucket=False)
    threat_list_service.reset_cache()
    assert bucket_of("alpha") not in set(decode((await get(token)).json()))
    await load(indicator("alpha"))
    assert bucket_of("alpha") in set(decode((await get(token)).json()))


async def test_a_tampered_row_is_skipped_instead_of_failing_the_endpoint(token: str) -> None:
    await load(indicator("alpha"), indicator("bravo"))
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text(
                "update threat_indicators set bucket_enc = '1.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'"
                " where value_hmac = :h"
            ),
            {"h": hmac_h1(fake_h1("alpha"))[1]},
        )
    resp = await get(token)
    assert resp.status_code == 200
    buckets = set(decode(resp.json()))
    assert bucket_of("alpha") not in buckets
    assert bucket_of("bravo") in buckets


@pytest.mark.parametrize(
    ("skipped", "total", "expected"),
    [
        (0, 0, False),
        (0, 50, False),
        (1, 2, False),
        (2, 10, False),
        (1, 1, True),
        (2, 2, True),
        (3, 60, False),
        (3, 50, True),
        (5, 100, False),
        (6, 100, True),
        (50, 50, True),
    ],
)
def test_undecodable_threshold(skipped: int, total: int, expected: bool) -> None:
    assert threat_list_service.too_many_undecodable(skipped, total) is expected


TAMPERED = "1.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


async def tamper(*labels: str) -> None:
    async with get_sessionmaker().begin() as session:
        for label in labels:
            await session.execute(
                text("update threat_indicators set bucket_enc = :b where value_hmac = :h"),
                {"b": TAMPERED, "h": hmac_h1(fake_h1(label))[1]},
            )


async def test_when_most_rows_cannot_be_decoded_the_endpoint_fails_instead_of_serving_an_empty_list(token: str) -> None:
    """Sai khóa dữ liệu ⇒ mọi dòng hỏng. Không được phát ảnh chụp rỗng hợp lệ (máy sẽ thay danh sách tốt bằng nó)."""
    await load(*(indicator(label) for label in LABELS))
    good = await get(token)
    assert good.status_code == 200 and len(decode(good.json())) == len(LABELS)
    await tamper(*LABELS)
    threat_list_service.reset_cache()
    resp = await get(token)
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "Dịch vụ chưa sẵn sàng"
    assert TAMPERED not in resp.text
    assert lookups._threat_list_hits[next(iter(lookups._threat_list_hits))] is not None  # còn theo dõi thiết bị


async def test_a_failed_snapshot_is_not_cached_and_the_failure_does_not_use_up_the_day(token: str) -> None:
    await load(*(indicator(label) for label in LABELS))
    await tamper(*LABELS)
    threat_list_service.reset_cache()
    for _ in range(lookups.THREAT_LIST_PER_DAY + 3):  # lỗi phía ta không tốn lượt trong ngày của máy
        assert (await get(token)).status_code == 503
    await load(*(indicator(label) for label in LABELS))  # nạp lại bản mã đúng ⇒ hồi phục ngay, không chờ hết đệm
    assert (await get(token)).status_code == 200


async def test_a_few_stray_bad_rows_among_many_are_still_skipped(token: str) -> None:
    labels = [f"row{i:02d}" for i in range(60)]
    await load(*(indicator(label) for label in labels))
    await tamper(labels[0], labels[1])  # 2 dòng: dưới ngưỡng 3 ⇒ chỉ bỏ qua
    threat_list_service.reset_cache()
    resp = await get(token)
    assert resp.status_code == 200, resp.text
    buckets = set(decode(resp.json()))
    assert bucket_of(labels[2]) in buckets and bucket_of(labels[0]) not in buckets
    await tamper(labels[2], labels[3])  # 4/60 > 5% và ≥ 3 ⇒ lỗi
    threat_list_service.reset_cache()
    assert (await get(token)).status_code == 503


async def test_production_never_ships_demo_rows(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    await load(indicator("alpha"), is_demo=True)
    await load(indicator("bravo"), is_demo=False)
    monkeypatch.setenv("HOICON_ENV", "prod")
    get_settings.cache_clear()
    threat_list_service.reset_cache()
    buckets = set(decode((await get(token)).json()))
    assert bucket_of("alpha") not in buckets
    assert bucket_of("bravo") in buckets
    monkeypatch.setenv("HOICON_ENV", "dev")
    get_settings.cache_clear()
    threat_list_service.reset_cache()
    assert {bucket_of("alpha"), bucket_of("bravo")} <= set(decode((await get(token)).json()))


@pytest.mark.parametrize("env", ["staging", "production", ""])
async def test_only_known_dev_environments_ship_demo_rows(
    token: str, monkeypatch: pytest.MonkeyPatch, env: str
) -> None:
    await load(indicator("alpha"), is_demo=True)
    monkeypatch.setenv("HOICON_ENV", env)
    get_settings.cache_clear()
    threat_list_service.reset_cache()
    assert bucket_of("alpha") not in set(decode((await get(token)).json()))


@pytest.mark.parametrize("bits", [16, 20, 24])
async def test_bucket_bits_setting_changes_the_shift(token: str, monkeypatch: pytest.MonkeyPatch, bits: int) -> None:
    await load(*(indicator(label) for label in LABELS))
    monkeypatch.setenv("HOICON_THREAT_BUCKET_BITS", str(bits))
    get_settings.cache_clear()
    threat_list_service.reset_cache()
    doc = (await get(token)).json()
    assert doc["bucket_bits"] == bits
    assert valid(doc) == []
    assert {bucket_of(label, bits) for label in LABELS} <= set(decode(doc))


@pytest.mark.parametrize("bits", ["15", "25", "0", "-3"])
def test_bucket_bits_outside_16_to_24_is_refused(monkeypatch: pytest.MonkeyPatch, bits: str) -> None:
    monkeypatch.setenv("HOICON_THREAT_BUCKET_BITS", bits)
    get_settings.cache_clear()
    with pytest.raises(ValueError, match="threat_bucket_bits"):
        get_settings()
    get_settings.cache_clear()


async def test_snapshot_is_cached_for_five_minutes(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    await load(indicator("alpha"))
    built = 0
    real = threat_list_service.build_snapshot

    async def counting(*args: Any, **kwargs: Any) -> Any:
        nonlocal built
        built += 1
        return await real(*args, **kwargs)

    monkeypatch.setattr(threat_list_service, "build_snapshot", counting)
    await get(token)
    await get(token)
    assert built == 1
    now = time.monotonic()
    monkeypatch.setattr(threat_list_service, "_now", lambda: now + threat_list_service.CACHE_TTL_S + 1)
    await get(token)
    assert built == 2


async def test_sync_records_the_list_version_on_the_device(token: str, device_world: Any) -> None:
    await load(indicator("alpha"))
    version = (await get(token)).json()["version"]
    async with get_sessionmaker()() as session:
        stored = await session.scalar(
            select(Device.threat_list_version).where(Device.family_id == device_world.family_id)
        )
    assert stored == version


async def test_requires_a_device_token(token: str, device_world: Any) -> None:
    assert (await get(None)).status_code == 401
    assert (await get("not-a-token")).status_code == 401
    async with get_sessionmaker().begin() as session:
        await session.execute(
            text("update devices set revoked_at = now() where family_id = :f"), {"f": device_world.family_id}
        )
    assert (await get(token)).status_code == 401


async def test_24_syncs_a_day_then_429(token: str) -> None:
    await load(indicator("alpha"))
    version = (await get(token)).json()["version"]
    for _ in range(23):
        assert (await get(token, since=version)).status_code == 304
    resp = await get(token)
    assert resp.status_code == 429
    assert 1 <= int(resp.headers["Retry-After"]) <= 86400


async def test_empty_list_is_a_valid_empty_snapshot(token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def nothing(*_: Any, **__: Any) -> Any:
        return threat_list_service.empty_snapshot(22)

    monkeypatch.setattr(threat_list_service, "build_snapshot", nothing)
    doc = (await get(token)).json()
    assert valid(doc) == []
    assert (doc["count"], doc["buckets_b64"]) == (0, "")


async def test_concurrent_requests_at_expiry_build_the_snapshot_once(
    token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    await load(indicator("alpha"))
    built = 0
    real = threat_list_service.build_snapshot

    async def slow(*args: Any, **kwargs: Any) -> Any:
        nonlocal built
        built += 1
        await asyncio.sleep(0.05)
        return await real(*args, **kwargs)

    monkeypatch.setattr(threat_list_service, "build_snapshot", slow)
    sessions = get_sessionmaker()
    await asyncio.gather(*(threat_list_service.get_snapshot(sessions, 22, "dev") for _ in range(8)))
    assert built == 1


async def test_a_server_side_failure_does_not_use_up_the_daily_quota(
    token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    await load(indicator("alpha"))

    async def broken(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("thiếu khóa")

    real = threat_list_service.get_snapshot
    monkeypatch.setattr(threat_list_service, "get_snapshot", broken)
    for _ in range(30):
        assert (await get(token)).status_code == 503
    monkeypatch.setattr(threat_list_service, "get_snapshot", real)
    assert (await get(token)).status_code == 200
