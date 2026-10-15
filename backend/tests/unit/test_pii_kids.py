"""`candidate_hmacs`: tra cứu danh sách đe dọa phải thử mọi kid pepper đã cấu hình (xoay pepper, ADR-006)."""

import hashlib
import hmac
from collections.abc import Iterator

import pytest

from hoicon.config import get_settings
from hoicon.domain.pii import candidate_hmacs, hmac_h1

H1 = "aa1b1fcd5c51853e998738c59cffa5a4d95bd39ef7ef3b6d905c9c6c3af987e4"
PEPPER_1, PEPPER_2 = "11" * 32, "22" * 32  # khóa GIẢ chỉ cho test


@pytest.fixture(autouse=True)
def fresh_settings() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_current_kid_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", PEPPER_1)
    assert candidate_hmacs(H1) == [hmac_h1(H1, 1)]


def test_old_kid_is_still_tried_after_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", PEPPER_1)
    monkeypatch.setenv("HOICON_PHONE_PEPPER_2", PEPPER_2)
    monkeypatch.setenv("HOICON_PHONE_PEPPER_KID", "2")
    found = candidate_hmacs(H1)
    assert [kid for kid, _ in found] == [2, 1]  # kid hiện hành đứng đầu
    expected = hmac.new(PEPPER_1.encode(), H1.encode(), hashlib.sha256).hexdigest()
    assert (1, expected) in found
    assert found[0][1] != found[1][1]


def test_no_pepper_configured_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("HOICON_PHONE_PEPPER_1", "HOICON_PHONE_PEPPER_2"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(get_settings(), "phone_pepper_1", None)  # .env của máy (nếu có) không được lọt vào test
    with pytest.raises(RuntimeError, match="PEPPER"):
        candidate_hmacs(H1)


def test_raw_number_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOICON_PHONE_PEPPER_1", PEPPER_1)
    with pytest.raises(ValueError):
        candidate_hmacs("0900000002")
