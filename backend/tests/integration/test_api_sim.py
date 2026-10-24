"""Spec 033 (FR-002…FR-008): `/v1/sim/*` — cổng, chỉ gia đình demo, Zalo thật không bao giờ được gọi, kịch bản, một lượt
phát lại đi cùng đường với eval, hạn mức. Gọi qua ASGITransport (không worker nền)."""

import json
import secrets
import time
from collections import deque
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest
from consent_support import call, purge_family
from eval_support import eval_target
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import delete, func, select

from hoicon.api.auth import issue_guardian_access_token
from hoicon.channels.guardian import ChannelDeps, send_to_guardian
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, AgentStep, Family, Incident, Job, Member, MessageOut
from hoicon.db.session import get_sessionmaker
from hoicon.domain.pii import note_flags
from hoicon.eval.cases import SCENARIOS_DIR, case_secrets, elder_reply, load_case
from hoicon.eval.runner import run_suite
from hoicon.services import sim_service
from hoicon.services.runtime_service import close_runtime

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
ORIGIN = {"Sec-Fetch-Site": "same-origin"}
SCAM = "fake_police_safe_account_002"
NO_RULE = "benign_official_residence_005"


def _validator(name: str) -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = json.loads((SCHEMAS / f"{name}.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


RUN = _validator("sim_run")
SCENARIOS = _validator("sim_scenarios")


@pytest.fixture
async def sim_world(seeded_threat: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[SimpleNamespace]:
    """Gia đình demo (người giám hộ + "Mẹ") và một gia đình THẬT; cổng mô phỏng bật; khóa JWT/pepper GIẢ."""
    monkeypatch.setenv("HOICON_DEVICE_JWT_SECRET", JWT_KEY)
    monkeypatch.setenv("HOICON_SIM_ENABLED", "true")
    monkeypatch.setenv("HOICON_ANTHROPIC_API_KEY", "")  # không bao giờ gọi LLM thật trong test
    get_settings.cache_clear()
    sim_service.reset()
    world = SimpleNamespace(families=[])
    async with get_sessionmaker().begin() as session:
        for tag, demo in (("demo", True), ("real", False)):
            family = Family(display_name=f"test-033-{tag}-{secrets.token_hex(3)}", region="nam", is_demo=demo)
            session.add(family)
            await session.flush()
            guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
            protected = Member(family_id=family.id, role="protected", alias="Mẹ")
            session.add_all([guardian, protected])
            await session.flush()
            token = issue_guardian_access_token(guardian.id, family.id)
            setattr(world, tag, SimpleNamespace(family=family.id, guardian=guardian.id, token=token))
            world.families.append(family.id)
    yield world
    await close_runtime()
    for entry in list(sim_service._registry):
        await sim_service._drop(entry)
    async with get_sessionmaker().begin() as session:
        threads = [
            str(i) for i in await session.scalars(select(Incident.id).where(Incident.family_id.in_(world.families)))
        ]
        await session.execute(delete(AgentRun).where(AgentRun.thread_id.in_(threads)))
    for family_id in world.families:
        await purge_family(family_id)
    sim_service.reset()
    get_settings.cache_clear()


async def post(world_part: Any, path: str, body: Any = None, **headers: str) -> Any:
    return await call("POST", path, token=world_part.token, json=body, headers={**ORIGIN, **headers})


async def get(world_part: Any, path: str) -> Any:
    return await call("GET", path, token=world_part.token)


async def finish(run: dict[str, Any], who: Any, case_id: str = SCAM) -> dict[str, Any]:
    """Trả lời mọi câu E8 theo kịch bản (như eval) cho tới khi đồ thị không còn hỏi."""
    case = load_case(case_id)
    asks = 0
    while run["pending_question"] is not None:
        asks += 1
        flags = note_flags(case.elder_note) if asks == 1 and case.elder_note else None
        reply = elder_reply(case, run["pending_question"]["question_id"], first=False)
        body: dict[str, Any] = {"question_id": run["pending_question"]["question_id"], "answer": reply["answer"]}
        if flags:
            body["note_flags"] = flags
        res = await post(who, f"/v1/sim/runs/{run['incident_id']}/answer", body)
        assert res.status_code == 200, res.text
        run = res.json()
        RUN.validate(run)
        assert asks <= 3
    return run


# --- cổng (T003) -----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/sim/scenarios"),
        ("POST", "/v1/sim/runs"),
        ("GET", "/v1/sim/runs/5b0c1f3e-0000-4000-8000-000000000001"),
        ("POST", "/v1/sim/runs/5b0c1f3e-0000-4000-8000-000000000001/answer"),
    ],
)
async def test_gate_off_makes_every_route_a_404_even_without_a_session(
    sim_world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, method: str, path: str
) -> None:
    monkeypatch.setenv("HOICON_SIM_ENABLED", "false")
    get_settings.cache_clear()
    res = await call(method, path, json={}, headers=ORIGIN)
    assert res.status_code == 404
    res = await call(method, path, token=sim_world.demo.token, json={}, headers=ORIGIN)
    assert res.status_code == 404


async def test_real_family_gets_404_and_missing_session_gets_401(sim_world: SimpleNamespace) -> None:
    assert (await get(sim_world.real, "/v1/sim/scenarios")).status_code == 404
    assert (await post(sim_world.real, "/v1/sim/runs", {"scenario_id": SCAM})).status_code == 404
    assert (await call("GET", "/v1/sim/scenarios")).status_code == 401


async def test_wrong_origin_is_forbidden_for_writes(sim_world: SimpleNamespace) -> None:
    res = await call(
        "POST",
        "/v1/sim/runs",
        token=sim_world.demo.token,
        json={"scenario_id": SCAM},
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403


def test_production_compose_never_sets_the_sim_gate() -> None:
    compose = (Path(__file__).resolve().parents[3] / "infra" / "compose.prod.yml").read_text(encoding="utf-8")
    assert "HOICON_SIM_ENABLED" not in compose


# --- kịch bản (T005) -------------------------------------------------------------------------------------------------


async def test_scenarios_match_the_contract_and_the_yaml_files(sim_world: SimpleNamespace) -> None:
    res = await get(sim_world.demo, "/v1/sim/scenarios")
    assert res.status_code == 200
    body = res.json()
    SCENARIOS.validate(body)
    ids = [s["id"] for s in body["scenarios"]]
    assert ids == sorted(ids) and len(ids) == len(list(SCENARIOS_DIR.glob("*.yaml")))
    blob = json.dumps(body, ensure_ascii=False)
    assert "source_ref" not in blob and "elder_note" not in blob and "device_signals" not in blob
    # FR-015: mọi kịch bản có tên tiếng Việt; id chỉ còn ở trường `id`
    assert all(s["title_vi"] for s in body["scenarios"])
    by_id = {s["id"]: s["title_vi"] for s in body["scenarios"]}
    if "fake_police_safe_account_002" in by_id:
        assert by_id["fake_police_safe_account_002"] == "Giả danh công an · ca 2"


# --- một lượt phát lại (T006, T007) ----------------------------------------------------------------------------------


async def test_a_replayed_run_follows_the_same_steps_as_the_eval_run_of_the_same_case(
    sim_world: SimpleNamespace,
) -> None:
    res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM, "llm": "replay"})
    assert res.status_code == 200, res.text
    run = res.json()
    RUN.validate(run)
    assert run["is_demo"] and run["llm_mode"] == "replay" and run["incident_id"] and run["run_id"]
    assert run["pending_question"] is not None and run["pending_question"]["question_id"]
    assert run["guardian_messages"], "cảnh báo nhanh phải có trong bản ghi mock"
    assert all(m["text"].startswith("Đây là trợ lý AI HỏiCon") for m in run["guardian_messages"])
    run = await finish(run, sim_world.demo)
    assert run["pending_question"] is None

    async with get_sessionmaker()() as session:
        rows = (
            await session.scalars(
                select(AgentStep).where(AgentStep.run_id == UUID(run["run_id"])).order_by(AgentStep.at, AgentStep.id)
            )
        ).all()
    sim_nodes = [r.node for r in rows]
    url, shared = eval_target()
    (outcome,) = await run_suite([load_case(SCAM)], database_url=url, shared_db_ok=shared, suite="smoke")
    eval_nodes = [s["node"] for s in outcome.result.steps]
    assert sim_nodes == eval_nodes[: len(sim_nodes)] and len(sim_nodes) >= 5, (sim_nodes, eval_nodes)
    assert [r.output["level"] for r in rows if r.node in ("ingest", "risk_scorer")] == [
        s["output"]["level"] for s in outcome.result.steps if s["node"] in ("ingest", "risk_scorer")
    ]


