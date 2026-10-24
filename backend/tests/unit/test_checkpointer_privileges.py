"""Spec 012 T017: role ứng dụng `hoicon_app` không có DDL (infra/postgres/roles.sql) vẫn mở được bộ lưu checkpoint."""

import pytest
from psycopg import errors as pg_errors

from hoicon.agents import runtime


class _Pool:
    async def __aenter__(self) -> "_Pool":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


async def test_a_role_without_ddl_rights_still_opens_the_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    async def denied(_: object) -> None:
        raise pg_errors.InsufficientPrivilege("permission denied for schema public")

    monkeypatch.setattr(runtime, "AsyncConnectionPool", lambda *a, **k: _Pool())
    monkeypatch.setattr(runtime.AsyncPostgresSaver, "setup", denied)
    async with runtime.open_checkpointer("postgresql+psycopg://x/y") as saver:
        assert isinstance(saver, runtime.AsyncPostgresSaver)


async def test_any_other_setup_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def broken(_: object) -> None:
        raise pg_errors.OperationalError("connection refused")

    monkeypatch.setattr(runtime, "AsyncConnectionPool", lambda *a, **k: _Pool())
    monkeypatch.setattr(runtime.AsyncPostgresSaver, "setup", broken)
    with pytest.raises(pg_errors.OperationalError):
        async with runtime.open_checkpointer("postgresql+psycopg://x/y"):
            pass
