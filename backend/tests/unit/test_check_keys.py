"""check_keys không bao giờ in giá trị khóa (CLAUDE.md luật 9) và phân loại đúng Thiếu/Đạt/Lỗi."""

import http.client

import pytest
from pydantic import SecretStr

from hoicon.config import Settings
from hoicon.ops import check_keys

FAKE = "sk-test-DO-NOT-PRINT-0123456789abcdef"
FAKE_PEPPER = "ab" * 32


def _settings(**overrides: str) -> Settings:
    base: dict[str, SecretStr | None] = {
        "anthropic_api_key": None,
        "gemini_api_key": None,
        "zalo_bot_token": None,
        "zalo_webhook_secret": None,
        "phone_pepper_1": None,
    }
    base.update({k: SecretStr(v) for k, v in overrides.items()})
    return Settings(_env_file=None, **base)


def _no_network(*_a: object, **_k: object) -> None:
    pytest.fail("không được gọi mạng")


def _all(value: str) -> Settings:
    return _settings(
        anthropic_api_key=value,
        gemini_api_key=value,
        zalo_bot_token=value,
        zalo_webhook_secret=value,
        phone_pepper_1=value,
    )


def _assert_not_printed(capsys: pytest.CaptureFixture[str], *secrets: str) -> str:
    out = capsys.readouterr()
    for s in secrets:
        assert s.strip() not in out.out + out.err
    return out.out


def test_missing_keys_reported_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_keys, "_get", _no_network)
    results = dict(check_keys.run(_settings()))
    assert results["Anthropic API"] == "Thiếu"
    assert results["Zalo Bot token"] == "Thiếu"


def test_http_error_never_prints_secret(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(check_keys, "_get", lambda url, headers: (401, {}))
    monkeypatch.setattr(check_keys, "get_settings", lambda: _all(FAKE))
    assert check_keys.main() == 1
    assert "Lỗi HTTP 401" in _assert_not_printed(capsys, FAKE)


@pytest.mark.parametrize("bad", ["123:FAKE abc-token", "sk-FAKE-KEY-999\nabc", "sk-FAKE\tkey", "sk-FAKĖ-key"])
def test_malformed_secret_blocked_before_network(
    bad: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """PoC của review: khoảng trắng/xuống dòng làm urllib ném InvalidURL/ValueError chứa nguyên khóa."""
    monkeypatch.setattr(check_keys, "_get", _no_network)
    monkeypatch.setattr(check_keys, "get_settings", lambda: _all(bad))
    assert check_keys.main() == 1
    assert "dán lại" in _assert_not_printed(capsys, bad, *bad.split())


def test_unexpected_exception_prints_only_class_name(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(url: str, headers: dict[str, str]) -> None:
        raise http.client.InvalidURL(f"URL can't contain control characters. {url!r} {headers!r}")

    monkeypatch.setattr(check_keys, "_get", boom)
    monkeypatch.setattr(check_keys, "get_settings", lambda: _settings(anthropic_api_key=FAKE, zalo_bot_token=FAKE))
    check_keys.main()
    assert "Lỗi (InvalidURL)" in _assert_not_printed(capsys, FAKE)


def test_length_and_format_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_keys, "_get", _no_network)
    results = dict(check_keys.run(_settings(zalo_webhook_secret="short", phone_pepper_1=FAKE_PEPPER)))
    assert results["Zalo webhook secret (8–256)"].startswith("Lỗi")
    assert results["Pepper băm số điện thoại"] == "Đạt"
    assert dict(check_keys.run(_settings(phone_pepper_1="x" * 64)))["Pepper băm số điện thoại"].startswith("Lỗi")
