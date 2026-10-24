"""Spec 025 (FR-006/FR-007/FR-009): `/v1/runs/{id}/steps`, `/v1/runs/{id}/stream`, `/v1/incidents/{id}/run` qua
ASGITransport. ASGITransport gom hết thân phản hồi nên MỌI lượt dùng ở đây đã kết thúc (`done`/`failed`); luồng thật
(bước mới, ping, ngắt đột ngột) ở `test_trace_sse_live.py`."""

from typing import Any

import pytest
from consent_support import call
from sqlalchemy import delete
from trace_support import (
    AT,
    FAKE_PHONE,
    LONG_HEX,
    RAW_PHONE,
    TOKEN43,
    VALIDATORS,
    add_run,
    another_incident,
    auth,
    parse_sse,
    protected_of,
    steps_in_db,
)

from hoicon.api.auth import issue_guardian_access_token
from hoicon.db.ids import new_id
from hoicon.db.models import AgentStep
from hoicon.db.session import get_sessionmaker
from hoicon.services import trace_service

pytestmark = pytest.mark.integration


# --- /steps -----------------------------------------------------------------------------------------------------


async def test_steps_match_the_database_in_order_and_the_schema(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    res = await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))
    assert res.status_code == 200, res.text
    body = res.json()
    VALIDATORS["run_steps"].validate(body)
    rows = await steps_in_db(run_id)
    assert [s["id"] for s in body["steps"]] == [str(r.id) for r in rows]
    assert body["steps"] == [trace_service.step_view(r) for r in rows]
    assert (body["run_id"], body["status"], body["is_drill"], body["is_demo"]) == (str(run_id), "done", False, True)
    assert res.headers["content-type"].startswith("application/json")
    assert res.headers["cache-control"] == "no-store"  # dữ liệu cá nhân: không để proxy/trình duyệt lưu


async def test_steps_with_the_same_timestamp_come_back_in_id_order_without_loss(trace_world: dict[str, Any]) -> None:
    run_id = await add_run(await another_incident(trace_world), trace_world, poisoned=False)
    async with get_sessionmaker().begin() as session:
        await session.execute(delete(AgentStep).where(AgentStep.run_id == run_id))
        for _ in range(5):
            session.add(AgentStep(run_id=run_id, node="ingest", output={}, at=AT, latency_ms=0))
    res = await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))
    ids = [s["id"] for s in res.json()["steps"]]
    assert len(ids) == 5 and ids == sorted(ids)  # UUIDv7 tăng dần, `(at, id)` xác định thứ tự
    from httpx import ASGITransport, AsyncClient

    from hoicon.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app, client=("203.0.113.7", 1)), base_url="http://t") as client:
        resumed = await client.get(
            f"/v1/runs/{run_id}/stream",
            headers={"Authorization": f"Bearer {auth(trace_world)}", "Last-Event-ID": ids[1]},
        )
    assert [f["id"] for f in parse_sse(resumed.text) if f["event"] == "step"] == ids[2:]


# --- SSE của lượt đã kết thúc -----------------------------------------------------------------------------------


async def test_stream_of_a_finished_run_ends_with_done_matching_the_database(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    res = await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/event-stream; charset=utf-8"
    assert res.headers["cache-control"] == "no-cache, no-transform"
    assert res.headers["x-accel-buffering"] == "no"
    assert "connection" not in res.headers  # hop-by-hop: HTTP/2 cấm
    assert res.text.startswith("retry: 3000\n\n")
    frames = parse_sse(res.text)
    assert [f["event"] for f in frames] == ["step"] * 4 + ["done"]
    rows = await steps_in_db(run_id)
    assert [f["id"] for f in frames[:4]] == [str(r.id) for r in rows]
    VALIDATORS["run_done"].validate(frames[-1]["data"])
    assert frames[-1]["data"] == {
        "run_id": str(run_id), "status": "done", "total_steps": 4, "cost_usd": "0.002450", "is_drill": False,
        "is_demo": True,
    }  # fmt: skip
    for frame in frames[:4]:
        VALIDATORS["agent_step"].validate(frame["data"])
    assert trace_service.open_streams() == 0, "chỗ phải được nhả khi luồng kết thúc"


async def test_sse_steps_are_identical_to_the_history_endpoint(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    history = (await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))).json()["steps"]
    streamed = [
        f["data"] for f in parse_sse((await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))).text)
    ]
    assert streamed[:-1] == history


