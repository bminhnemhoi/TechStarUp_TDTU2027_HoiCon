"""Spec 031 FR-013 (SC-001, SC-002, SC-006): hồ sơ trên sự cố seed THẬT chạy đồ thị với `ReplayClient` của kịch bản.

Eval không có sự cố thật nên đi thẳng END; độ sạch của hồ sơ đo ở đây: ≥ 5 kịch bản lừa đảo (≥ 2 chèn lệnh)."""

import json
from collections.abc import AsyncIterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from case_support import purge_case, seed_case
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import select

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.config import get_settings
from hoicon.db.models import AgentRun, AgentStep, CaseFile, Job
from hoicon.db.session import get_sessionmaker
from hoicon.eval.cases import (
    Case,
    build_event,
    case_secrets,
    elder_reply,
    find_cassette,
    load_case,
    load_suite,
)
from hoicon.eval.replay import ReplayClient

pytestmark = pytest.mark.integration

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"


def _content_validator() -> Draft202012Validator:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.json")]
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs])
    schema = {"$ref": "https://hoicon.vn/schemas/case_file.v1.json#/$defs/content"}
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


CONTENT = _content_validator()


def pick_cases() -> list[Case]:
    scams = [c for c in load_suite("full") if not c.is_benign and build_event(c) is not None]
    injected = [c for c in scams if c.injection][:2]
    plain = [c for c in scams if not c.injection][:3]
    return [*plain, *injected]


CASES = pick_cases()


def test_the_selection_covers_five_scam_scenarios_with_two_injections() -> None:
    assert len(CASES) == 5 and sum(c.injection for c in CASES) == 2


@pytest.fixture(params=[c.id for c in CASES])
async def run(request: pytest.FixtureRequest, require_db: None, seeded_threat: dict[str, Any]) -> AsyncIterator[Any]:
    case = load_case(request.param)
    world = await seed_case(state="detected", with_run=False, flagged=False, answers=())
    client = ReplayClient.from_path(find_cassette(case.id, "full"))
    settings = get_settings().model_copy(update={"timer_ask_elder_s": 60, "timer_t3_s": 60})
    deps = Deps(LlmRouter(client, settings.llm_fast_model, Decimal(1000)), get_sessionmaker(), settings)
    yield case, world, deps
    await purge_case(world)


async def test_a_scam_decision_produces_a_clean_draft_and_message(run: Any) -> None:
    case, world, deps = run
    thread = str(world.incident)
    async with IncidentRuntime.open(deps) as runtime:
        status = await runtime.start(
            build_event(case), incident_id=thread, elder_alias="Mẹ", family_id=str(world.family), is_demo=True
        )
        asks = 0
        while status.waiting_for == "ask_elder":
            asks += 1
            status = await runtime.resume(
                thread, elder_reply(case, status.interrupt["question_id"], first=asks == 1), expect="ask_elder"
            )
            assert asks <= 3
        status = await runtime.resume(thread, {"decision": "scam"}, expect="await_guardian")
        assert status.waiting_for == "await_case_approval", status
        await runtime.graph.checkpointer.adelete_thread(thread)

    async with get_sessionmaker()() as session:
        row = await session.scalar(select(CaseFile).where(CaseFile.incident_id == world.incident))
        job = await session.scalar(select(Job).where(Job.idempotency_key == f"{world.incident}:msg:case_file"))
        run_row = await session.scalar(select(AgentRun).where(AgentRun.thread_id == thread))
        steps = (await session.scalars(select(AgentStep).where(AgentStep.run_id == run_row.id))).all()
    assert row is not None and row.status == "draft"
    CONTENT.validate(row.content)
    assert row.content["ai_label"].startswith("Đây là trợ lý AI HỏiCon")
    assert row.summary_source == "template"  # cassette không có phản hồi cho `case_file` ⇒ rơi về mẫu (SC-006)
    assert job is not None and job.payload["text"].startswith("Đây là trợ lý AI HỏiCon")
    blob = json.dumps(
        [row.content, job.payload, [[s.input_redacted, s.output] for s in steps]], ensure_ascii=False, default=str
    )
    for secret in case_secrets(case):
        assert secret not in blob, f"{case.id}: lọt chuỗi bí mật của ca"
