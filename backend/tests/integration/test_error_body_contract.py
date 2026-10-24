"""Spec 037 T013: thân 403 `consent_withdrawn` của `POST /v1/events` phải khớp `docs/schemas/error.v1.json`.

XFAIL CÓ CHỦ ĐÍCH (strict): thân thật là `{"detail": "consent_withdrawn"}` (FastAPI `HTTPException`; Android
`OutboxSender`/`PairingApiClient` đọc đúng dạng này, test của nó ghim ba biến thể), còn lược đồ là
`{"error": ..., "purpose": ...}` với `additionalProperties: false`. Chọn một: (a) sửa lược đồ cho khớp thân thật
(docs/schemas — ngoài quyền làn B), hoặc (b) đổi thân thật (đụng app Android đã phát hành). Khi một trong hai làm xong,
test này XPASS ⇒ strict làm đỏ ⇒ gỡ dấu xfail."""

import json
from pathlib import Path
from typing import Any

import pytest
from consent_support import pair_device
from jsonschema import Draft202012Validator
from test_api_events import make_event, post

pytestmark = pytest.mark.integration

SCHEMA = json.loads((Path(__file__).resolve().parents[3] / "docs" / "schemas" / "error.v1.json").read_text("utf-8"))


@pytest.mark.xfail(
    strict=True, reason="037 T013: thân 403 thật {'detail': ...} lệch lược đồ error.v1 — cần quyết định hợp đồng"
)
async def test_the_403_body_of_events_matches_error_schema(device_world: Any) -> None:
    paired = await pair_device(device_world.code, consent=False)  # chưa có đồng ý nào ⇒ 403 consent_withdrawn
    resp = await post(paired["access_token"], make_event())
    assert resp.status_code == 403
    Draft202012Validator(SCHEMA).validate(resp.json())
