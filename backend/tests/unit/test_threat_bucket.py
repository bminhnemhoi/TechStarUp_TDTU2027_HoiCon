"""Bucket k-ẩn danh của danh sách đe dọa (spec 026 FR-003, ADR-011): tính bucket, dịch bit, mã hóa `bucket_enc`."""

import base64
import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from hoicon.config import get_settings
from hoicon.domain.threat_bucket import bucket24, decrypt_bucket, encrypt_bucket, shift

KEY_1 = "aa" * 32
KEY_2 = "bb" * 32
HMAC_A = "cd" * 32  # = value_hmac của một chỉ báo giả
HMAC_B = "ef" * 32
VECTORS = Path(__file__).resolve().parents[3] / "docs" / "schemas" / "fixtures" / "h1_vectors.json"


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DATA_KEY_KID", "1")
    monkeypatch.setenv("HOICON_DATA_KEY_1", KEY_1)
    yield
    get_settings.cache_clear()


def _rotated(monkeypatch: pytest.MonkeyPatch, current_kid: int) -> None:
    """Stub cấu hình có thêm khóa 2 — `Settings` chỉ khai báo `data_key_1` cho tới khi thật sự xoay khóa."""
    stub = SimpleNamespace(data_key_kid=current_kid, data_key_1=SecretStr(KEY_1), data_key_2=SecretStr(KEY_2))
    monkeypatch.setattr("hoicon.domain.pii.get_settings", lambda: stub)
    monkeypatch.setattr("hoicon.domain.threat_bucket.get_settings", lambda: stub)


def test_bucket24_fixed_vectors() -> None:
    assert bucket24("3f0f23b3e724e869e1b0552e6c64ea562a022c311476be6dadb58b6011936956") == 0x3F0F23
    assert bucket24("000000" + "f" * 58) == 0
    assert bucket24("ffffff" + "0" * 58) == 0xFFFFFF


def test_bucket24_matches_every_shared_h1_vector() -> None:
    vectors = [v for v in json.loads(VECTORS.read_text(encoding="utf-8"))["vectors"] if v.get("h1")]
    assert len(vectors) >= 5
    for vector in vectors:
        assert bucket24(vector["h1"]) == int(vector["h1"][:6], 16)


@pytest.mark.parametrize("bad", ["", "abc", "A" * 64, "g" * 64, "a" * 63, "a" * 64 + "\n"])
def test_bucket24_rejects_anything_that_is_not_a_lowercase_h1(bad: str) -> None:
    with pytest.raises(ValueError, match="h1"):
        bucket24(bad)


@pytest.mark.parametrize(
    ("bits", "expected"),
    [(24, 0x3F0F23), (22, 0x3F0F23 >> 2), (16, 0x3F0F)],
)
def test_shift_keeps_the_leading_bits(bits: int, expected: int) -> None:
    assert shift(0x3F0F23, bits) == expected


def test_shift_stays_inside_the_bucket_range() -> None:
    for bits in (16, 22, 24):
        assert 0 <= shift(0xFFFFFF, bits) < 2**bits
        assert shift(0, bits) == 0


@pytest.mark.parametrize("bits", [0, 15, 25, 32, -1])
def test_shift_rejects_bits_outside_16_to_24(bits: int) -> None:
    with pytest.raises(ValueError, match="bit"):
        shift(1, bits)


@pytest.mark.parametrize("value", [-1, 2**24, 2**30])
def test_shift_rejects_values_outside_24_bits(value: int) -> None:
    with pytest.raises(ValueError, match="bucket"):
        shift(value, 22)


def test_encrypt_then_decrypt_returns_the_same_bucket() -> None:
    for value in (0, 1, 0x3F0F23, 0xFFFFFF):
        assert decrypt_bucket(encrypt_bucket(value, HMAC_A), HMAC_A) == value


def test_stored_value_carries_the_kid_and_fits_the_column() -> None:
    stored = encrypt_bucket(0x3F0F23, HMAC_A)
    assert stored.startswith("1.")
    assert len(stored) <= 128


def test_every_encryption_uses_a_fresh_nonce() -> None:
    assert encrypt_bucket(0x3F0F23, HMAC_A) != encrypt_bucket(0x3F0F23, HMAC_A)


def test_ciphertext_does_not_contain_the_plain_bucket() -> None:
    value = 0x3F0F23
    stored = encrypt_bucket(value, HMAC_A)
    sealed = base64.urlsafe_b64decode(stored.partition(".")[2])
    assert value.to_bytes(3, "big") not in sealed
    assert format(value, "06x") not in stored
    assert str(value) not in stored


def test_swapping_ciphertext_between_two_indicators_breaks_decryption() -> None:
    stored = encrypt_bucket(0x3F0F23, HMAC_A)
    with pytest.raises(ValueError, match="bucket"):
        decrypt_bucket(stored, HMAC_B)


def test_a_wrong_kid_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _rotated(monkeypatch, 1)
    stored = encrypt_bucket(0x3F0F23, HMAC_A)
    forged = "2." + stored.partition(".")[2]  # đổi tiền tố kid: AAD khác ⇒ giải mã hỏng
    with pytest.raises(ValueError, match="bucket"):
        decrypt_bucket(forged, HMAC_A)


def test_a_missing_key_for_the_kid_raises() -> None:
    stored = encrypt_bucket(0x3F0F23, HMAC_A)
    forged = "7." + stored.partition(".")[2]
    with pytest.raises(RuntimeError, match="HOICON_DATA_KEY_7"):
        decrypt_bucket(forged, HMAC_A)


def test_old_rows_stay_readable_after_the_key_is_rotated(monkeypatch: pytest.MonkeyPatch) -> None:
    _rotated(monkeypatch, 1)
    old = encrypt_bucket(0x123456, HMAC_A)
    _rotated(monkeypatch, 2)
    new = encrypt_bucket(0x123456, HMAC_A)
    assert old.startswith("1.")
    assert new.startswith("2.")
    assert decrypt_bucket(old, HMAC_A) == decrypt_bucket(new, HMAC_A) == 0x123456


@pytest.mark.parametrize("bad", ["", "no-dot", ".blob", "x.blob", "1.", "1.!!!", "1.AAAA"])
def test_malformed_stored_values_raise_without_leaking_data(bad: str) -> None:
    with pytest.raises(ValueError, match="bucket") as excinfo:
        decrypt_bucket(bad, HMAC_A)
    assert "blob" not in str(excinfo.value)
    assert excinfo.value.__cause__ is None


def test_bit_flip_in_the_ciphertext_is_detected() -> None:
    kid, _, blob = encrypt_bucket(0x3F0F23, HMAC_A).partition(".")
    sealed = bytearray(base64.urlsafe_b64decode(blob))
    sealed[-1] ^= 0x01
    with pytest.raises(ValueError, match="bucket"):
        decrypt_bucket(f"{kid}.{base64.urlsafe_b64encode(bytes(sealed)).decode()}", HMAC_A)


def test_encrypt_rejects_out_of_range_buckets_and_empty_context() -> None:
    for bad in (-1, 2**24):
        with pytest.raises(ValueError, match="bucket"):
            encrypt_bucket(bad, HMAC_A)
    with pytest.raises(ValueError, match="value_hmac"):
        encrypt_bucket(1, "")
