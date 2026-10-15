"""Mô hình ORM theo docs/DATA-MODEL.md (import tại đây để Alembic thấy). Gia đình/thành viên/mã ghép/tin gửi đi:
spec 002 (migration 0003, ADR-010). Bảng nghiệp vụ còn lại (thiết bị, đồng ý, sự cố…): spec 020, 021."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from hoicon.db.base import Base
from hoicon.db.ids import new_id


class Job(Base):
    """Hàng đợi job trong Postgres (ADR-004): bộ hẹn giờ T1/T2/T3, gửi tin, xóa theo hạn lưu. Lấy bằng SKIP LOCKED."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_due", "run_at", postgresql_where=text("done_at IS NULL")),
        # Đếm lần thử ghép Zalo và tin chữ theo thời gian (spec 002, migration 0003) không phải quét cả bảng.
        Index("ix_jobs_kind_created", "kind", "created_at"),
    )

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


class Family(Base):
    __tablename__ = "families"
    __table_args__ = (CheckConstraint("region IN ('bac', 'trung', 'nam')", name="region"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(64))  # bí danh do người dùng đặt, không phải tên thật
    region: Mapped[str] = mapped_column(String(8))
    plan: Mapped[str] = mapped_column(String(16), server_default=text("'free'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))


class Member(Base):
    """Người được bảo vệ hoặc người giám hộ. Zalo ID KHÔNG lưu thô (ADR-010 D1): `zalo_user_hmac` để tra cứu,
    `zalo_chat_enc` (AES-256-GCM) để gửi tin. Bốn cột Zalo cùng có hoặc cùng rỗng."""

    __tablename__ = "members"
    __table_args__ = (
        CheckConstraint("role IN ('protected', 'guardian')", name="role"),
        CheckConstraint(
            # IS NOT NULL tường minh: `NULL IN (1, 2)` là NULL và CHECK coi NULL là đạt
            "(role = 'guardian' AND guardian_rank IS NOT NULL AND guardian_rank IN (1, 2))"
            " OR (role = 'protected' AND guardian_rank IS NULL)",
            name="guardian_rank",
        ),
        CheckConstraint(
            "(zalo_bot_id IS NULL AND zalo_user_hmac IS NULL AND zalo_hmac_kid IS NULL AND zalo_chat_enc IS NULL)"
            " OR (zalo_bot_id IS NOT NULL AND zalo_user_hmac IS NOT NULL AND zalo_hmac_kid IS NOT NULL"
            " AND zalo_chat_enc IS NOT NULL)",
            name="zalo_all_or_none",
        ),
        UniqueConstraint("zalo_bot_id", "zalo_user_hmac", name="uq_members_zalo_account"),
        Index(
            "uq_members_guardian_rank",
            "family_id",
            "guardian_rank",
            unique=True,
            postgresql_where=text("role = 'guardian'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(16))
    alias: Mapped[str | None] = mapped_column(String(20))  # cách xưng hô ("Mẹ", "Bố"); không lưu tên thật
    address_form: Mapped[str | None] = mapped_column(String(32))
    guardian_rank: Mapped[int | None] = mapped_column(SmallInteger)
    zalo_bot_id: Mapped[str | None] = mapped_column(String(64))
    zalo_user_hmac: Mapped[str | None] = mapped_column(String(64))
    zalo_hmac_kid: Mapped[int | None] = mapped_column(SmallInteger)
    zalo_chat_enc: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(8), server_default=text("'vi'"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class PairingCode(Base):
    """Mã ghép Zalo 6 số: chỉ lưu băm, hết hạn 15 phút, dùng một lần (FR-003)."""

    __tablename__ = "pairing_codes"
    __table_args__ = (
        Index("uq_pairing_codes_unused", "code_hash", unique=True, postgresql_where=text("used_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    code_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]


class MessageOut(Base):
    """Mỗi tin gửi đi: nguồn của bộ đếm hạn mức theo bot/tháng và của việc gửi đúng một lần (`job_key` unique).
    `family_id` rỗng được: tin trả lời người chưa ghép vẫn tính vào hạn mức (ADR-010, điều chỉnh khi hiện thực)."""

    __tablename__ = "messages_out"
    __table_args__ = (
        CheckConstraint("channel IN ('zalo', 'push', 'web')", name="channel"),
        CheckConstraint("status IN ('queued', 'sent', 'held_quota', 'failed', 'fallback_required')", name="status"),
        Index("ix_messages_out_quota", "bot_id", "quota_month", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    # SET NULL (không CASCADE): xóa gia đình không được làm mất dòng đã gửi — bộ đếm hạn mức đếm trên bảng này.
    family_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("families.id", ondelete="SET NULL"))
    # FK tới incidents thêm ở spec 021 (bảng chưa có), như agent_runs.incident_id.
    incident_id: Mapped[uuid.UUID | None]
    member_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(8))
    bot_id: Mapped[str] = mapped_column(String(64))
    template_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))
    quota_month: Mapped[str] = mapped_column(String(7))  # "YYYY-MM" theo giờ Việt Nam
    sent_at: Mapped[datetime | None]
    error: Mapped[str | None] = mapped_column(String(64))
    job_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ThreatIndicator(Base):
    """Số điện thoại bị gắn cờ (spec 003, ADR-006): CHỈ `HMAC(pepper[kid], h1)` + 3 số cuối, không bao giờ lưu h1.
    Khóa duy nhất cũng là chỉ mục tra cứu (`lookup_h1`)."""

    __tablename__ = "threat_indicators"
    __table_args__ = (
        CheckConstraint("kind IN ('phone')", name="kind"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),
        CheckConstraint("value_hmac ~ '^[0-9a-f]{64}$'", name="hmac_hex"),
        UniqueConstraint("kind", "value_kid", "value_hmac", name="uq_threat_indicators_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(16))
    value_hmac: Mapped[str] = mapped_column(CHAR(64))
    value_kid: Mapped[int] = mapped_column(SmallInteger)
    last3: Mapped[str | None] = mapped_column(CHAR(3))
    source: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    tactic: Mapped[str | None] = mapped_column(String(64))
    list_version: Mapped[str] = mapped_column(String(32))
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))
    first_seen: Mapped[datetime] = mapped_column(server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime | None]


__all__ = [
    "AgentRun",
    "AgentStep",
    "Base",
    "Family",
    "Job",
    "Member",
    "MessageOut",
    "PairingCode",
    "ThreatIndicator",
]
