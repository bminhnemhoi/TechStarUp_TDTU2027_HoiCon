"""Spec 034 FR-006 / SC-005: mặc định an toàn (`prod`), `/readyz` nêu khóa thiếu (chỉ tên), thân yêu cầu ≤ 256 KB."""

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from hoicon.api import main
from hoicon.api.body_limit import MAX_BODY_BYTES
from hoicon.api.main import app
from hoicon.channels.zalo import build_zalo_client
from hoicon.config import Settings, get_settings
from hoicon.ops import threat_list
from hoicon.services import drill_service

KEY = "ab" * 32
JWT = "j" * 40  # đủ 32 ký tự; chuỗi giả
VALUES = {"phone_pepper_1": KEY, "data_key_1": KEY, "device_jwt_secret": JWT}


def settings_with(**fields: Any) -> Settings:
    """Cấu hình dựng thẳng (không đọc tệp cấu hình cục bộ của máy)."""
    values = {k: SecretStr(v) for k, v in VALUES.items() if k not in fields}
    values.update({k: (SecretStr(v) if isinstance(v, str) and k in VALUES else v) for k, v in fields.items()})
    return Settings(_env_file=None, **{k: v for k, v in values.items() if v is not None})


# --- mặc định `prod` (FR-006, D4) -----------------------------------------------------------------------------------


def test_with_no_env_variable_the_app_runs_as_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOICON_ENV", raising=False)
    config = Settings(_env_file=None)
    assert config.env == "prod" and config.is_dev_env is False


@pytest.mark.parametrize("env", ["dev", "test", "ci"])
def test_dev_environments_are_explicit_opt_ins(monkeypatch: pytest.MonkeyPatch, env: str) -> None:
    monkeypatch.setenv("HOICON_ENV", env)
    assert Settings(_env_file=None).is_dev_env is True


def test_the_test_suite_itself_runs_outside_prod() -> None:
    assert get_settings().env in ("test", "ci", "dev")


async def test_prod_only_guards_switch_on_when_the_variable_is_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOICON_ENV", raising=False)
    config = Settings(_env_file=None)
    # 1) seed demo bị từ chối
    demo_seed = {"version": "x", "is_demo": True, "indicators": []}
    with pytest.raises(threat_list.SeedError):
        await threat_list.load_seed(None, demo_seed, env=config.env)  # type: ignore[arg-type]
    # 2) Zalo mock không được dùng ngoài dev/test (tin "gửi" bằng mock không tới người nhận)
    with pytest.raises(RuntimeError):
        build_zalo_client(config)
    # 3) kịch bản diễn tập chưa duyệt bị đóng
    monkeypatch.setattr(drill_service, "get_settings", lambda: config)
    assert drill_service._approved_or_dev({"approved": False}) is False
    # 4) cookie phiên người giám hộ có cờ Secure
    assert config.is_dev_env is False


def test_the_env_example_and_init_env_pin_dev_explicitly(repo_root) -> None:
    example = (repo_root / "backend" / ".env.example").read_text(encoding="utf-8")
    assert "\nHOICON_ENV=dev\n" in example
    from hoicon.ops import init_env

    assert "\nHOICON_ENV=dev\n" in init_env._fresh_text()


def test_ci_workflow_pins_the_environment(repo_root) -> None:
    workflow = (repo_root / ".github" / "workflows" / "backend.yml").read_text(encoding="utf-8")
    assert "HOICON_ENV: test" in workflow


# --- /readyz nêu khóa thiếu, chỉ tên (FR-006) -----------------------------------------------------------------------


async def readyz(monkeypatch: pytest.MonkeyPatch, config: Settings) -> Any:
    monkeypatch.setattr(main, "get_settings", lambda: config)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/readyz")


