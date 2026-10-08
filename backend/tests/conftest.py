import asyncio
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    # psycopg async không chạy trên ProactorEventLoop (mặc định của Windows). Linux vốn dùng SelectorEventLoop.
    # pytest-asyncio ≥ 1.4 bắt buộc hook trả về mapping khác rỗng (trả None ⇒ UsageError trên CI Linux).
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
