"""Spec 020 US1 (FR-003/FR-004, SC-001): `POST /v1/pair` đổi mã 6 số lấy token thiết bị."""

import asyncio
import hashlib
import json
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, select, update

from hoicon.api import auth
from hoicon.api.main import app
from hoicon.api.routers import pairing
from hoicon.db.models import Device, Member, PairingCode
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import hmac_pairing_code

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
GENERIC_400 = "Mã ghép đôi không tồn tại hoặc đã hết hạn"


def body(code: str, **changes: Any) -> dict[str, Any]:
    base = {"code": code, "app_version": "0.2.0-debug", "rules_version": "2026.10.15", "platform": "android"}
    return {**base, **changes}


async def pair(payload: Any, *, client_host: str = "203.0.113.7") -> Any:
    transport = ASGITransport(app=app, client=(client_host, 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/v1/pair", json=payload)


def response_validator() -> Draft202012Validator:
    schema = json.loads((SCHEMAS / "pair_response.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


async def test_valid_code_returns_a_contract_valid_response_and_a_working_token(device_world: Any) -> None:
    resp = await pair(body(device_world.code, device_label="Máy của mẹ"))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert [e.message for e in response_validator().iter_errors(data)] == []
    assert data["family_name"] == device_world.display_name
    assert data["token_type"] == "bearer" and data["expires_in"] == auth.ACCESS_TTL_S == 30 * 24 * 3600
    claims = auth.decode_access_token(data["access_token"])
    assert str(claims.family_id) == data["family_id"] == str(device_world.family_id)
    assert (str(claims.device_id), str(claims.member_id)) == (data["device_id"], data["member_id"])

    async with get_sessionmaker()() as session:
        device = (await session.scalars(select(Device).where(Device.family_id == device_world.family_id))).one()
        member = await session.get(Member, claims.member_id)
    assert str(device.id) == data["device_id"] and device.platform == "android" and device.label == "Máy của mẹ"
    assert (device.app_version, device.rules_version) == ("0.2.0-debug", "2026.10.15")
    assert device.device_secret_hash == hashlib.sha256(data["refresh_token"].encode()).hexdigest()
    assert device.revoked_at is None
    assert member is not None and member.role == "protected" and member.family_id == device_world.family_id


async def test_code_is_consumed_atomically_with_the_device(device_world: Any) -> None:
    assert (await pair(body(device_world.code))).status_code == 200
    async with get_sessionmaker()() as session:
        row = (await session.scalars(select(PairingCode).where(PairingCode.family_id == device_world.family_id))).one()
        assert row.used_at is not None
    again = await pair(body(device_world.code))  # dùng lại ⇒ 400, không tạo thêm thiết bị
    assert again.status_code == 400 and again.json() == {"detail": GENERIC_400}
    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count()).select_from(Device).where(Device.family_id == device_world.family_id)
        )
    assert count == 1


@pytest.mark.parametrize("why", ["sai", "hết hạn"])
async def test_wrong_or_expired_code_gets_the_same_vietnamese_400(device_world: Any, why: str) -> None:
    code = device_world.code
    if why == "sai":
        code = "000000" if code != "000000" else "000001"
    else:
        async with get_sessionmaker().begin() as session:
            await session.execute(
                update(PairingCode)
                .where(PairingCode.family_id == device_world.family_id)
                .values(expires_at=func.now() - timedelta(seconds=1))
            )
    resp = await pair(body(code))
    assert resp.status_code == 400 and resp.json() == {"detail": GENERIC_400}
    async with get_sessionmaker()() as session:
        devices = await session.scalar(
            select(func.count()).select_from(Device).where(Device.family_id == device_world.family_id)
        )
    assert devices == 0


@pytest.mark.parametrize(
    "doc",
    json.loads((SCHEMAS / "fixtures" / "pair_request.v1.invalid.json").read_text(encoding="utf-8")),
    ids=lambda d: d["_why"],
)
async def test_invalid_contract_fixtures_are_rejected_before_touching_the_db(
    doc: dict[str, Any], device_world: Any
) -> None:
    resp = await pair({k: v for k, v in doc.items() if k != "_why"})
    assert resp.status_code == 422


async def test_unknown_fields_and_bad_shapes_are_422(device_world: Any) -> None:
    assert (await pair(body(device_world.code, extra="x"))).status_code == 422
    assert (await pair(body(device_world.code, device_label="x" * 65))).status_code == 422
    assert (await pair(body(device_world.code, app_version=""))).status_code == 422
    assert (await pair(body("1234567"))).status_code == 422
    assert (await pair(body("123456\n"))).status_code == 422  # `$` cho lọt "\n" ở cuối; phải fullmatch
    assert (await pair(["not", "an", "object"])).status_code == 422


async def test_two_devices_racing_for_one_code_only_one_wins(device_world: Any) -> None:
    first, second = await asyncio.gather(pair(body(device_world.code)), pair(body(device_world.code)))
    assert sorted([first.status_code, second.status_code]) == [200, 400]
    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count()).select_from(Device).where(Device.family_id == device_world.family_id)
        )
    assert count == 1


