"""Eval smoke chạy đồ thị sự cố thật trên Postgres với phản hồi LLM ghi sẵn (spec 030, FR-005/010/011/012)."""

import ipaddress
import socket
import uuid
from typing import Any

import anthropic
import pytest
from eval_support import run
from pydantic import SecretStr
from sqlalchemy import func, select

from hoicon.config import get_settings
from hoicon.db.models import Job
from hoicon.eval.cases import load_case, load_suite
from hoicon.eval.runner import CaseOutcome, IsolationError, check_isolation, run_suite

pytestmark = pytest.mark.integration

THREE = ["fake_police_drug_ring_001", "benign_family_vegetables_001", "benign_official_tax_reminder_001"]


def by_id(outcomes: list[CaseOutcome]) -> dict[str, CaseOutcome]:
    return {o.case.id: o for o in outcomes}


def fingerprint(outcome: CaseOutcome) -> dict[str, Any]:
    r = outcome.result
    return {
        "levels": r.levels,
        "final": r.final_level,
        "outcome": r.outcome,
        "notified": r.notified,
        "messages": r.messages,
        "questions": r.questions,
        "violations": outcome.violations,
        "failures": outcome.failures,
        "fallbacks": r.fallbacks,
        "llm_calls": r.llm_calls,
    }


async def test_three_representative_cases(target: tuple[str, bool]) -> None:
    got = by_id(await run(target, [load_case(c) for c in THREE]))
    scam, benign, quiet = got[THREE[0]], got[THREE[1]], got[THREE[2]]
    # LLM cố hạ mức xuống low nhưng sàn critical giữ; người giám hộ quyết định "scam" ⇒ ngăn được
    assert scam.result.final_level == "critical" and scam.result.outcome == "resolved_prevented"
    assert scam.result.notified and scam.result.incident_started and scam.violations == [] and scam.failures == []
    assert scam.result.run_id and all(m.startswith("Đây là trợ lý AI HỏiCon") for m in scam.result.messages)
    assert benign.result.final_level == "high" and benign.result.outcome == "resolved_safe"  # sàn R1 = high
    assert benign.violations == [] and benign.failures == []
    assert quiet.result.incident_started is False and quiet.result.outcome == "no_incident"
    assert quiet.result.final_level == "none" and not quiet.result.notified and quiet.violations == []


async def test_whole_smoke_suite_has_no_violation_and_full_disclosure(target: tuple[str, bool]) -> None:
    outcomes = await run(target, load_suite("smoke"))
    assert len(outcomes) == 20
    assert {o.case.id: o.violations for o in outcomes if o.violations} == {}
    for o in outcomes:
        assert all(m.startswith("Đây là trợ lý AI HỏiCon") for m in [*o.result.messages, *o.result.questions])
    assert sum(o.result.incident_started for o in outcomes) == 19  # đúng một ca không kích hoạt luật
    assert all(o.result.fallbacks <= o.result.llm_calls for o in outcomes)


async def test_two_runs_give_identical_results_on_the_same_database(target: tuple[str, bool]) -> None:
    cases = [load_case(c) for c in [*THREE, "fake_bank_card_locked_002", "recovery_scam_bank_refund_003"]]
    first, second = await run(target, cases), await run(target, cases)
    assert [fingerprint(o) for o in first] == [fingerprint(o) for o in second]
    runs = [{o.result.run_id for o in outcomes} - {"no-incident"} for outcomes in (first, second)]
    assert len(runs[0]) == len(runs[1]) == 4 and runs[0].isdisjoint(runs[1])  # mỗi lượt có agent_runs riêng


async def test_error_cassettes_fall_back_to_templates(target: tuple[str, bool]) -> None:
    got = by_id(await run(target, [load_case("recovery_scam_bank_refund_003")]))["recovery_scam_bank_refund_003"]
    assert got.result.fallbacks == got.result.llm_calls == 3  # từ chối + quá hạn + sai cấu trúc
    assert got.result.final_level == "critical" and got.violations == []