async def test_the_guardian_can_decide_with_the_existing_route_and_the_view_shows_the_final_state(
    sim_world: SimpleNamespace,
) -> None:
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    run = await finish(run, sim_world.demo)
    res = await post(sim_world.demo, f"/v1/incidents/{run['incident_id']}/decision", {"decision": "emergency_pause"})
    assert res.status_code == 200, res.text
    view = (await get(sim_world.demo, f"/v1/sim/runs/{run['incident_id']}")).json()
    RUN.validate(view)
    assert view["state"] == "case_open"


async def test_responses_never_carry_the_phone_number_hash_or_package_name(sim_world: SimpleNamespace) -> None:
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    run = await finish(run, sim_world.demo)
    blob = json.dumps(run, ensure_ascii=False)
    for secret in case_secrets(load_case(SCAM)):
        assert secret not in blob, secret


async def test_a_scenario_that_triggers_no_rule_opens_no_incident(sim_world: SimpleNamespace) -> None:
    res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": NO_RULE})
    assert res.status_code == 200
    run = res.json()
    RUN.validate(run)
    assert run["incident_id"] is None and run["note"] == "Máy không bật nhắc dừng lại với tình huống này"


async def test_unknown_scenario_and_invalid_body(sim_world: SimpleNamespace) -> None:
    assert (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": "khong_co_999"})).status_code == 404
    assert (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": "../etc/passwd"})).status_code == 422
    assert (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM, "llm": "x"})).status_code == 422


