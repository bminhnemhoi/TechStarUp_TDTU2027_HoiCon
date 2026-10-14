"""Mô hình ORM theo docs/DATA-MODEL.md (import tại đây để Alembic thấy). Bảng nghiệp vụ gia đình/sự cố: P2-01, P2-03."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hoicon.db.base import Base
from hoicon.db.ids import new_id


class Job(Base):
    """Hàng đợi job trong Postgres (ADR-004): bộ hẹn giờ T1/T2/T3, gửi tin, xóa theo hạn lưu. Lấy bằng SKIP LOCKED."""

    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_due", "run_at", postgresql_where=text("done_at IS NULL")),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    run_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # Chạy lại một node (vd. sau kill -9) không được tạo job trùng: INSERT … ON CONFLICT DO NOTHING theo khóa này.
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    attempts: Mapped[int] = mapped_column(server_default=text("0"))
    locked_at: Mapped[datetime | None]
    locked_by: Mapped[str | None] = mapped_column(String(64))
    done_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AgentRun(Base):
    """Một lần chạy đồ thị tác tử; checkpoint nằm ở bảng của AsyncPostgresSaver (khóa = thread_id)."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint("graph IN ('incident', 'coach')", name="graph"),
        CheckConstraint("status IN ('running', 'waiting', 'done', 'failed')", name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    # FK tới incidents thêm ở P2-03 (bảng chưa có).
    incident_id: Mapped[uuid.UUID | None]
    graph: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'running'"))
    thread_id: Mapped[str] = mapped_column(String(64), unique=True)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    finished_at: Mapped[datetime | None]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default=text("0"))
    is_drill: Mapped[bool] = mapped_column(server_default=text("false"))
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))


class AgentStep(Base):
    """Một bước của tác tử (đã che PII) — nguồn cho /trace. Nội dung giữ 30 ngày, số đo giữ lâu hơn (DATA-MODEL §6)."""

    __tablename__ = "agent_steps"
    __table_args__ = (Index("ix_agent_steps_run_at", "run_id", "at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"))
    node: Mapped[str] = mapped_column(String(64))
    model_profile: Mapped[str | None] = mapped_column(String(16))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    input_redacted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    latency_ms: Mapped[int] = mapped_column(server_default=text("0"))
    tokens_in: Mapped[int] = mapped_column(server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(server_default=text("0"))
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), server_default=text("0"))
    fallback_used: Mapped[bool] = mapped_column(server_default=text("false"))
    error: Mapped[str | None] = mapped_column(String(64))
    at: Mapped[datetime] = mapped_column(server_default=func.now())


__all__ = ["AgentRun", "AgentStep", "Base", "Job"]