async def test_nothing_leaves_the_machine_and_no_anthropic_client(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts: list[Any] = []
    real_connect = socket.socket.connect

    def guarded(self: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else None
        if host not in (None, "localhost") and not ipaddress.ip_address(host).is_loopback:
            attempts.append(address)
            raise OSError("eval không được phép kết nối ra ngoài")
        return real_connect(self, address)

    def no_client(*_: Any, **__: Any) -> None:
        raise AssertionError("eval không được tạo client Anthropic")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(anthropic.AsyncAnthropic, "__init__", no_client)
    monkeypatch.setattr(anthropic.Anthropic, "__init__", no_client)
    outcomes = await run(target, [load_case(c) for c in THREE])
    assert attempts == [] and len(outcomes) == 3


async def test_no_eval_job_is_left_behind(target: tuple[str, bool]) -> None:
    from hoicon.eval.runner import make_sessionmaker

    await run(target, [load_case(c) for c in THREE])
    sessions, engine = make_sessionmaker(target[0])
    try:
        async with sessions() as session:
            left = await session.scalar(
                select(func.count()).select_from(Job).where(Job.idempotency_key.startswith("eval-"))
            )
    finally:
        await engine.dispose()
    assert left == 0


# --- Cô lập (FR-010) -------------------------------------------------------------------------------------------


def settings_for(url: str, env: str = "dev"):
    return get_settings().model_copy(update={"database_url": SecretStr(url), "env": env})


def test_refuses_prod_environment() -> None:
    with pytest.raises(IsolationError, match="prod"):
        check_isolation(
            "postgresql+psycopg://x:y@127.0.0.1:15432/hoicon_eval", True, settings_for("postgresql+psycopg://a", "prod")
        )


def test_refuses_the_application_database_unless_shared_flag() -> None:
    url = "postgresql+psycopg://x:y@127.0.0.1:15432/hoicon"
    with pytest.raises(IsolationError, match="trùng"):
        check_isolation(url, False, settings_for(url))
    check_isolation(url, True, settings_for(url))  # CI: DB service dùng chung, có cờ cho phép
    check_isolation("postgresql+psycopg://x:y@127.0.0.1:15432/hoicon_eval", False, settings_for(url))


def test_refuses_missing_url() -> None:
    with pytest.raises(IsolationError, match="HOICON_EVAL_DATABASE_URL"):
        check_isolation("", False, settings_for("postgresql+psycopg://a"))


@pytest.mark.parametrize(
    "eval_url",
    [
        "postgresql+psycopg://other:pw@localhost:15432/hoicon",  # localhost = 127.0.0.1
        "postgresql+psycopg://hoicon:khac@127.0.0.1/hoicon?connect_timeout=3".replace("127.0.0.1/", "127.0.0.1:15432/"),
        "postgresql://hoicon:hoicon_dev@[::1]:15432/hoicon",  # IPv6 loopback
    ],
)
def test_isolation_sees_through_different_spellings_of_the_application_database(eval_url: str) -> None:
    app = settings_for("postgresql+psycopg://hoicon:hoicon_dev@127.0.0.1:15432/hoicon")
    with pytest.raises(IsolationError, match="trùng"):
        check_isolation(eval_url, False, app)
    check_isolation(eval_url.replace(":15432/hoicon", ":15432/hoicon_eval"), False, app)  # DB khác tên ⇒ cho phép


@pytest.mark.parametrize("env", ["prod", "Prod", "PRODUCTION", " production "])
def test_refuses_every_spelling_of_production(env: str) -> None:
    with pytest.raises(IsolationError, match="prod"):
        check_isolation(
            "postgresql+psycopg://x:y@127.0.0.1:15432/hoicon_eval", True, settings_for("postgresql+psycopg://a", env)
        )


def test_a_remote_database_must_look_like_an_eval_database_unless_shared() -> None:
    app = settings_for("postgresql+psycopg://hoicon:pw@127.0.0.1:15432/hoicon")
    with pytest.raises(IsolationError, match="eval"):
        check_isolation("postgresql+psycopg://x:y@db.example.internal:5432/hoicon_main", False, app)
    check_isolation("postgresql+psycopg://x:y@db.example.internal:5432/hoicon_eval", False, app)
    check_isolation("postgresql+psycopg://x:y@db.example.internal:5432/ci_test", False, app)
    check_isolation("postgresql+psycopg://x:y@db.example.internal:5432/hoicon_main", True, app)  # CI: cờ cho phép


async def test_escalation_to_the_second_guardian_is_part_of_every_incident(target: tuple[str, bool]) -> None:
    (outcome,) = await run(target, [load_case("fake_police_drug_ring_001")])
    assert len(outcome.result.messages) == 4  # fast_alert, detail, reminder (T1), escalation (T2)
    assert any("đã nhắn cho một người nhà khác" in m for m in outcome.result.messages)
    assert outcome.violations == []


async def test_drill_incidents_carry_the_drill_label_everywhere(target: tuple[str, bool]) -> None:
    url, shared = target
    cases = [load_case("fake_police_drug_ring_001"), load_case("benign_family_vegetables_001")]
    outcomes = await run_suite(cases, database_url=url, shared_db_ok=shared, drill=True)
    for o in outcomes:
        assert o.violations == [] and o.result.is_drill
        assert all("[DIỄN TẬP]" in m for m in [*o.result.messages, *o.result.questions])


async def test_eval_never_attaches_a_family_so_no_guardian_channel_can_fire(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.agents.runtime import IncidentRuntime

    real_start, seen = IncidentRuntime.start, []

    async def spy(self, event, **kwargs):
        seen.append(kwargs)
        return await real_start(self, event, **kwargs)

    monkeypatch.setattr(IncidentRuntime, "start", spy)
    await run(target, [load_case("fake_police_drug_ring_001")])
    assert seen and all(k.get("family_id") is None and k["is_demo"] is True for k in seen)
    assert all(k["incident_id"].startswith("eval-") for k in seen)


async def test_a_case_that_crashes_leaves_no_running_agent_run(
    target: tuple[str, bool], monkeypatch: pytest.MonkeyPatch
) -> None:
    from hoicon.agents.runtime import IncidentRuntime
    from hoicon.db.models import AgentRun
    from hoicon.eval.runner import make_sessionmaker

    async def boom(self, *args, **kwargs):
        raise RuntimeError("giả lập lỗi giữa ca")

    monkeypatch.setattr(IncidentRuntime, "resume", boom)
    (outcome,) = await run(target, [load_case("fake_police_drug_ring_001")])
    assert (
        outcome.result.error == "RuntimeError"
        and outcome.violations == []
        and outcome.failures == ["unexpected_outcome"]
    )
    sessions, engine = make_sessionmaker(target[0])
    try:
        async with sessions() as session:
            status = await session.scalar(
                select(AgentRun.status).where(AgentRun.id == uuid.UUID(outcome.result.run_id))
            )
    finally:
        await engine.dispose()
    assert status == "failed"  # không để `recover()` của app nhặt lại thread eval
