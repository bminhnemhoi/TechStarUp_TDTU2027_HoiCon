"""Spec 020 (FR-004, T2): JWT thiết bị HS256 30 ngày + refresh token chỉ lưu băm. Không DB."""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from hoicon.api import auth
from hoicon.config import get_settings

KEY = "unit-test-key-" + "x" * 32  # gitleaks:allow — khóa giả của test
IDS = (uuid4(), uuid4(), uuid4())


@pytest.fixture(autouse=True)
def signing_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", KEY)
    yield
    get_settings.cache_clear()


def forge(key: str = KEY, *, algorithm: str = "HS256", **changes: object) -> str:
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": str(IDS[0]),
        "family_id": str(IDS[1]),
        "member_id": str(IDS[2]),
        "role": "protected",
        "iss": auth.ISSUER,
        "aud": auth.AUDIENCE,
        "iat": now,
        "exp": now + timedelta(days=1),
    }
    payload.update(changes)
    return jwt.encode({k: v for k, v in payload.items() if v is not None}, key, algorithm=algorithm)


def test_roundtrip_carries_the_three_ids_and_lives_30_days() -> None:
    token = auth.issue_access_token(*IDS)
    claims = auth.decode_access_token(token)
    assert (claims.device_id, claims.family_id, claims.member_id) == IDS
    raw = jwt.decode(token, KEY, algorithms=["HS256"], audience=auth.AUDIENCE)
    assert raw["role"] == "protected"
    assert raw["exp"] - raw["iat"] == int(timedelta(days=30).total_seconds()) == auth.ACCESS_TTL_S
    assert set(raw) == {"sub", "family_id", "member_id", "role", "iss", "aud", "iat", "exp"}


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(forge("another-key-" + "y" * 32), id="sai khóa"),
        pytest.param(forge(exp=datetime.now(UTC) - timedelta(seconds=5)), id="hết hạn"),
        pytest.param(forge(algorithm="HS512"), id="thuật toán khác"),
        pytest.param(forge(aud="other"), id="sai audience"),
        pytest.param(forge(iss="other"), id="sai issuer"),
        pytest.param(forge(role="guardian"), id="sai vai trò"),
        pytest.param(forge(sub="not-a-uuid"), id="sub không phải uuid"),
        pytest.param(forge(family_id=None), id="thiếu family_id"),
        pytest.param(forge(exp=None), id="thiếu exp"),
        pytest.param(jwt.encode({"sub": str(IDS[0])}, "", algorithm="none"), id="alg none"),
        pytest.param("không-phải-jwt", id="rác"),
        pytest.param("", id="rỗng"),
    ],
)
def test_bad_tokens_are_rejected(token: str) -> None:
    with pytest.raises(auth.DeviceTokenError):
        auth.decode_access_token(token)


def test_tampered_payload_is_rejected() -> None:
    head, _, sig = auth.issue_access_token(*IDS).split(".")
    other = forge(family_id=str(uuid4())).split(".")[1]
    with pytest.raises(auth.DeviceTokenError):
        auth.decode_access_token(f"{head}.{other}.{sig}")


@pytest.mark.parametrize("value", ["", "short"])
def test_missing_or_short_key_refuses_to_sign_or_verify(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    token = forge()  # ký trước khi xóa khóa
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", value)  # rỗng cũng ghi đè được tệp cấu hình cục bộ của máy
    with pytest.raises(auth.DeviceAuthNotConfiguredError):
        auth.issue_access_token(*IDS)
    with pytest.raises(auth.DeviceAuthNotConfiguredError):
        auth.decode_access_token(token)


def test_refresh_token_is_random_and_only_its_sha256_is_kept() -> None:
    token, digest = auth.new_refresh_token()
    assert digest == hashlib.sha256(token.encode()).hexdigest()
    assert len(token) >= 43 and token != digest
    assert auth.new_refresh_token()[0] != token
