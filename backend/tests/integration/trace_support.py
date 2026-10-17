"""Dữ liệu và hàm dùng chung cho test spec 025 (`test_api_runs.py`, `test_trace_sse_live.py`): hai gia đình demo, mỗi
nhà một người giám hộ, một sự cố đã đóng + một lượt `done` có bước "đầu độc"; dọn sạch sau test."""

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from sqlalchemy import select

from hoicon.db.models import AgentRun, AgentStep, Incident, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services import trace_service

SCHEMAS = Path(__file__).resolve().parents[3] / "docs" / "schemas"
JWT_KEY = "integration-test-key-" + "k" * 32  # gitleaks:allow — khóa GIẢ cho test
RAW_PHONE = re.compile(r"(\+84|0)(3[2-9]|5[689]|7[06-9]|8[1-689]|9[0-46-9])[0-9]{7}")
LONG_HEX = re.compile(r"[0-9a-fA-F]{32,}")
FAKE_PHONE = "0900000123"  # số hư cấu
HEX64 = "0123456789abcdef" * 4
TOKEN43 = "29KgWDAcHhzTs8TUOPWMx0Odx6Z5vZ0X_TyTcAV6t4M"  # gitleaks:allow — token GIẢ 43 ký tự (hình dạng action token)
AT = datetime(2026, 12, 1, 2, 15, 31, tzinfo=UTC)


def _validators() -> dict[str, Draft202012Validator]:
    docs = {p.stem.removesuffix(".v1"): json.loads(p.read_text(encoding="utf-8")) for p in SCHEMAS.glob("*.v1.json")}
    registry = Registry().with_resources([(d["$id"], Resource.from_contents(d)) for d in docs.values()])
    return {
        name: Draft202012Validator(docs[name], registry=registry, format_checker=FormatChecker())
        for name in ("agent_step", "run_steps", "run_done")
    }


VALIDATORS = _validators()


def parse_sse(body: str) -> list[dict[str, Any]]:
    """Khung SSE ⇒ [{"event", "id", "data"}]; khung chú thích (`: ping`) bỏ qua."""
    frames = []
    for block in body.split("\n\n"):
        if not block or block.startswith(":") or block.startswith("retry:"):
            continue
        fields = dict(line.split(": ", 1) for line in block.splitlines())
        frames.append({"event": fields["event"], "id": fields.get("id"), "data": json.loads(fields["data"])})
    return frames


async def add_run(incident_id: UUID | str, ids: dict[str, Any], *, status: str = "done", poisoned: bool = True) -> UUID:
    thread = str(incident_id)
    async with get_sessionmaker().begin() as session:
        run = AgentRun(
            graph="incident",
            status=status,
            thread_id=thread,
            cost_usd=Decimal("0.002450"),
            is_drill=False,
            is_demo=True,
        )
        session.add(run)
        await session.flush()
        outputs: list[dict[str, Any] | None] = [
            {"level": "high", "rule_floor": "high"},
            {"level": "high", "h1": HEX64, "nested": {"phone": FAKE_PHONE, "ok": [f"gọi {FAKE_PHONE} ngay", HEX64]}},
            {
                "link": f"/a/{TOKEN43}",
                "note": "kẻ gian nói gì đó",
                "amount": "20.000.000 đồng",
                "text": "thân tin Zalo",
            },
            None,
        ]
        for i, output in enumerate(outputs if poisoned else outputs[:1]):
            session.add(
                AgentStep(
                    run_id=run.id, node=("ingest", "risk_scorer", "intervention", "resolve")[i], output=output,
                    input_redacted={"context": f"người gọi {FAKE_PHONE}", "untrusted": True, "h1": HEX64},
                    latency_ms=i + 1, tokens_in=0, tokens_out=0, cost_usd=Decimal(0), fallback_used=False,
                    at=datetime(2026, 12, 1, 2, 15, 31 + i, tzinfo=UTC),
                )
            )  # fmt: skip
    ids["runs"].append(run.id)
    return run.id


async def another_incident(world: dict[str, Any], tag: str = "a") -> UUID:
    """Thêm một sự cố đã đóng cho gia đình `tag` (`agent_runs.thread_id` UNIQUE ⇒ mỗi lượt cần một sự cố riêng)."""
    async with get_sessionmaker().begin() as session:
        incident = Incident(
            family_id=world[tag]["family"], member_id=await protected_of(world, tag), state="resolved_safe",
            level="high", rule_floor="high", is_demo=True, outcome="safe", closed_at=AT,
        )  # fmt: skip
        session.add(incident)
    return incident.id


def auth(world: dict[str, Any], tag: str = "a") -> str:
    return world[tag]["token"]


async def steps_in_db(run_id: UUID) -> list[AgentStep]:
    async with get_sessionmaker()() as session:
        return await trace_service.list_steps(session, run_id)


async def protected_of(world: dict[str, Any], tag: str) -> UUID:

    async with get_sessionmaker()() as session:
        return await session.scalar(
            select(Member.id).where(Member.family_id == world[tag]["family"], Member.role == "protected")
        )