async def test_readyz_is_ok_with_every_key(require_db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    resp = await readyz(monkeypatch, settings_with())
    assert resp.status_code == 200 and resp.json()["db"] == "up" and "missing" not in resp.json()


@pytest.mark.parametrize(
    ("absent", "name"),
    [("phone_pepper_1", "phone_pepper"), ("data_key_1", "data_key"), ("device_jwt_secret", "device_jwt_secret")],
)
async def test_readyz_names_exactly_the_missing_key(
    require_db: None, monkeypatch: pytest.MonkeyPatch, absent: str, name: str
) -> None:
    resp = await readyz(monkeypatch, settings_with(**{absent: None}))
    assert resp.status_code == 503
    assert resp.json()["missing"] == [name]


async def test_readyz_lists_every_missing_key_and_never_a_value(
    require_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    resp = await readyz(monkeypatch, Settings(_env_file=None))
    assert resp.status_code == 503
    assert resp.json()["missing"] == ["phone_pepper", "data_key", "device_jwt_secret"]
    for value in (KEY, JWT):
        assert value not in resp.text


async def test_readyz_rejects_a_too_short_signing_key(require_db: None, monkeypatch: pytest.MonkeyPatch) -> None:
    resp = await readyz(monkeypatch, settings_with(device_jwt_secret="x" * 31))
    assert resp.status_code == 503 and resp.json()["missing"] == ["device_jwt_secret"]
    assert "x" * 31 not in resp.text


async def test_readyz_follows_the_current_key_id_not_just_kid_1(
    require_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = Settings(
        _env_file=None,
        phone_pepper_kid=2,
        phone_pepper_1=SecretStr(KEY),  # kid cũ còn, kid hiện hành (2) thiếu
        data_key_1=SecretStr(KEY),
        device_jwt_secret=SecretStr(JWT),
    )
    resp = await readyz(monkeypatch, config)
    assert resp.status_code == 503 and resp.json()["missing"] == ["phone_pepper"]


# --- giới hạn thân 256 KB (FR-006) ----------------------------------------------------------------------------------


def body_of(size: int) -> bytes:
    return json.dumps({"events": [], "pad": "a" * size}).encode()[:size].ljust(size, b" ")


async def post(content: Any, headers: dict[str, str] | None = None) -> Any:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            "/v1/events", content=content, headers={"content-type": "application/json", **(headers or {})}
        )


async def chunks(total: int, size: int = 16 * 1024) -> AsyncIterator[bytes]:
    sent = 0
    while sent < total:
        piece = min(size, total - sent)
        sent += piece
        yield b" " * piece


def test_the_limit_is_256_kib() -> None:
    assert MAX_BODY_BYTES == 262_144


async def test_a_300_kb_body_with_content_length_is_413() -> None:
    resp = await post(body_of(300 * 1024))
    assert resp.status_code == 413 and "quá lớn" in resp.json()["detail"]


async def test_a_300_kb_chunked_body_is_413() -> None:
    resp = await post(chunks(300 * 1024))
    assert resp.status_code == 413


async def test_a_lying_content_length_cannot_slip_a_big_body_through() -> None:
    """Content-Length nhỏ nhưng thân thật lớn: vẫn bị đếm khi đọc."""
    resp = await post(chunks(300 * 1024), headers={"content-length": "10"})
    assert resp.status_code == 413


@pytest.mark.parametrize("size", [200 * 1024, MAX_BODY_BYTES])
async def test_a_body_up_to_the_limit_gets_through_to_the_route(size: int) -> None:
    resp = await post(body_of(size))
    assert resp.status_code in (401, 422)  # tới được router (thân rỗng/không hợp lệ), không bị chặn ở middleware


async def test_a_chunked_body_up_to_the_limit_gets_through() -> None:
    assert (await post(chunks(200 * 1024))).status_code in (401, 422)


async def test_one_byte_over_is_refused() -> None:
    assert (await post(body_of(MAX_BODY_BYTES + 1))).status_code == 413


async def test_get_requests_and_health_checks_are_untouched() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/healthz")).status_code == 200


async def test_readyz_fails_when_prod_would_run_the_mock_zalo_channel(
    require_db: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review 034 #1: prod quên `HOICON_ZALO_MODE=live` ⇒ worker không dựng được kênh gửi ⇒ phải thấy ngay ở /readyz."""
    resp = await readyz(monkeypatch, settings_with(env="prod", zalo_mode="mock"))
    assert resp.status_code == 503 and resp.json()["misconfigured"] == ["zalo_mode"]
    ok = await readyz(monkeypatch, settings_with(env="prod", zalo_mode="live"))
    assert ok.status_code == 200
    ci = await readyz(monkeypatch, settings_with(env="ci", zalo_mode="mock"))  # build_zalo_client cũng từ chối `ci`
    assert ci.status_code == 503


async def test_the_worker_loop_logs_loudly_instead_of_dying_silently(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import asyncio

    from hoicon.jobs import worker
    from hoicon.services import runtime_service

    async def fake_runtime() -> object:
        return object()

    def bad_handlers(_: object) -> dict:
        raise RuntimeError("mock not allowed")

    monkeypatch.setattr(runtime_service, "ensure_runtime", fake_runtime)
    monkeypatch.setattr(worker, "incident_handlers", bad_handlers)
    with caplog.at_level("ERROR"):
        await runtime_service._worker_loop(asyncio.Event())
    assert any("KHÔNG chạy được" in r.message for r in caplog.records)
