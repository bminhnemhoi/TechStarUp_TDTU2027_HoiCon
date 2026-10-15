"""Hàm dùng chung của test eval (spec 030): chọn DB eval và chạy một danh sách ca."""

import os

from hoicon.config import get_settings
from hoicon.eval.cases import Case
from hoicon.eval.runner import CaseOutcome, run_suite


def eval_target() -> tuple[str, bool]:
    """(URL DB eval, shared_db_ok): DB riêng `HOICON_EVAL_DATABASE_URL`; không có ⇒ DB ứng dụng với cờ cho CI."""
    url = os.environ.get("HOICON_EVAL_DATABASE_URL")
    app_url = get_settings().database_url.get_secret_value()
    return (url, url == app_url) if url else (app_url, True)


async def run(target: tuple[str, bool], cases: list[Case]) -> list[CaseOutcome]:
    url, shared = target
    return await run_suite(cases, database_url=url, shared_db_ok=shared)