async def test_last_event_id_header_resumes_without_repeating_steps(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    rows = await steps_in_db(run_id)
    from httpx import ASGITransport, AsyncClient

    from hoicon.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app, client=("203.0.113.7", 1)), base_url="http://t") as client:
        res = await client.get(
            f"/v1/runs/{run_id}/stream",
            headers={"Authorization": f"Bearer {auth(trace_world)}", "Last-Event-ID": str(rows[1].id)},
        )
        alien = await client.get(
            f"/v1/runs/{run_id}/stream",
            headers={"Authorization": f"Bearer {auth(trace_world)}", "Last-Event-ID": str(new_id())},
        )
    assert [f["id"] for f in parse_sse(res.text) if f["event"] == "step"] == [str(rows[2].id), str(rows[3].id)]
    assert len([f for f in parse_sse(alien.text) if f["event"] == "step"]) == 4  # id lạ ⇒ phát lại từ đầu
    async with AsyncClient(transport=ASGITransport(app=app, client=("203.0.113.7", 1)), base_url="http://t") as client:
        for junk in ("x" * 500, "khong-phai-uuid", "0"):
            res = await client.get(
                f"/v1/runs/{run_id}/stream",
                headers={"Authorization": f"Bearer {auth(trace_world)}", "Last-Event-ID": junk},
            )
            assert res.status_code == 200, junk  # header rác không làm hỏng luồng: phát lại từ đầu
            assert len([f for f in parse_sse(res.text) if f["event"] == "step"]) == 4, junk


async def test_failed_run_streams_done_with_failed_status(trace_world: dict[str, Any]) -> None:
    run_id = await add_run(await another_incident(trace_world), trace_world, status="failed", poisoned=False)
    frames = parse_sse((await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))).text)
    assert frames[-1]["event"] == "done" and frames[-1]["data"]["status"] == "failed"


# --- SC-002: che PII ---------------------------------------------------------------------------------------------


async def test_poisoned_steps_leak_nothing_on_either_endpoint(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    for path in (f"/v1/runs/{run_id}/steps", f"/v1/runs/{run_id}/stream"):
        text = (await call("GET", path, token=auth(trace_world))).text
        assert not RAW_PHONE.search(text), path
        assert FAKE_PHONE not in text and not LONG_HEX.search(text), path
        assert TOKEN43 not in text and "input_redacted" not in text, path
        for key in ('"h1"', '"phone"', '"note"', '"text"', '"token"', '"package"', '"caller"'):
            assert key not in text, (path, key)
        assert "20.000.000 đồng" in text  # số tiền giữ nguyên
        assert "[SĐT ***123]" in text and "[HASH]" in text and "[TOKEN]" in text


# --- quyền xem ---------------------------------------------------------------------------------------------------


async def test_missing_or_bad_token_is_401(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    for path in (
        f"/v1/runs/{run_id}/steps",
        f"/v1/runs/{run_id}/stream",
        f"/v1/incidents/{trace_world['a']['incident']}/run",
    ):
        assert (await call("GET", path)).status_code == 401, path
        assert (await call("GET", path, token="khong-phai-jwt")).status_code == 401, path
        # token qua query string KHÔNG được chấp nhận (Caddy ghi log URL)
        assert (await call("GET", f"{path}?access_token={auth(trace_world)}")).status_code == 401, path


async def test_other_family_unknown_and_eval_runs_are_404(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    eval_run = await add_run(f"eval-{new_id().hex[:8]}-case", trace_world, poisoned=False)
    ghost = await add_run(new_id(), trace_world, poisoned=False)  # thread_id là UUID của sự cố KHÔNG tồn tại
    for tag, target in (("b", run_id), ("a", eval_run), ("a", ghost), ("a", new_id())):
        for suffix in ("steps", "stream"):
            res = await call("GET", f"/v1/runs/{target}/{suffix}", token=auth(trace_world, tag))
            assert res.status_code == 404, (tag, target, suffix)
            assert str(target) not in res.text, "không lặp lại id đã hỏi"
    assert (await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world, "b"))).json() == (
        await call("GET", f"/v1/runs/{new_id()}/steps", token=auth(trace_world, "b"))
    ).json(), "nhà khác và id lạ phải không phân biệt được"


async def test_a_protected_member_token_cannot_read_a_run(trace_world: dict[str, Any]) -> None:
    protected = await protected_of(trace_world, "a")
    token = issue_guardian_access_token(protected, trace_world["a"]["family"])
    assert (await call("GET", f"/v1/runs/{trace_world['a']['run']}/steps", token=token)).status_code == 401


# --- giới hạn luồng -----------------------------------------------------------------------------------------------


async def test_fourth_stream_of_one_member_is_429_and_overall_cap_is_503(trace_world: dict[str, Any]) -> None:
    run_id = trace_world["a"]["run"]
    guardian = trace_world["a"]["guardian"]
    held = [trace_service.acquire_slot(guardian) for _ in range(trace_service.MAX_STREAMS_PER_MEMBER)]
    res = await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))
    assert res.status_code == 429 and int(res.headers["retry-after"]) > 0
    assert (await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))).status_code == 200, (
        "/steps không bị đếm"
    )
    for slot in held:
        slot.release()
    held = [trace_service.acquire_slot(new_id()) for _ in range(trace_service.MAX_STREAMS)]
    busy = await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))
    assert busy.status_code == 503 and busy.headers["retry-after"] == "5"
    for slot in held:
        slot.release()
    assert (await call("GET", f"/v1/runs/{run_id}/stream", token=auth(trace_world))).status_code == 200
    assert trace_service.open_streams() == 0


