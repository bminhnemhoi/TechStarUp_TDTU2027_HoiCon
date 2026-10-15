"""Giả lập MỘT cập nhật Zalo đến, chạy đầu–cuối trong tiến trình này với `MockZaloClient` (không token, không gọi mạng):

    uv run --directory backend python -m hoicon.ops.zalo_simulate "/start 482913"
    uv run --directory backend python -m hoicon.ops.zalo_simulate 1 --user fixture-user-0001

Dựng cập nhật từ fixture hợp đồng (docs/schemas/fixtures/zalo_update.v1.valid.json), qua đúng đường của webhook
(`parse_update` → `build_job_payload`) rồi `handle_update`. Ghi vào Postgres dev thật (ghép người giám hộ,
`messages_out`) nên chỉ chạy khi `HOICON_ENV=dev` và chỉ nhận người dùng hư cấu (`fixture-…`).
KHÔNG bao giờ gửi tin thật: luôn dùng mock, kể cả khi `HOICON_ZALO_MODE=live`.
Tạo mã ghép: `python -m hoicon.ops.pairing_code --family <tên>`.
"""

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any

from hoicon.agents.incident_graph import Deps
from hoicon.agents.llm_router import LlmRouter
from hoicon.agents.runtime import IncidentRuntime
from hoicon.channels.guardian import ChannelDeps
from hoicon.channels.inbound import build_job_payload, parse_update
from hoicon.channels.updates import handle_update
from hoicon.channels.zalo import MockZaloClient
from hoicon.config import Settings, get_settings
from hoicon.db.ids import new_id
from hoicon.db.session import get_sessionmaker

FIXTURE = Path(__file__).resolve().parents[4] / "docs" / "schemas" / "fixtures" / "zalo_update.v1.valid.json"
USER_PREFIX = "fixture-"


def mock_deps(settings: Settings) -> ChannelDeps:
    return ChannelDeps(get_sessionmaker(), MockZaloClient(), settings)


def build_update(text: str, user: str, message_id: str) -> dict[str, Any]:
    template = next(u for u in json.loads(FIXTURE.read_text(encoding="utf-8")) if u["_name"] == "text_reply_1")
    update = {k: v for k, v in template.items() if k != "_name"}
    message = update["result"]["message"]
    message.update(text=text, message_id=message_id)
    message["from"]["id"] = user
    message["chat"]["id"] = f"chat-of-{user}"
    return update


async def run(
    text: str, *, user: str = "fixture-user-0001", message_id: str | None = None, deps: ChannelDeps | None = None
) -> int:
    settings = deps.settings if deps else get_settings()
    if settings.env != "dev":
        print("Từ chối: chỉ chạy được khi HOICON_ENV=dev.")
        return 2
    if not user.startswith(USER_PREFIX):
        print(f"Từ chối: --user phải là người dùng hư cấu, bắt đầu bằng '{USER_PREFIX}' (không nhập Zalo ID thật).")
        return 2
    deps = deps or mock_deps(settings)
    client = deps.client
    parsed = parse_update(build_update(text, user, message_id or f"fixture-msg-{new_id().hex[:12]}"))
    if parsed is None:
        print("Cập nhật giả lập không dùng được.")
        return 1
    payload = build_job_payload(settings.zalo_bot_id, parsed)
    async with contextlib.AsyncExitStack() as stack:
        runtime = None
        if payload["kind"] == "choice":  # trả lời 1/2/3 cần đồ thị sự cố để chạy tiếp
            runtime_deps = Deps(LlmRouter.from_settings(sessions=deps.sessions), deps.sessions, settings)
            runtime = await stack.enter_async_context(IncidentRuntime.open(runtime_deps))
        before = len(getattr(client, "sent", []))
        status = await handle_update(deps, runtime, payload)
    print(f"Cập nhật giả lập: loại={payload['kind']} · trả lời: {status}")
    for sent in getattr(client, "sent", [])[before:]:
        print(f"[mock] Tin trả lời người giám hộ: {sent.text}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", help='nội dung tin người giám hộ nhắn, vd. "/start 482913" hoặc 1')
    parser.add_argument("--user", default="fixture-user-0001", help="người dùng hư cấu, bắt đầu bằng 'fixture-'")
    args = parser.parse_args(argv)
    return asyncio.run(run(args.text, user=args.user), loop_factory=asyncio.SelectorEventLoop)


if __name__ == "__main__":
    sys.exit(main())
