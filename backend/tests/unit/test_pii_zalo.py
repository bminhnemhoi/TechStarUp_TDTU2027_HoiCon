"""Định danh Zalo (spec 002 D1): `chat_id` mã hóa AES-256-GCM (để gửi) + HMAC tra cứu; không lưu ID thô (luật 1–2)."""

import base64
import hashlib
import hmac
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from hoicon.config import get_settings
from hoicon.domain.pii import decrypt_chat_id, encrypt_chat_id, hmac_h1, hmac_zalo

PEPPER = "11" * 32
KEY_1 = "aa" * 32
KEY_2 = "bb" * 32
CHAT_ID = "fixture-chat-0001"
CTX = "cd" * 32  # = HMAC của người sở hữu (zalo_user_hmac); gắn vào dữ liệu xác thực


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", PEPPER)
    monkeypatch.setenv("HOICON_DATA_KEY_KID", "1")
    monkeypatch.setenv("HOICON_DATA_KEY_1", KEY_1)
    yield
    get_settings.cache_clear()


def _rotated(monkeypatch: pytest.MonkeyPatch, current_kid: int) -> None:
    """Stub cấu hình có thêm khóa 2 — `Settings` chỉ khai báo `data_key_1` cho tới khi thật sự xoay khóa."""
    stub = SimpleNamespace(data_key_kid=current_kid, data_key_1=SecretStr(KEY_1), data_key_2=SecretStr(KEY_2))
    monkeypatch.setattr("hoicon.domain.pii.get_settings", lambda: stub)


def test_chat_id_roundtrip_including_non_ascii() -> None:
    for chat_id in (CHAT_ID, "6ede9afa66b88fe6d6a9", "chat-Việt-Nam"):
        assert decrypt_chat_id(encrypt_chat_id(chat_id, CTX), CTX) == chat_id


def test_stored_value_has_kid_prefix_and_hides_plaintext() -> None:
    stored = encrypt_chat_id(CHAT_ID, CTX)
    kid, _, blob = stored.partition(".")
    assert kid == "1"
    assert CHAT_ID not in stored
    assert CHAT_ID.encode() not in base64.urlsafe_b64decode(blob)


def test_nonce_differs_each_time_but_both_decrypt() -> None:
    first, second = encrypt_chat_id(CHAT_ID, CTX), encrypt_chat_id(CHAT_ID, CTX)
    assert first != second
    assert decrypt_chat_id(first, CTX) == decrypt_chat_id(second, CTX) == CHAT_ID


def test_tampered_ciphertext_is_rejected_without_leaking() -> None:
    kid, _, blob = encrypt_chat_id(CHAT_ID, CTX).partition(".")
    raw = bytearray(base64.urlsafe_b64decode(blob))
    raw[-1] ^= 0x01
    with pytest.raises(ValueError) as info:
        decrypt_chat_id(f"{kid}.{base64.urlsafe_b64encode(bytes(raw)).decode()}", CTX)
    assert CHAT_ID not in str(info.value) + repr(info.value)
    assert info.value.__context__ is None


def test_wrong_kid_fails_both_when_key_missing_and_when_key_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    body = encrypt_chat_id(CHAT_ID, CTX, kid=1).partition(".")[2]
    with pytest.raises(RuntimeError, match="HOICON_DATA_KEY_2"):
        decrypt_chat_id(f"2.{body}", CTX)  # chưa có khóa 2
    _rotated(monkeypatch, current_kid=1)
    with pytest.raises(ValueError):
        decrypt_chat_id(f"2.{body}", CTX)  # khóa 2 có nhưng không phải khóa đã mã hóa (kid còn nằm trong AAD)


def test_key_rotation_old_rows_still_decrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    old = encrypt_chat_id(CHAT_ID, CTX)
    _rotated(monkeypatch, current_kid=2)
    fresh = encrypt_chat_id(CHAT_ID, CTX)
    assert old.startswith("1.") and fresh.startswith("2.")
    assert decrypt_chat_id(old, CTX) == decrypt_chat_id(fresh, CTX) == CHAT_ID


@pytest.mark.parametrize("bad", ["", "abc", "1.", "x.AAAA", "1.%%%", "1.AAAA", ".AAAA", "١.AAAA"])
def test_malformed_stored_value_is_value_error(bad: str) -> None:
    with pytest.raises(ValueError):
        decrypt_chat_id(bad, CTX)


