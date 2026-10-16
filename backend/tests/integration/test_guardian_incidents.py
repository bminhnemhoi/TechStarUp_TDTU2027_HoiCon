"""Kiểm thử tích hợp spec 027 (FR-004, SC-002): API đọc sự cố cho người giám hộ + ma trận cô lập hai gia đình."""

import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, purge_family
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import delete, select

from hoicon.api.auth import GUARDIAN_COOKIE, issue_guardian_access_token
from hoicon.config import get_settings
from hoicon.db.ids import new_id
from hoicon.db.models import AgentRun, Family, Incident, IncidentTransition, Member
from hoicon.db.session import get_sessionmaker

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
RAW_PHONE = re.compile(r"(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}")
OPEN = {"detected", "assessing", "awaiting_guardian", "verifying", "rescore", "case_open"}
CLOSED = {"resolved_safe", "resolved_prevented", "resolved_false_alarm", "resolved_no_response", "closed"}
NOT_FOUND = "Không tìm thấy sự cố"
BASE = datetime(2026, 12, 1, 2, 0, 0, tzinfo=UTC)


def _validator(name: str, fragment: str = "") -> Draft202012Validator:
    docs = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.v1.json")}
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs.values()])
    schema = docs[f"{name}.v1.json"]
    if fragment:
        schema = {"$ref": f"{schema['$id']}#/$defs/{fragment}"}
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


LIST_SCHEMA = _validator("incident_list")
DETAIL_SCHEMA = _validator("incident", "detail")