async def test_live_without_a_key_falls_back_to_templates(sim_world: SimpleNamespace) -> None:
    res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM, "llm": "live"})
    assert res.status_code == 200, res.text
    assert res.json()["llm_mode"] == "fallback"


async def test_runs_of_another_family_or_real_incidents_are_not_visible(sim_world: SimpleNamespace) -> None:
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    assert (await get(sim_world.real, f"/v1/sim/runs/{run['incident_id']}")).status_code == 404
    async with get_sessionmaker().begin() as session:  # một sự cố thường (không phải mô phỏng) của gia đình demo
        member = await session.scalar(
            select(Member.id).where(Member.family_id == sim_world.demo.family, Member.role == "protected")
        )
        real = Incident(
            family_id=sim_world.demo.family, member_id=member, state="detected", level="high", rule_floor="high"
        )
        real.is_demo = True
        session.add(real)
        await session.flush()
        real_id = real.id
    assert (await get(sim_world.demo, f"/v1/sim/runs/{real_id}")).status_code == 404
    res = await post(
        sim_world.demo, f"/v1/sim/runs/{real_id}/answer", {"question_id": "q_know_caller", "answer": "yes"}
    )
    assert res.status_code == 404


async def test_answering_a_question_that_is_not_waiting_is_a_conflict(sim_world: SimpleNamespace) -> None:
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    asked = run["pending_question"]["question_id"]
    other = next(q for q in ("q_caller_authority", "q_asked_transfer", "q_know_caller") if q != asked)
    res = await post(
        sim_world.demo, f"/v1/sim/runs/{run['incident_id']}/answer", {"question_id": other, "answer": "yes"}
    )
    assert res.status_code == 409
    free_text = {"question_id": asked, "answer": "yes", "note": "đừng báo ai"}
    assert (await post(sim_world.demo, f"/v1/sim/runs/{run['incident_id']}/answer", free_text)).status_code == 422


# --- Zalo thật không bao giờ được gọi (T004) -------------------------------------------------------------------------


