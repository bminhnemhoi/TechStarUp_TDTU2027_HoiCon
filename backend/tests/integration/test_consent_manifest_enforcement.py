"""Spec 037 FR-001 / SC-001: ở chế độ nghiêm (`HOICON_CONSENT_STRICT`, mặc định bật ngoài dev)
`POST /v1/consents` chỉ nhận (purpose, version, sha256) thuộc `docs/legal/consent/manifest.json`
ở trạng thái `approved` hoặc đã `released`."""

from typing import Any

import pytest
from consent_support import call, pair_device
from sqlalchemy import func, select

from hoicon.api.routers import consents as consents_router
from hoicon.config import get_settings
from hoicon.db.models import Consent
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

GOOD_SHA = "a" * 64
OTHER_SHA = "b" * 64


def manifest(*, approved: bool = False, released: bool = False) -> dict[str, Any]:
    return {
        "released": [{"purpose": "core_protection", "version": "2026.10-v3", "sha256": GOOD_SHA}] if released else [],
        "purposes": [
            {
                "purpose": "core_protection",
                "version": "2026.10-v3",
                "sha256": GOOD_SHA,
                "status": "approved" if approved else "draft",
            }
        ],
    }


@pytest.fixture
def strict(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Bật chế độ nghiêm + manifest giả cho từng test (`set_manifest`)."""
    monkeypatch.setenv("HOICON_CONSENT_STRICT", "true")
    get_settings.cache_clear()

    def set_manifest(value: Any) -> None:
        def load() -> dict[str, Any]:
            if isinstance(value, Exception):
                raise value
            return value

        monkeypatch.setattr(consents_router, "load_manifest", load)

    yield set_manifest
    get_settings.cache_clear()


async def count(family_id: Any) -> int:
    async with get_sessionmaker()() as session:
        return int(
            await session.scalar(select(func.count()).select_from(Consent).where(Consent.family_id == family_id)) or 0
        )


def entry(**changes: Any) -> dict[str, Any]:
    return {
        "purpose": "core_protection",
        "granted": True,
        "consent_version": "2026.10-v3",
        "text_sha256": GOOD_SHA,
        "channel": "app",
        **changes,
    }


async def send(device_world: Any, **changes: Any) -> Any:
    paired = await pair_device(device_world.code, consent=False)
    return await call("POST", "/v1/consents", token=paired["access_token"], json={"items": [entry(**changes)]})


async def test_a_text_outside_the_manifest_is_refused_and_nothing_is_written(device_world: Any, strict: Any) -> None:
    strict(manifest(approved=True))
    resp = await send(device_world, text_sha256=OTHER_SHA)
    assert resp.status_code == 422
    assert await count(device_world.family_id) == 0
    assert GOOD_SHA not in resp.text  # không nêu sha mong đợi


async def test_an_unknown_version_is_refused(device_world: Any, strict: Any) -> None:
    strict(manifest(approved=True))
    assert (await send(device_world, consent_version="v9.9")).status_code == 422


async def test_an_approved_text_is_accepted(device_world: Any, strict: Any) -> None:
    strict(manifest(approved=True))
    assert (await send(device_world)).status_code == 200
    assert await count(device_world.family_id) == 1


async def test_a_released_text_is_accepted_even_if_no_longer_approved(device_world: Any, strict: Any) -> None:
    strict(manifest(released=True))
    assert (await send(device_world)).status_code == 200


async def test_a_draft_text_is_refused_in_strict_mode(device_world: Any, strict: Any) -> None:
    strict(manifest())
    resp = await send(device_world)
    assert resp.status_code == 422 and await count(device_world.family_id) == 0


async def test_an_unreadable_manifest_fails_closed(device_world: Any, strict: Any) -> None:
    strict(FileNotFoundError("manifest"))
    resp = await send(device_world)
    assert resp.status_code == 503 and await count(device_world.family_id) == 0


async def test_without_strict_mode_every_well_formed_record_is_accepted_as_before(device_world: Any) -> None:
    get_settings.cache_clear()
    assert get_settings().consent_strict_on is False  # môi trường test là dev
    assert (await send(device_world, text_sha256=OTHER_SHA, consent_version="v1.0")).status_code == 200


def test_strict_defaults_to_on_outside_dev_and_can_be_overridden(monkeypatch: pytest.MonkeyPatch) -> None:
    for env, flag, expected in [
        ("prod", None, True),
        ("dev", None, False),
        ("prod", "false", False),
        ("dev", "true", True),
    ]:
        monkeypatch.setenv("HOICON_ENV", env)
        monkeypatch.delenv("HOICON_CONSENT_STRICT", raising=False)
        if flag is not None:
            monkeypatch.setenv("HOICON_CONSENT_STRICT", flag)
        get_settings.cache_clear()
        assert get_settings().consent_strict_on is expected, (env, flag)
    get_settings.cache_clear()


async def test_a_withdrawal_is_always_recorded_even_when_the_text_is_unknown_or_the_manifest_unreadable(
    device_world: Any, strict: Any
) -> None:
    """Quyền rút không phụ thuộc manifest hay phiên bản app (reviewer 037 #1)."""
    token = (await pair_device(device_world.code, consent=False))["access_token"]

    async def post(**changes: Any) -> Any:
        return await call("POST", "/v1/consents", token=token, json={"items": [entry(**changes)]})

    strict(manifest())  # bản nháp: mọi lệnh CẤP đều bị từ chối
    assert (await post(text_sha256=OTHER_SHA, granted=False)).status_code == 200
    strict(FileNotFoundError("manifest"))
    assert (await post(granted=False)).status_code == 200
    assert await count(device_world.family_id) == 2
    assert (await post()).status_code == 503  # lệnh cấp vẫn đóng
