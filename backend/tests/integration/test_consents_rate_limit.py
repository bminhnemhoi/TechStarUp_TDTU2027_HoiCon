"""Spec 037 FR-005: `POST /v1/consents` có giới hạn tần suất theo thiết bị (429 + Retry-After),
không ảnh hưởng thiết bị khác."""

from typing import Any

import pytest
from consent_support import call, item, pair_device

from hoicon.api.routers import consents

pytestmark = pytest.mark.integration


async def test_the_device_is_slowed_down_after_the_window_limit(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)
    token = paired["access_token"]
    for _ in range(consents.MAX_PER_WINDOW):
        assert (await call("POST", "/v1/consents", token=token, json={"items": [item()]})).status_code == 200
    resp = await call("POST", "/v1/consents", token=token, json={"items": [item()]})
    assert resp.status_code == 429
    assert 1 <= int(resp.headers["Retry-After"]) <= consents.WINDOW_S


async def test_another_device_is_not_affected(device_world: Any) -> None:
    first = await pair_device(device_world.code, consent=False)
    for _ in range(consents.MAX_PER_WINDOW + 1):
        await call("POST", "/v1/consents", token=first["access_token"], json={"items": [item()]})
    from hoicon.db.session import get_sessionmaker
    from hoicon.ops.pairing_code import create_pairing_code

    code = await create_pairing_code(get_sessionmaker(), device_world.family_id)
    second = await pair_device(code, consent=False)
    assert (
        await call("POST", "/v1/consents", token=second["access_token"], json={"items": [item()]})
    ).status_code == 200


def test_the_limiter_forgets_old_calls_and_is_bounded() -> None:
    from uuid import uuid4

    consents.reset_limits()
    device = uuid4()
    for _ in range(consents.MAX_PER_WINDOW):
        assert consents._retry_after(device, 1000.0) is None
    assert consents._retry_after(device, 1000.0) is not None
    assert consents._retry_after(device, 1000.0 + consents.WINDOW_S) is None  # cửa sổ đã trượt qua
    for _ in range(consents.MAX_TRACKED_DEVICES + 10):
        consents._retry_after(uuid4(), 2000.0)
    assert len(consents._calls) <= consents.MAX_TRACKED_DEVICES
    consents.reset_limits()
