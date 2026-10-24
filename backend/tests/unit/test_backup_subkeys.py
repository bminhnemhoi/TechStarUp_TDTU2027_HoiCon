"""Spec 037 FR-005 (D5): sao lưu v2 dùng khóa con theo từng tệp (HKDF + salt ngẫu nhiên 16 byte);
bản v1 cũ vẫn khôi phục được."""

import base64
import io
from pathlib import Path

import pytest

from hoicon.ops import backup as bk

KEY = bytes.fromhex("0f" * 32)
KID = 1
LEGACY = Path(__file__).resolve().parents[1] / "fixtures" / "backup_v1.dump.enc.b64"
LEGACY_PLAIN = b"legacy-block-one|" * 3 + b"legacy-block-two|" * 2 + b"tail"


def seal(chunks: list[bytes]) -> bytes:
    out = io.BytesIO()
    bk.encrypt_stream(iter(chunks), KEY, KID, out)
    return out.getvalue()


def open_(data: bytes, monkeypatch: pytest.MonkeyPatch) -> bytes:
    monkeypatch.setattr(bk, "key_for", lambda kid, settings=None: KEY)
    return b"".join(bk.decrypt_stream(io.BytesIO(data)))


def test_new_files_are_version_2_with_a_random_16_byte_salt() -> None:
    a, b = seal([b"same plaintext"]), seal([b"same plaintext"])
    assert a[4] == 2 and a[:4] == b"HCBK" and bk.HEADER_LEN == 4 + 2 + 16
    assert a[6 : bk.HEADER_LEN] != b[6 : bk.HEADER_LEN]  # salt khác nhau mỗi tệp


def test_two_files_under_the_same_master_key_use_different_subkeys() -> None:
    assert bk._subkey(KEY, b"a" * 16) != bk._subkey(KEY, b"b" * 16)
    assert bk._subkey(KEY, b"a" * 16) != KEY and len(bk._subkey(KEY, b"a" * 16)) == 32


def test_the_ciphertext_of_the_first_block_differs_between_files_even_with_equal_nonce_index() -> None:
    # Nonce của khối 0 giống nhau ở mọi tệp v2 (chỉ số khối), nên an toàn chỉ nhờ khóa con khác nhau.
    first = [seal([b"x" * 64])[bk.HEADER_LEN + 4 :][:64] for _ in range(3)]
    assert len(set(first)) == 3


def test_round_trip_of_the_new_format(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [b"a" * 100, b"b" * 50, b"c"]
    assert open_(seal(chunks), monkeypatch) == b"".join(chunks)


def test_an_old_version_1_backup_still_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    data = base64.b64decode(LEGACY.read_text())
    assert data[4] == 1  # bản sinh bằng mã trước khi đổi định dạng
    assert open_(data, monkeypatch) == LEGACY_PLAIN


def test_flipping_a_salt_byte_fails_to_decrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    data = bytearray(seal([b"payload" * 10]))
    data[8] ^= 0x01  # nằm trong salt ⇒ khóa con khác ⇒ thẻ xác thực sai
    with pytest.raises(bk.BackupError):
        open_(bytes(data), monkeypatch)


def test_a_version_1_file_cannot_be_downgraded_from_a_version_2_one(monkeypatch: pytest.MonkeyPatch) -> None:
    data = bytearray(seal([b"payload" * 10]))
    data[4] = 1  # đổi nhãn phiên bản: AAD/khóa khác ⇒ phải lỗi, không được giải mã
    with pytest.raises(bk.BackupError):
        open_(bytes(data), monkeypatch)
