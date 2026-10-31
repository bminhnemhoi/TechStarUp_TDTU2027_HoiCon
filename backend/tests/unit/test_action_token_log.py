"""Spec 023: token `/a/[token]` không bao giờ vào log truy cập (chỉ lưu SHA-256)."""

import logging

from hoicon.api.routers.actions import RedactActionTokenFilter, redact_action_token

TOKEN = "Zm9vYmFyYmF6cXV4cXV1eGNvcmdlZ3JhdWx0Z2FycGx5"  # gitleaks:allow — chuỗi giả, dài như token thật


def test_redacts_view_and_decision_paths() -> None:
    assert redact_action_token(f"/v1/action/{TOKEN}") == "/v1/action/***"
    assert redact_action_token(f"/v1/action/{TOKEN}/decision?x=1") == "/v1/action/***/decision?x=1"
    assert redact_action_token("/v1/events") == "/v1/events"


def test_uvicorn_access_record_is_redacted_before_formatting() -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "POST", f"/v1/action/{TOKEN}/decision", "1.1", 200),
        None,
    )
    assert RedactActionTokenFilter().filter(record)
    assert TOKEN not in record.getMessage() and "/v1/action/***/decision" in record.getMessage()
    assert any(isinstance(f, RedactActionTokenFilter) for f in logging.getLogger("uvicorn.access").filters)