async def make_family(name: str) -> dict[str, Any]:
    async with get_sessionmaker().begin() as session:
        family = Family(display_name=name, region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        session.add_all([protected, guardian])
        await session.flush()
        return {"family": family.id, "protected": protected.id, "guardian": guardian.id, "incidents": []}


async def add_incident(w: dict[str, Any], state: str, opened_at: datetime, **changes: Any) -> UUID:
    async with get_sessionmaker().begin() as session:
        incident = Incident(
            family_id=w["family"],
            member_id=w["protected"],
            state=state,
            level="high",
            rule_floor="high",
            is_demo=True,
            opened_at=opened_at,
            closed_at=opened_at + timedelta(minutes=5) if state in CLOSED else None,
            **changes,
        )
        session.add(incident)
        await session.flush()
        w["incidents"].append(incident.id)
        return incident.id


@pytest.fixture
async def worlds(
    require_db: None, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[dict[str, Any], dict[str, Any]]]:
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    get_settings.cache_clear()
    a, b = await make_family("Nhà A 027"), await make_family("Nhà B 027")
    yield a, b
    async with get_sessionmaker().begin() as session:
        for w in (a, b):
            await session.execute(delete(AgentRun).where(AgentRun.thread_id.in_([str(i) for i in w["incidents"]])))
    await purge_family(a["family"])
    await purge_family(b["family"])
    get_settings.cache_clear()


def bearer(w: dict[str, Any]) -> str:
    return issue_guardian_access_token(w["guardian"], w["family"])


async def list_page(w: dict[str, Any], **params: Any) -> Any:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return await call("GET", "/v1/guardian/incidents" + (f"?{query}" if query else ""), token=bearer(w))


async def add_run(incident_id: UUID, status: str = "running") -> UUID:
    async with get_sessionmaker().begin() as session:
        run = AgentRun(graph="incident", status=status, thread_id=str(incident_id), is_demo=True)
        session.add(run)
        await session.flush()
        return run.id


async def walk(w: dict[str, Any], **params: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    cursor: str | None = None
    for _ in range(20):
        resp = await list_page(w, **params, **({"cursor": cursor} if cursor else {}))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert [e.message for e in LIST_SCHEMA.iter_errors(body)] == []
        items += body["incidents"]
        cursor = body["next_cursor"]
        if cursor is None:
            return items
    raise AssertionError("phân trang không dừng")


# --- danh sách --------------------------------------------------------------------------------------------------


async def test_list_matches_the_contract_and_carries_alias_and_run_flag(worlds: Any) -> None:
    a, _ = worlds
    with_run = await add_incident(a, "awaiting_guardian", BASE)
    await add_incident(a, "resolved_safe", BASE - timedelta(hours=1), outcome="safe")
    await add_run(with_run)
    resp = await list_page(a)
    assert resp.status_code == 200 and resp.headers["cache-control"] == "no-store"
    body = resp.json()
    assert [e.message for e in LIST_SCHEMA.iter_errors(body)] == []
    by_id = {item["id"]: item for item in body["incidents"]}
    assert by_id[str(with_run)]["has_run"] is True and by_id[str(with_run)]["elder_alias"] == "Mẹ"
    assert [i["has_run"] for i in body["incidents"]].count(False) == 1
    assert all("transitions" not in item for item in body["incidents"])
    assert not RAW_PHONE.search(resp.text)


async def test_open_incidents_come_first_then_closed_newest_first(worlds: Any) -> None:
    a, _ = worlds
    closed_new = await add_incident(a, "resolved_safe", BASE + timedelta(hours=3))
    open_old = await add_incident(a, "assessing", BASE)
    open_new = await add_incident(a, "case_open", BASE + timedelta(hours=1))
    closed_old = await add_incident(a, "closed", BASE - timedelta(hours=1))
    ids = [UUID(i["id"]) for i in await walk(a)]
    assert ids == [open_new, open_old, closed_new, closed_old]


async def test_status_filter_uses_exactly_the_open_and_closed_state_sets(worlds: Any) -> None:
    a, _ = worlds
    for index, state in enumerate(sorted(OPEN | CLOSED)):
        await add_incident(a, state, BASE + timedelta(minutes=index))
    opened = {i["state"] for i in await walk(a, status="open")}
    closed = {i["state"] for i in await walk(a, status="closed")}
    assert opened == OPEN and closed == CLOSED


async def test_pagination_has_no_duplicates_and_no_gaps_even_with_equal_timestamps(worlds: Any) -> None:
    a, _ = worlds
    expected: set[UUID] = set()
    for index in range(33):  # 33 sự cố mở, nhiều cái trùng thời điểm ⇒ khóa phụ theo id
        expected.add(await add_incident(a, "awaiting_guardian", BASE + timedelta(minutes=index // 3)))
    for index in range(14):
        expected.add(await add_incident(a, "resolved_safe", BASE + timedelta(minutes=index // 2)))
    first = (await list_page(a)).json()
    assert len(first["incidents"]) == 20 and first["next_cursor"] is not None
    items = await walk(a)
    ids = [UUID(i["id"]) for i in items]
    assert len(ids) == len(set(ids)) == len(expected) and set(ids) == expected
    groups = [i["state"] in OPEN for i in items]
    assert groups == sorted(groups, reverse=True)  # mọi sự cố mở đứng trước mọi sự cố đã xong
    for status_filter, size in (("open", 33), ("closed", 14)):
        assert len(await walk(a, status=status_filter)) == size


async def test_drill_incidents_are_flagged(worlds: Any) -> None:
    a, _ = worlds
    await add_incident(a, "awaiting_guardian", BASE, is_drill=True, drill_id=new_id())
    [item] = (await list_page(a)).json()["incidents"]
    assert item["is_drill"] is True


@pytest.mark.parametrize("cursor", ["khong-hop-le", "!!!", "QQ", "a" * 200])
async def test_bad_cursor_or_status_is_422_and_not_echoed(worlds: Any, cursor: str) -> None:
    a, _ = worlds
    resp = await list_page(a, cursor=cursor)
    assert resp.status_code == 422 and cursor not in resp.text
    assert (await list_page(a, status="tat-ca")).status_code == 422


# --- chi tiết ---------------------------------------------------------------------------------------------------


async def test_detail_has_transitions_alias_and_run_id(worlds: Any) -> None:
    a, _ = worlds
    incident = await add_incident(a, "awaiting_guardian", BASE)
    async with get_sessionmaker().begin() as session:
        session.add_all(
            [
                IncidentTransition(
                    incident_id=incident,
                    from_state=None,
                    to_state="detected",
                    actor="device",
                    reason="risk_event",
                    at=BASE,
                ),
                IncidentTransition(
                    incident_id=incident,
                    from_state="detected",
                    to_state="awaiting_guardian",
                    actor="agent",
                    reason="alerted",
                    at=BASE + timedelta(seconds=30),
                ),
            ]
        )
    run_id = await add_run(incident)
    resp = await call("GET", f"/v1/guardian/incidents/{incident}", token=bearer(a))
    assert resp.status_code == 200 and resp.headers["cache-control"] == "no-store"
    body = resp.json()
    assert [e.message for e in DETAIL_SCHEMA.iter_errors(body)] == []
    assert body["elder_alias"] == "Mẹ" and body["run_id"] == str(run_id)
    assert [t["to_state"] for t in body["transitions"]] == ["detected", "awaiting_guardian"]
    assert not RAW_PHONE.search(resp.text)


async def test_detail_without_a_run_has_a_null_run_id(worlds: Any) -> None:
    a, _ = worlds
    incident = await add_incident(a, "detected", BASE)
    body = (await call("GET", f"/v1/guardian/incidents/{incident}", token=bearer(a))).json()
    assert body["run_id"] is None


# --- ma trận cô lập: 2 gia đình × mọi route ---------------------------------------------------------------------


async def test_isolation_matrix_other_family_is_always_404_and_nothing_changes(worlds: Any) -> None:
    a, b = worlds
    mine = await add_incident(a, "awaiting_guardian", BASE)
    theirs = await add_incident(b, "awaiting_guardian", BASE)
    my_run, their_run = await add_run(mine, "done"), await add_run(theirs, "done")  # `running`: luồng không kết thúc
    token = bearer(a)
    unknown = UUID(int=12345)
    routes = [
        ("GET", "/v1/guardian/incidents/{inc}", None),
        ("GET", "/v1/incidents/{inc}/run", None),
        ("GET", "/v1/runs/{run}/steps", None),
        ("GET", "/v1/runs/{run}/stream", None),
        ("POST", "/v1/incidents/{inc}/decision", {"decision": "safe"}),
    ]
    for method, template, body in routes:
        own = await call(method, template.format(inc=mine, run=my_run), token=token, json=body)
        assert own.status_code in (200, 409), (method, template, own.text)  # của mình: dùng được
        other = await call(method, template.format(inc=theirs, run=their_run), token=token, json=body)
        ghost = await call(method, template.format(inc=unknown, run=unknown), token=token, json=body)
        assert other.status_code == 404, (method, template, other.text)
        assert ghost.status_code == 404 and other.json() == ghost.json(), template  # không lộ nhà khác có tồn tại
    async with get_sessionmaker()() as session:
        state = await session.scalar(select(Incident.state).where(Incident.id == theirs))
    assert state == "awaiting_guardian"  # quyết định "an toàn" nhắm vào nhà khác không đổi gì
    listing = await walk(a)
    assert {i["id"] for i in listing} == {str(mine)}
    assert str(theirs) not in json.dumps(listing)


async def test_detail_404_is_identical_for_other_family_and_unknown_id(worlds: Any) -> None:
    a, b = worlds
    theirs = await add_incident(b, "awaiting_guardian", BASE)
    other = await call("GET", f"/v1/guardian/incidents/{theirs}", token=bearer(a))
    ghost = await call("GET", f"/v1/guardian/incidents/{UUID(int=99)}", token=bearer(a))
    assert other.status_code == ghost.status_code == 404 and other.json() == ghost.json() == {"detail": NOT_FOUND}


# --- xác thực ---------------------------------------------------------------------------------------------------


async def test_routes_need_a_guardian_session_and_accept_the_cookie(worlds: Any) -> None:
    a, _ = worlds
    incident = await add_incident(a, "detected", BASE)
    for path in ("/v1/guardian/incidents", f"/v1/guardian/incidents/{incident}"):
        assert (await call("GET", path)).status_code == 401
        assert (await call("GET", path, cookies={GUARDIAN_COOKIE: bearer(a)})).status_code == 200


async def test_a_removed_guardian_loses_access_immediately(worlds: Any) -> None:
    a, _ = worlds
    token = bearer(a)
    assert (await call("GET", "/v1/guardian/incidents", token=token)).status_code == 200
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(Member).where(Member.id == a["guardian"]))
    assert (await call("GET", "/v1/guardian/incidents", token=token)).status_code == 401


async def test_device_tokens_cannot_use_the_guardian_routes(worlds: Any) -> None:
    from hoicon.api.auth import issue_access_token

    a, _ = worlds
    device_token = issue_access_token(UUID(int=1), a["family"], a["protected"])
    assert (await call("GET", "/v1/guardian/incidents", token=device_token)).status_code == 401