async def test_a_second_code_reuses_the_families_protected_member(device_world: Any) -> None:
    first = (await pair(body(device_world.code))).json()
    second = (await pair(body(await device_world.new_code(), device_label="Máy dự phòng"))).json()
    assert first["member_id"] == second["member_id"] and first["device_id"] != second["device_id"]
    async with get_sessionmaker()() as session:
        members = await session.scalar(
            select(func.count())
            .select_from(Member)
            .where(Member.family_id == device_world.family_id, Member.role == "protected")
        )
    assert members == 1


async def test_repeated_failures_are_throttled_even_for_a_valid_code(device_world: Any) -> None:
    for _ in range(pairing.MAX_FAILURES_PER_CLIENT):
        assert (await pair(body("000000" if device_world.code != "000000" else "000001"))).status_code == 400
    blocked = await pair(body(device_world.code))  # cùng nguồn, mã ĐÚNG nhưng đã quá số lần thử sai
    assert blocked.status_code == 429 and "Retry-After" in blocked.headers
    other = await pair(body(device_world.code), client_host="203.0.113.99")  # nguồn khác không bị vạ lây
    assert other.status_code == 200


async def test_global_failure_cap_stops_a_distributed_guesser(device_world: Any) -> None:
    for i in range(pairing.MAX_FAILURES_GLOBAL):
        await pair(body("000000" if device_world.code != "000000" else "000001"), client_host=f"198.51.100.{i % 250}")
    assert (await pair(body(device_world.code), client_host="203.0.113.50")).status_code == 429


async def test_success_is_not_counted_as_a_failure(device_world: Any) -> None:
    for _ in range(pairing.MAX_FAILURES_PER_CLIENT + 2):
        assert (await pair(body(await device_world.new_code()))).status_code == 200


async def test_nothing_sensitive_reaches_the_logs_or_the_database(
    device_world: Any, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    resp = (await pair(body(device_world.code))).json()
    await pair(body("000000" if device_world.code != "000000" else "000001"))
    for secret in (device_world.code, resp["access_token"], resp["refresh_token"]):
        assert secret not in caplog.text
    async with get_sessionmaker()() as session:
        stored = (
            await session.scalars(select(PairingCode.code_hash).where(PairingCode.family_id == device_world.family_id))
        ).one()
    assert stored == hmac_pairing_code(device_world.code) and stored != device_world.code


async def test_missing_signing_key_is_a_503_and_the_code_is_not_burned(
    device_world: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.config import get_settings

    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "")  # rỗng ghi đè cả tệp cấu hình cục bộ của máy
    get_settings.cache_clear()
    resp = await pair(body(device_world.code))
    assert resp.status_code == 503 and device_world.code not in resp.text
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "integration-test-key-" + "k" * 32)
    get_settings.cache_clear()
    assert (await pair(body(device_world.code))).status_code == 200


async def test_a_burst_of_concurrent_wrong_guesses_cannot_outrun_the_failure_cap(device_world: Any) -> None:
    """Review #1: đếm phải GIỮ CHỖ trước khi chạm DB, nếu không mọi yêu cầu đang bay đều lọt qua ngưỡng."""
    wrong = "000000" if device_world.code != "000000" else "000001"
    results = await asyncio.gather(*(pair(body(wrong)) for _ in range(pairing.MAX_FAILURES_PER_CLIENT * 5)))
    codes = [r.status_code for r in results]
    assert codes.count(400) == pairing.MAX_FAILURES_PER_CLIENT
    assert codes.count(429) == len(codes) - pairing.MAX_FAILURES_PER_CLIENT


async def test_ipv6_sources_in_one_slash_64_share_a_bucket(device_world: Any) -> None:
    wrong = "000000" if device_world.code != "000000" else "000001"
    for i in range(pairing.MAX_FAILURES_PER_CLIENT):
        assert (await pair(body(wrong), client_host=f"2001:db8:1:2::{i + 1:x}")).status_code == 400
    blocked = await pair(body(device_world.code), client_host="2001:db8:1:2:ffff::1")  # cùng /64, địa chỉ khác
    assert blocked.status_code == 429
    assert (await pair(body(device_world.code), client_host="2001:db8:1:3::1")).status_code == 200  # /64 khác


async def test_device_label_is_masked_and_versions_are_constrained(device_world: Any) -> None:
    """Review #4: nhãn máy là chuỗi người dùng gõ ⇒ không được lưu số điện thoại thô (luật 1)."""
    fake_number = "0900000123"  # số hư cấu
    resp = await pair(body(device_world.code, device_label=f"Máy của mẹ {fake_number}"))
    assert resp.status_code == 200
    async with get_sessionmaker()() as session:
        label = (await session.scalars(select(Device.label).where(Device.family_id == device_world.family_id))).one()
    assert fake_number not in label and "123" in label  # che nhưng còn 3 số cuối để nhận ra máy
    for bad in ({"app_version": "1.0 <script>"}, {"rules_version": "a" * 33}, {"app_version": "\n1.0"}):
        assert (await pair(body(await device_world.new_code(), **bad))).status_code == 422


async def test_a_null_device_label_is_accepted(device_world: Any) -> None:
    assert (await pair(body(device_world.code, device_label=None))).status_code == 200
