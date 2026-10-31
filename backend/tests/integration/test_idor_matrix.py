"""Spec 037 FR-004 / SC-003: ma trận IDOR. Mỗi route có id/token của tài nguyên được thử với (a) tài nguyên của
GIA ĐÌNH KHÁC, (b) token sai audience, (c) token của gia đình đã bị xóa.

Tính chất chính: với cùng một token, tài nguyên "của nhà khác" và tài nguyên "không tồn tại" cho CÙNG mã trạng thái
và CÙNG thân (không lộ sự tồn tại). Bảng `CELLS` là nguồn duy nhất;
`test_every_route_with_an_id_is_in_the_matrix_or_exempt`
đọc OpenAPI nên route mới có id mà chưa vào bảng (hay danh sách miễn có lý do) sẽ làm
test đỏ."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from case_support import seed_case
from consent_support import call, purge_family

from hoicon.api.auth import issue_access_token, issue_guardian_access_token
from hoicon.api.main import app
from hoicon.config import get_settings
from hoicon.db.session import get_sessionmaker
from hoicon.services import consent_gate

pytestmark = pytest.mark.integration

ORIGIN = {"Origin": "http://localhost:3100"}  # dev: nguồn web được phép (chỉ cần với lệnh ghi bằng cookie)


@dataclass(frozen=True)
class Cell:
    method: str
    template: str  # có {incident} {run} {family} {drill}
    audience: str  # "guardian" | "device"
    body: dict[str, Any] | None = None


CELLS = [
    Cell("GET", "/v1/guardian/incidents/{incident}", "guardian"),
    Cell("GET", "/v1/guardian/incidents/{incident}/case-file", "guardian"),
    Cell("POST", "/v1/guardian/incidents/{incident}/case-file", "guardian", {"action": "approve"}),
    Cell("GET", "/v1/incidents/{incident}", "device"),
    Cell("GET", "/v1/families/{family}/incidents", "device"),
    Cell("POST", "/v1/incidents/{incident}/decision", "guardian", {"decision": "safe"}),
    Cell("POST", "/v1/incidents/{incident}/answers", "device", {"question_id": "q_asked_transfer", "answer": "no"}),
    Cell("GET", "/v1/incidents/{incident}/pending-question", "device"),
    Cell("GET", "/v1/incidents/{incident}/run", "guardian"),
    Cell("GET", "/v1/runs/{run}/steps", "guardian"),
    Cell("POST", "/v1/drills/{drill}/result", "device", {"drill_id": "d-1", "status": "declined", "answers": []}),
]

# Route có id/token trong đường dẫn nhưng KHÔNG nằm trong ma trận, kèm lý do (đổi sang ma trận khi có thể).
EXEMPT = {
    (
        "GET",
        "/v1/action/{token}",
    ): "liên kết dùng một lần: token chính là bằng chứng; có test riêng (test_withdrawn_links, 023)",
    ("POST", "/v1/action/{token}/decision"): "như trên",
    ("GET", "/v1/runs/{run_id}/stream"): "SSE; kiểm ở test_api_runs / test_guardian_consent_gate",
    ("GET", "/v1/sim/runs/{incident_id}"): "cổng HOICON_SIM_ENABLED + chỉ gia đình demo; ma trận riêng ở test_api_sim",
    ("POST", "/v1/sim/runs/{incident_id}/answer"): "như trên",
    (
        "DELETE",
        "/v1/data-requests/{request_id}",
    ): "yêu cầu xóa, không phải sự cố: IDOR (nhà khác/id lạ ⇒ cùng 404, 401, 409) ở test_api_data_requests (038)",
    ("POST", "/webhooks/zalo/{bot_id}"): "xác thực bằng bí mật webhook, không theo gia đình",
}


@pytest.fixture
async def worlds(
    require_db: None, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple[SimpleNamespace, SimpleNamespace]]:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", "integration-test-key-" + "k" * 32)  # gitleaks:allow — khóa GIẢ
    get_settings.cache_clear()
    consent_gate.reset_cache()
    a = await seed_case(state="awaiting_guardian")
    b = await seed_case(state="awaiting_guardian")
    yield a, b
    await purge_family(a.family)
    await purge_family(b.family)
    get_settings.cache_clear()


async def device_of(w: SimpleNamespace) -> Any:
    from sqlalchemy import select

    from hoicon.db.models import Device

    async with get_sessionmaker()() as session:
        return await session.scalar(select(Device.id).where(Device.family_id == w.family))


async def token(w: SimpleNamespace, audience: str) -> str:
    if audience == "guardian":
        return issue_guardian_access_token(w.guardian, w.family)
    return issue_access_token(await device_of(w), w.family, w.protected)


def path_for(cell: Cell, w: SimpleNamespace | None) -> str:
    """Đường dẫn với tài nguyên của `w`; `None` ⇒ id ngẫu nhiên (không tồn tại)."""
    ids = {
        "incident": w.incident if w else uuid4(),
        "run": w.run if w else uuid4(),
        "family": w.family if w else uuid4(),
        "drill": uuid4(),  # không có bài diễn tập của nhà nào: luôn "không có"
    }
    return cell.template.format(**ids)


async def hit(cell: Cell, path: str, tok: str) -> tuple[int, Any]:
    body = cell.body
    if body is not None and "drill_id" in body:  # thân phải khớp id trong đường dẫn: /v1/drills/<id>/result
        body = {**body, "drill_id": path.split("/")[3]}
    resp = await call(cell.method, path, token=tok, json=body, headers=ORIGIN)
    try:
        payload: Any = resp.json()
    except ValueError:
        payload = resp.text
    return resp.status_code, payload


@pytest.mark.parametrize("cell", CELLS, ids=lambda c: f"{c.method} {c.template}")
async def test_a_foreign_resource_looks_exactly_like_a_missing_one(
    worlds: tuple[SimpleNamespace, SimpleNamespace], cell: Cell
) -> None:
    a, b = worlds
    tok = await token(b, cell.audience)  # người của nhà B hỏi về tài nguyên của nhà A
    foreign = await hit(cell, path_for(cell, a), tok)
    missing = await hit(cell, path_for(cell, None), tok)
    assert foreign[0] in (403, 404), foreign
    assert foreign == missing, "phản hồi cho tài nguyên nhà khác khác với tài nguyên không tồn tại"


@pytest.mark.parametrize("cell", CELLS, ids=lambda c: f"{c.method} {c.template}")
async def test_a_token_of_the_wrong_audience_is_refused(
    worlds: tuple[SimpleNamespace, SimpleNamespace], cell: Cell
) -> None:
    a, _ = worlds
    wrong = "device" if cell.audience == "guardian" else "guardian"
    status, _ = await hit(cell, path_for(cell, a), await token(a, wrong))
    assert status == 401


@pytest.mark.parametrize("cell", CELLS, ids=lambda c: f"{c.method} {c.template}")
async def test_a_token_of_a_deleted_family_is_refused(
    worlds: tuple[SimpleNamespace, SimpleNamespace], cell: Cell
) -> None:
    a, _ = worlds
    tok = await token(a, cell.audience)
    path = path_for(cell, a)
    await purge_family(a.family)
    status, _ = await hit(cell, path, tok)
    assert status == 401


def test_every_route_with_an_id_is_in_the_matrix_or_exempt() -> None:
    covered = {
        (
            c.method,
            c.template.replace("{incident}", "{incident_id}")
            .replace("{family}", "{family_id}")
            .replace("{run}", "{run_id}")
            .replace("{drill}", "{drill_id}"),
        )
        for c in CELLS
    }
    missing: list[str] = []
    for path, ops in app.openapi()["paths"].items():
        if "{" not in path:
            continue
        for method in ops:
            key = (method.upper(), path)
            if key not in covered and key not in EXEMPT:
                missing.append(f"{key[0]} {key[1]}")
    assert missing == [], f"route có id/token chưa vào ma trận IDOR hay danh sách miễn: {missing}"


def test_the_exemptions_are_real_routes_with_a_reason() -> None:
    paths = {(m.upper(), p) for p, ops in app.openapi()["paths"].items() for m in ops}
    assert set(EXEMPT) <= paths
    assert all(EXEMPT.values())
