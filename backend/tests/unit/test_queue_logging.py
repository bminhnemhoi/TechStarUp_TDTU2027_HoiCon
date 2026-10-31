"""Spec 037 FR-005: log lỗi của job không mang thông điệp lỗi (SQLAlchemy nhúng cả tham số SQL ⇒ có thể lộ PII)."""

import logging
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from hoicon.jobs import queue

SENSITIVE = "0900000001"
MESSAGE = f"INSERT ... [parameters: ('{SENSITIVE}', 'Mẹ')]"  # như thông điệp lỗi của SQLAlchemy


async def test_a_failing_job_logs_the_error_class_and_frames_but_never_the_message(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    job = SimpleNamespace(id=uuid4(), kind="notify_guardian", payload={}, attempts=1)
    done: list[Any] = []

    async def claim(*_: Any) -> list[Any]:
        return [job]

    async def complete(_: Any, j: Any, error: str | None = None) -> None:
        done.append(error)

    async def handler(_: dict[str, Any]) -> None:
        raise RuntimeError(MESSAGE)

    monkeypatch.setattr(queue, "claim_due", claim)
    monkeypatch.setattr(queue, "complete", complete)
    with caplog.at_level(logging.INFO, logger=queue.logger.name):
        assert await queue.run_once(None, {"notify_guardian": handler}, "w") == 1  # type: ignore[arg-type]
    text = "\n".join(record.getMessage() + (record.exc_text or "") for record in caplog.records)
    assert "RuntimeError" in text and "notify_guardian" in text
    assert SENSITIVE not in text and "parameters" not in text
    assert all(record.exc_info is None for record in caplog.records)  # không có exc_info (kèm thông điệp lỗi)
    assert done == ["RuntimeError"]  # tên lớp lỗi vẫn ghi vào `jobs.error`
