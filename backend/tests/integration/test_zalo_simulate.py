"""FR-012/T018: lệnh giả lập cập nhật Zalo đến (từ fixture hợp đồng) chạy đầu–cuối với MockZaloClient, không token."""

from typing import Any

import pytest

from hoicon.agents import texts
from hoicon.ops import zalo_simulate

pytestmark = pytest.mark.integration


async def test_simulated_start_pairs_and_prints_the_mock_reply(
    zalo_world: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    world = zalo_world
    code = await world.make_code()
    assert await zalo_simulate.run(f"/start {code}", user="fixture-user-sim", deps=world.deps) == 0
    out = capsys.readouterr().out
    (member,) = await world.members()
    assert member.guardian_rank == 1
    assert texts.pairing_confirmed() in out and "[mock]" in out
    assert code not in out  # mã ghép không được in lại
    assert "fixture-user-sim" not in out and "chat-of" not in out  # không in định danh


async def test_simulated_wrong_code_prints_the_generic_reply(
    zalo_world: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    world = zalo_world
    assert await zalo_simulate.run("/start 000000", user="fixture-user-sim", deps=world.deps) == 0
    assert texts.pairing_help() in capsys.readouterr().out
    assert await world.members() == []


async def test_only_fictional_users_are_accepted(zalo_world: Any, capsys: pytest.CaptureFixture[str]) -> None:
    world = zalo_world
    assert await zalo_simulate.run("1", user="6ede9afa66b88fe6d6a9", deps=world.deps) == 2  # trông như Zalo ID thật
    assert "fixture-" in capsys.readouterr().out
    assert world.client.sent == []


async def test_refuses_outside_dev(zalo_world: Any, capsys: pytest.CaptureFixture[str]) -> None:
    world = zalo_world
    prod = world.settings.model_copy(update={"env": "prod"})
    deps = type(world.deps)(world.deps.sessions, world.deps.client, prod)
    assert await zalo_simulate.run("1", user="fixture-user-sim", deps=deps) == 2
    assert world.client.sent == []


async def test_unusable_text_is_still_a_valid_update(zalo_world: Any, capsys: pytest.CaptureFixture[str]) -> None:
    world = zalo_world
    assert await zalo_simulate.run("xin chào", user="fixture-user-sim", deps=world.deps) == 0
    assert texts.pairing_help() in capsys.readouterr().out  # người chưa ghép nhắn linh tinh


def test_simulator_never_builds_a_live_client(monkeypatch: pytest.MonkeyPatch) -> None:
    from hoicon.channels.zalo import LiveZaloClient, MockZaloClient

    settings = zalo_simulate.get_settings().model_copy(update={"zalo_mode": "live"})
    assert isinstance(zalo_simulate.mock_deps(settings).client, MockZaloClient)
    assert not isinstance(zalo_simulate.mock_deps(settings).client, LiveZaloClient)