class CountingClient:
    simulated = False

    def __init__(self) -> None:
        self.calls = 0

    async def send_message(self, chat_id: str, text: str) -> Any:
        self.calls += 1
        raise AssertionError("LiveZaloClient không được gọi cho sự cố mô phỏng")


async def test_sim_messages_never_reach_the_zalo_client_even_in_live_mode(
    sim_world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOICON_ZALO_MODE", "live")
    get_settings.cache_clear()
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    async with get_sessionmaker()() as session:
        jobs = (
            await session.scalars(
                select(Job).where(
                    Job.kind == "notify_guardian", Job.idempotency_key.startswith(f"{run['incident_id']}:msg:")
                )
            )
        ).all()
    assert jobs and all(j.payload.get("sim") is True for j in jobs)
    client = CountingClient()
    deps = ChannelDeps(get_sessionmaker(), client, get_settings())
    for job in jobs:
        assert await send_to_guardian(deps, job.payload) == "simulated"
    assert client.calls == 0
    async with get_sessionmaker()() as session:
        sent = await session.scalar(
            select(func.count()).select_from(MessageOut).where(MessageOut.incident_id == UUID(run["incident_id"]))
        )
    assert sent == 0, "không tạo messages_out, không trừ hạn mức"


async def test_a_normal_incident_payload_has_no_sim_flag(sim_world: SimpleNamespace) -> None:
    from hoicon.services import AlertService

    async with get_sessionmaker().begin() as session:
        member = await session.scalar(
            select(Member.id).where(Member.family_id == sim_world.demo.family, Member.role == "protected")
        )
        incident = Incident(
            family_id=sim_world.demo.family, member_id=member, state="detected", level="high", rule_floor="high"
        )
        incident.is_demo = True
        session.add(incident)
        await session.flush()
        await AlertService.trigger_guardian_fast_alert(session, incident=incident)
        job = await session.scalar(select(Job).where(Job.idempotency_key == f"{incident.id}:msg:fast_alert"))
    assert "sim" not in job.payload


# --- hạn mức (T008) --------------------------------------------------------------------------------------------------


async def test_the_eleventh_start_in_an_hour_is_rate_limited(sim_world: SimpleNamespace) -> None:
    now = time.monotonic()
    sim_service._starts[sim_world.demo.guardian] = deque([now - 5] * sim_service.MAX_STARTS_PER_HOUR)
    res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})
    assert res.status_code == 429
    assert int(res.headers["Retry-After"]) > 0


async def test_a_fourth_concurrent_run_is_rate_limited(sim_world: SimpleNamespace) -> None:
    for _ in range(sim_service.MAX_ACTIVE_PER_FAMILY):
        res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})
        assert res.status_code == 200, res.text
    res = await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})
    assert res.status_code == 429 and res.headers["Retry-After"]


async def test_an_expired_replay_runtime_continues_with_the_shared_runtime_as_fallback(
    sim_world: SimpleNamespace,
) -> None:
    run = (await post(sim_world.demo, "/v1/sim/runs", {"scenario_id": SCAM})).json()
    await sim_service._drop(UUID(run["incident_id"]))  # như hết 60 phút hoặc API khởi động lại
    asked = run["pending_question"]["question_id"]
    res = await post(
        sim_world.demo, f"/v1/sim/runs/{run['incident_id']}/answer", {"question_id": asked, "answer": "yes"}
    )
    assert res.status_code == 200, res.text
    assert res.json()["llm_mode"] == "fallback"


async def test_registry_keeps_at_most_twenty_runtimes_and_drops_the_expired(sim_world: SimpleNamespace) -> None:
    for i in range(sim_service.MAX_RUNTIMES + 3):
        sim_service._registry[UUID(int=i + 1)] = sim_service._Entry("replay", time.monotonic() + 100)
    await sim_service._prune(time.monotonic())
    assert len(sim_service._registry) == sim_service.MAX_RUNTIMES
    sim_service._registry[UUID(int=999)] = sim_service._Entry("replay", time.monotonic() - 1)
    await sim_service._prune(time.monotonic())
    assert UUID(int=999) not in sim_service._registry