def test_empty_chat_id_is_rejected() -> None:
    with pytest.raises(ValueError):
        encrypt_chat_id("", CTX)


@pytest.mark.parametrize("bad_key", ["", "zz" * 32, "aa" * 31, "aa" * 33, f"{'aa' * 32}\n"])
def test_bad_key_is_runtime_error_and_not_echoed(bad_key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DATA_KEY_1", bad_key)
    with pytest.raises(RuntimeError, match="HOICON_DATA_KEY_1") as info:
        encrypt_chat_id(CHAT_ID, CTX)
    assert bad_key.strip() == "" or bad_key.strip() not in str(info.value)


def test_missing_key_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_DATA_KEY_KID", "9")
    with pytest.raises(RuntimeError, match="HOICON_DATA_KEY_9"):
        encrypt_chat_id(CHAT_ID, CTX)


def test_hmac_zalo_is_stable_and_matches_independent_computation() -> None:
    kid, digest = hmac_zalo("fixture-bot-1", "fixture-user-0001")
    # cùng quy ước với hmac_h1: khóa HMAC là chuỗi pepper (hex) ở dạng bytes
    message = b"hoicon:zalo:v1:fixture-bot-1:fixture-user-0001"
    assert (kid, digest) == (1, hmac.new(PEPPER.encode(), message, hashlib.sha256).hexdigest())
    assert hmac_zalo("fixture-bot-1", "fixture-user-0001") == (kid, digest)


def test_hmac_zalo_separates_bots_users_and_phone_hashes() -> None:
    base = hmac_zalo("fixture-bot-1", "fixture-user-0001")[1]
    assert hmac_zalo("fixture-bot-2", "fixture-user-0001")[1] != base
    assert hmac_zalo("fixture-bot-1", "fixture-user-0002")[1] != base
    # cùng pepper nhưng khác miền: không trùng HMAC của h1 số điện thoại (kể cả khi "user_id" trông như h1)
    h1 = hashlib.sha256(b"fixture-user-0001").hexdigest()
    assert hmac_zalo("fixture-bot-1", h1)[1] != hmac_h1(h1)[1]


def test_hmac_zalo_bot_id_cannot_blur_the_bot_user_boundary() -> None:
    with pytest.raises(ValueError):
        hmac_zalo("bot:1", "user")  # ("bot:1","user") không được trùng ("bot","1:user")


@pytest.mark.parametrize(("bot", "user"), [("", "u"), ("b", "")])
def test_hmac_zalo_rejects_empty_ids(bot: str, user: str) -> None:
    with pytest.raises(ValueError):
        hmac_zalo(bot, user)


def test_hmac_zalo_without_pepper_fails_loudly(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "9")
    with pytest.raises(RuntimeError, match="HOICON_PHONE_PEPPER_9"):
        hmac_zalo("fixture-bot-1", "fixture-user-0001")


def test_pairing_code_hash_is_stable_domain_separated_and_hides_code() -> None:
    from hoicon.domain.pii import hmac_pairing_code

    digest = hmac_pairing_code("482913")
    assert digest == hmac_pairing_code("482913") and len(digest) == 64 and "482913" not in digest
    assert digest != hmac_pairing_code("482914")
    assert digest == hmac.new(PEPPER.encode(), b"hoicon:pairing:v1:482913", hashlib.sha256).hexdigest()


@pytest.mark.parametrize("bad", ["", "12345", "1234567", "12345a", "١٢٣٤٥٦", "482913\n"])
def test_pairing_code_must_be_exactly_six_ascii_digits(bad: str) -> None:
    from hoicon.domain.pii import hmac_pairing_code

    with pytest.raises(ValueError):
        hmac_pairing_code(bad)


def test_ciphertext_is_bound_to_its_owner_so_swapping_rows_cannot_redirect_alerts() -> None:
    stored = encrypt_chat_id(CHAT_ID, CTX)
    assert decrypt_chat_id(stored, CTX) == CHAT_ID
    with pytest.raises(ValueError):
        decrypt_chat_id(stored, "ef" * 32)  # bản mã của người này không giải được dưới danh nghĩa người khác


def test_context_is_mandatory() -> None:
    with pytest.raises(ValueError):
        encrypt_chat_id(CHAT_ID, "")
    with pytest.raises(ValueError):
        decrypt_chat_id(encrypt_chat_id(CHAT_ID, CTX), "")