async def test_404_is_returned_before_a_slot_is_taken(trace_world: dict[str, Any]) -> None:
    await call("GET", f"/v1/runs/{new_id()}/stream", token=auth(trace_world))
    assert trace_service.open_streams() == 0


# --- /v1/incidents/{id}/run --------------------------------------------------------------------------------------


async def test_incident_run_lookup(trace_world: dict[str, Any]) -> None:
    incident = trace_world["a"]["incident"]
    res = await call("GET", f"/v1/incidents/{incident}/run", token=auth(trace_world))
    assert res.status_code == 200 and res.json() == {"run_id": str(trace_world["a"]["run"]), "status": "done"}
    assert (await call("GET", f"/v1/incidents/{incident}/run", token=auth(trace_world, "b"))).status_code == 404
    assert (await call("GET", f"/v1/incidents/{new_id()}/run", token=auth(trace_world))).status_code == 404
    no_run = trace_world["b"]["incident"]  # sự cố nhà b chưa có lượt nào
    assert (await call("GET", f"/v1/incidents/{no_run}/run", token=auth(trace_world, "b"))).status_code == 404


# --- OpenAPI -----------------------------------------------------------------------------------------------------


async def test_openapi_declares_the_event_stream() -> None:
    from hoicon.api.main import app

    spec = app.openapi()
    stream = spec["paths"]["/v1/runs/{run_id}/stream"]["get"]["responses"]["200"]["content"]
    assert "text/event-stream" in stream
    assert "/v1/runs/{run_id}/steps" in spec["paths"] and "/v1/incidents/{incident_id}/run" in spec["paths"]


async def test_family_cap_applies_across_guardians_of_the_same_family(trace_world: dict[str, Any]) -> None:
    family = trace_world["a"]["family"]
    held = [trace_service.acquire_slot(new_id(), family) for _ in range(trace_service.MAX_STREAMS_PER_FAMILY)]
    res = await call("GET", f"/v1/runs/{trace_world['a']['run']}/stream", token=auth(trace_world))
    assert res.status_code == 429 and int(res.headers["retry-after"]) > 0 and "Gia đình" in res.json()["detail"]
    for slot in held:
        slot.release()
    assert (await call("GET", f"/v1/runs/{trace_world['a']['run']}/stream", token=auth(trace_world))).status_code == 200


async def test_steps_carry_is_sim_true_only_for_a_sim_device_incident(trace_world: dict[str, Any]) -> None:
    """Spec 033 FR-015: `is_sim` luôn có mặt; true khi sự cố gắn thiết bị nhãn `sim:`."""
    import secrets

    from sqlalchemy import update

    from hoicon.db.models import Device, Incident

    run_id = trace_world["a"]["run"]
    res = await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))
    assert res.status_code == 200 and res.json()["is_sim"] is False
    VALIDATORS["run_steps"].validate(res.json())
    incident_id = trace_world["a"]["incident"]
    async with get_sessionmaker().begin() as session:
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        device = Device(
            family_id=incident.family_id, member_id=incident.member_id, platform="web", label="sim:fake_police_001",
            app_version="sim-1", rules_version="sim-1", device_secret_hash=secrets.token_hex(32),
        )  # fmt: skip
        session.add(device)
        await session.flush()
        await session.execute(update(Incident).where(Incident.id == incident_id).values(device_id=device.id))
    res = await call("GET", f"/v1/runs/{run_id}/steps", token=auth(trace_world))
    assert res.json()["is_sim"] is True
    VALIDATORS["run_steps"].validate(res.json())
