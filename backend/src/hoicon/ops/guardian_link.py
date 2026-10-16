"""Công cụ dev cho E2E web người giám hộ (spec 027, T019): sinh liên kết đăng nhập, dựng và dọn dữ liệu demo.

    uv run --directory backend python -m hoicon.ops.guardian_link --member <uuid>        # in liên kết /login/<token>
    uv run --directory backend python -m hoicon.ops.guardian_link --seed                  # gia đình + sự cố + lượt chạy
    uv run --directory backend python -m hoicon.ops.guardian_link --add-step <run_id>     # chèn một bước agent_steps
    uv run --directory backend python -m hoicon.ops.guardian_link --cleanup <family_id>   # dọn gia đình demo

CHỈ chạy khi HOICON_ENV=dev (cùng quy tắc với `pairing_code`): liên kết in ra là token dùng-một-lần (15 phút) để mở trên
trình duyệt, KHÔNG phải khóa dịch vụ; lệnh này không bao giờ chạm gia đình thật (chỉ nhận người giám hộ của gia đình
`is_demo`). Mọi định danh là dữ liệu hư cấu.
"""

import argparse
import asyncio
import json
import sys
from datetime import timedelta
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from hoicon.config import get_settings
from hoicon.db.models import AgentRun, AgentStep, Family, Incident, IncidentTransition, Member
from hoicon.db.session import get_sessionmaker
from hoicon.services.action_token_service import ActionTokenService

LOGIN_TTL = timedelta(minutes=15)
DEFAULT_BASE_URL = "http://localhost:3100"
REFUSED = "Từ chối: lệnh này chỉ chạy khi HOICON_ENV=dev và chỉ với gia đình demo (không bao giờ với gia đình thật)."


def allowed() -> bool:
    return get_settings().env == "dev"


async def make_link(sessions: async_sessionmaker, member_id: UUID, base_url: str = DEFAULT_BASE_URL) -> str | None:
    """Liên kết đăng nhập cho một người giám hộ của gia đình demo; None nếu không phải người giám hộ demo."""
    async with sessions.begin() as session:
        member = await session.get(Member, member_id)
        family = await session.get(Family, member.family_id) if member is not None else None
        if member is None or member.role != "guardian" or family is None or not family.is_demo:
            return None
        _, raw = await ActionTokenService.create_token(
            session, incident_id=None, member_id=member.id, scope="guardian_view", ttl=LOGIN_TTL
        )
    return f"{base_url.rstrip('/')}/login/{raw}"


async def seed(sessions: async_sessionmaker, base_url: str = DEFAULT_BASE_URL) -> dict[str, str]:
    """Gia đình demo + người giám hộ + người được bảo vệ ("Mẹ") + một sự cố đang chờ + một lượt chạy `running`."""
    async with sessions.begin() as session:
        family = Family(display_name="E2E 027", region="nam", is_demo=True)
        session.add(family)
        await session.flush()
        guardian = Member(family_id=family.id, role="guardian", guardian_rank=1)
        protected = Member(family_id=family.id, role="protected", alias="Mẹ")
        session.add_all([guardian, protected])
        await session.flush()
        incident = Incident(
            family_id=family.id, member_id=protected.id, state="awaiting_guardian", level="high", rule_floor="high"
        )
        incident.is_demo = True
        session.add(incident)
        await session.flush()
        session.add(
            IncidentTransition(
                incident_id=incident.id, from_state=None, to_state="detected", actor="device", reason="risk_event"
            )
        )
        run = AgentRun(incident_id=incident.id, graph="incident", status="running", thread_id=str(incident.id))
        run.is_demo = True
        session.add(run)
        await session.flush()
        session.add(AgentStep(run_id=run.id, node="ingest", output={"level": "high", "threat": "unknown"}))
        ids = {
            "family_id": str(family.id),
            "guardian_id": str(guardian.id),
            "incident_id": str(incident.id),
            "run_id": str(run.id),
        }
    link = await make_link(sessions, UUID(ids["guardian_id"]), base_url)
    return {**ids, "login_url": link or ""}


async def add_step(sessions: async_sessionmaker, run_id: UUID, node: str = "risk_scorer") -> dict[str, str] | None:
    async with sessions.begin() as session:
        run = await session.get(AgentRun, run_id)
        if run is None or not run.is_demo:
            return None
        step = AgentStep(run_id=run.id, node=node, output={"level": "high", "question": ""}, at=func.clock_timestamp())
        session.add(step)
        await session.flush()
        await session.refresh(step)  # `at` do DB đặt: để đo độ trễ từ lúc commit tới lúc web hiện bước
        return {"step_id": str(step.id), "at": step.at.isoformat()}


async def cleanup(sessions: async_sessionmaker, family_id: UUID) -> bool:
    async with sessions.begin() as session:
        family = await session.get(Family, family_id)
        if family is None or not family.is_demo:
            return False
        incidents = [str(i) for i in await session.scalars(select(Incident.id).where(Incident.family_id == family_id))]
        await session.execute(delete(AgentRun).where(AgentRun.thread_id.in_(incidents)))
        await session.delete(family)
    return True


async def run(args: argparse.Namespace) -> int:
    if not allowed():
        print(REFUSED)
        return 2
    sessions = get_sessionmaker()
    if args.member:
        link = await make_link(sessions, args.member, args.base_url)
        if link is None:
            print(REFUSED)
            return 2
        print(link)
    elif args.seed:
        print(json.dumps(await seed(sessions, args.base_url), ensure_ascii=False))
    elif args.add_step:
        added = await add_step(sessions, args.add_step, args.node)
        if added is None:
            print(REFUSED)
            return 2
        print(json.dumps(added))
    else:
        if not await cleanup(sessions, args.cleanup):
            print(REFUSED)
            return 2
        print("Đã dọn gia đình demo.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--member", type=UUID, help="id người giám hộ (gia đình demo): in liên kết đăng nhập")
    group.add_argument("--seed", action="store_true", help="dựng gia đình demo + sự cố + lượt chạy, in JSON")
    group.add_argument("--add-step", type=UUID, metavar="RUN_ID", help="chèn một bước agent_steps vào lượt demo")
    group.add_argument("--cleanup", type=UUID, metavar="FAMILY_ID", help="xóa gia đình demo và dữ liệu của nó")
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL, help="gốc web để dựng liên kết (mặc định localhost:3100)"
    )
    parser.add_argument("--node", default="risk_scorer", help="tên node cho --add-step")
    return asyncio.run(run(parser.parse_args(argv)))


if __name__ == "__main__":
    sys.exit(main())
