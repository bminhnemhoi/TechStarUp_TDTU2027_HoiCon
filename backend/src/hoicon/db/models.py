"""Mô hình ORM theo docs/DATA-MODEL.md (import tại đây để Alembic thấy). Gia đình/thành viên/mã ghép/tin gửi đi:
spec 002 (migration 0003, ADR-010). Thiết bị, sổ đồng ý, liên hệ tin cậy, action token: spec 020 (migration 0005).
Sự cố, chuyển trạng thái, sự kiện rủi ro: spec 021 (migration 0006). Xác minh/tra cứu: spec 026 (migration 0007).
Diễn tập: spec 028 (migration 0008). Gia cố lõi (yêu cầu xóa, tombstone): spec 034 (migration 0009)."""

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
        Index("ix_jobs_done_at", "done_at"),  # job `retention` (30 ngày sau done_at), spec 034
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
    __table_args__ = (
        Index("ix_agent_steps_run_at", "run_id", "at"),
        Index("ix_agent_steps_at", "at"),  # job `retention` (làm rỗng nội dung sau 30 ngày), spec 034
    )

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
    deleted_at: Mapped[datetime | None]  # tombstone sau yêu cầu xóa (spec 034): dòng còn nhưng đã ẩn danh


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
    weekly_digest_enabled: Mapped[bool] = mapped_column(
        server_default=text("true")
    )  # spec 032: bản tin tuần, theo người
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    deleted_at: Mapped[datetime | None]  # tombstone sau yêu cầu xóa (spec 034)


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
    # SET NULL: xóa sự cố không được làm mất dòng đã gửi (bộ đếm hạn mức). `agent_runs.incident_id` vẫn chưa có FK.
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
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
    # Spec 026, ADR-011: bucket 24 bit của h1, MÃ HÓA (AES-256-GCM, AAD gắn `value_hmac`). Không bao giờ lưu dạng rõ.
    bucket_enc: Mapped[str | None] = mapped_column(String(128))


class Device(Base):
    """Máy của người được bảo vệ, tạo khi ghép đôi (spec 020). Bí mật làm mới chỉ lưu băm SHA-256."""

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("platform IN ('android', 'ios', 'web')", name="platform"),
        CheckConstraint("device_secret_hash ~ '^[0-9a-f]{64}$'", name="secret_hash_hex"),
        UniqueConstraint("device_secret_hash", name="uq_devices_secret_hash"),
        Index("ix_devices_family", "family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    platform: Mapped[str] = mapped_column(String(16), server_default=text("'android'"))
    label: Mapped[str | None] = mapped_column(String(64))  # bí danh máy do người dùng đặt, không chứa PII
    app_version: Mapped[str] = mapped_column(String(32))
    rules_version: Mapped[str] = mapped_column(String(32))
    threat_list_version: Mapped[str | None] = mapped_column(String(32))
    permission_state: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    fcm_token_enc: Mapped[str | None] = mapped_column(Text)
    device_secret_hash: Mapped[str] = mapped_column(CHAR(64))
    last_heartbeat_at: Mapped[datetime] = mapped_column(server_default=func.now())
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Consent(Base):
    """Sổ đồng ý CHỈ GHI THÊM: trigger `trg_consents_immutable` chặn UPDATE/DELETE/TRUNCATE (Nghị định 356/2025).
    Rút đồng ý = thêm dòng `granted = false`. FK dùng RESTRICT: xóa gia đình không được kéo theo xóa bằng chứng."""

    __tablename__ = "consents"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('core_protection', 'call_screening', 'usage_monitoring', 'overlay_pause', 'guardian_alerts',"
            " 'llm_processing', 'voice_input', 'drills', 'pilot_research', 'lookups')",
            name="purpose",
        ),
        CheckConstraint("channel IN ('app', 'zalo', 'web')", name="channel"),
        CheckConstraint("text_sha256 ~ '^[0-9a-f]{64}$'", name="text_sha256_hex"),
        Index("ix_consents_member", "member_id", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="RESTRICT"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="RESTRICT"))
    purpose: Mapped[str] = mapped_column(String(32))
    granted: Mapped[bool]
    consent_version: Mapped[str] = mapped_column(String(16))
    text_sha256: Mapped[str] = mapped_column(CHAR(64))
    channel: Mapped[str] = mapped_column(String(16))
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TrustedContact(Base):
    """Liên hệ tin cậy (R0: không cảnh báo). CHỈ HMAC + 3 số cuối, không số thô (ADR-006)."""

    __tablename__ = "trusted_contacts"
    __table_args__ = (
        CheckConstraint("phone_hmac ~ '^[0-9a-f]{64}$'", name="phone_hmac_hex"),
        Index("ix_trusted_contacts_hmac", "phone_kid", "phone_hmac"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    phone_hmac: Mapped[str] = mapped_column(CHAR(64))
    phone_kid: Mapped[int] = mapped_column(SmallInteger)
    last3: Mapped[str | None] = mapped_column(CHAR(3))
    label: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ActionToken(Base):
    """Liên kết hành động một lần (`/a/[token]`): chỉ lưu băm. Xóa sự cố ⇒ token mất theo (vô nghĩa nếu thiếu sự cố)."""

    __tablename__ = "action_tokens"
    __table_args__ = (
        CheckConstraint("scope IN ('incident_decision', 'guardian_view', 'drill_debrief')", name="scope"),
        CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name="token_hash_hex"),
        UniqueConstraint("token_hash", name="uq_action_tokens_token_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64))
    scope: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


INCIDENT_STATES = (
    "'detected', 'assessing', 'awaiting_guardian', 'verifying', 'rescore', 'resolved_safe', 'resolved_prevented',"
    " 'resolved_false_alarm', 'resolved_no_response', 'case_open', 'closed'"
)
TERMINAL_STATES = "'resolved_safe', 'resolved_prevented', 'resolved_false_alarm', 'resolved_no_response', 'closed'"
RISK_LEVELS = "'none', 'low', 'medium', 'high', 'critical'"


class Incident(Base):
    """Sự cố (spec 021, DATA-MODEL §4). Mọi đổi `state` đi qua `IncidentService.transition()`. Hai bất biến nằm ở CSDL:
    `level >= rule_floor` (CHECK) và trạng thái cuối không quay lại, chỉ-đọc (trigger `trg_incidents_terminal`)."""

    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(f"state IN ({INCIDENT_STATES})", name="state"),
        CheckConstraint("level IN ('low', 'medium', 'high', 'critical')", name="level"),
        CheckConstraint(f"rule_floor IN ({RISK_LEVELS})", name="rule_floor"),
        CheckConstraint(
            f"array_position(ARRAY[{RISK_LEVELS}], level) >= array_position(ARRAY[{RISK_LEVELS}], rule_floor)",
            name="level_ge_floor",
        ),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("NOT is_drill OR drill_id IS NOT NULL", name="drill_has_id"),
        CheckConstraint(f"(closed_at IS NOT NULL) = (state IN ({TERMINAL_STATES}))", name="closed_iff_terminal"),
        Index("ix_incidents_family", "family_id", text("opened_at DESC")),
        Index(
            "ix_incidents_open_device",
            "device_id",
            postgresql_where=text(f"state NOT IN ({TERMINAL_STATES})"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    device_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("devices.id", ondelete="SET NULL"))
    state: Mapped[str] = mapped_column(String(24), server_default=text("'detected'"))
    level: Mapped[str] = mapped_column(String(16))
    rule_floor: Mapped[str] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(server_default=text("1"))  # khóa lạc quan
    is_drill: Mapped[bool] = mapped_column(server_default=text("false"))
    drill_id: Mapped[uuid.UUID | None]
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))
    # SET NULL: sự kiện có hạn lưu ngắn hơn sự cố (90 ngày so với 12 tháng).
    opened_by_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "risk_events.id", ondelete="SET NULL", use_alter=True, name="fk_incidents_opened_by_event_id_risk_events"
        )
    )
    outcome: Mapped[str | None] = mapped_column(String(32))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None]


class IncidentTransition(Base):
    """Nhật ký mọi chuyển trạng thái của sự cố (chỉ thêm dòng; trigger chặn UPDATE)."""

    __tablename__ = "incident_transitions"
    __table_args__ = (
        CheckConstraint(f"from_state IS NULL OR from_state IN ({INCIDENT_STATES})", name="from_state"),
        CheckConstraint(f"to_state IN ({INCIDENT_STATES})", name="to_state"),
        CheckConstraint("actor IN ('device', 'agent', 'guardian', 'timer', 'system')", name="actor"),
        Index("ix_incident_transitions_incident", "incident_id", "at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    from_state: Mapped[str | None] = mapped_column(String(24))
    to_state: Mapped[str] = mapped_column(String(24))
    actor: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(
        String(256)
    )  # mã ngắn do máy chủ đặt, không văn bản tự do của người dùng
    at: Mapped[datetime] = mapped_column(server_default=func.now())


class RiskEventRecord(Base):
    """Sự kiện rủi ro từ app Lính gác (`risk_event.v1.json`): CHỈ siêu dữ liệu. Số gọi đến chỉ có `HMAC(pepper, h1)` +
    3 số cuối (ADR-006), KHÔNG lưu h1. `id` do máy sinh (UUIDv7) ⇒ khóa chính cũng là khóa chống trùng."""

    __tablename__ = "risk_events"
    __table_args__ = (
        CheckConstraint(
            "type IN ('call_started', 'call_ended', 'flagged_number_call', 'risk_window_opened', 'risk_window_closed',"
            " 'banking_app_foreground', 'sideload_detected', 'safe_pause_shown', 'safe_pause_continued',"
            " 'safe_pause_cancelled', 'ask_child_pressed')",
            name="type",
        ),
        CheckConstraint("rule_id IS NULL OR rule_id IN ('R0', 'R1', 'R2', 'R4')", name="rule_id"),
        CheckConstraint(f"rule_floor IN ({RISK_LEVELS})", name="rule_floor"),
        CheckConstraint(
            "app_category IS NULL OR app_category IN ('bank', 'wallet', 'securities', 'sideloaded', 'other')",
            name="app_category",
        ),
        CheckConstraint("caller_hmac IS NULL OR caller_hmac ~ '^[0-9a-f]{64}$'", name="caller_hmac_hex"),
        CheckConstraint("caller_last3 IS NULL OR caller_last3 ~ '^[0-9]{3}$'", name="caller_last3_digits"),
        CheckConstraint(
            "(caller_hmac IS NULL) = (caller_kid IS NULL) AND (caller_hmac IS NULL) = (caller_last3 IS NULL)",
            name="caller_together",
        ),
        CheckConstraint("call_duration_s IS NULL OR call_duration_s >= 0", name="call_duration"),
        CheckConstraint("timing_detect_ms IS NULL OR timing_detect_ms >= 0", name="timing_detect"),
        CheckConstraint("timing_pause_ms IS NULL OR timing_pause_ms >= 0", name="timing_pause"),
        CheckConstraint("NOT is_drill OR drill_id IS NOT NULL", name="drill_has_id"),
        Index("ix_risk_events_device", "device_id", "received_at"),
        Index("ix_risk_events_incident", "incident_id"),
        Index("ix_risk_events_received", "received_at"),  # job `retention` (90 ngày)
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)  # UUIDv7 do máy sinh, KHÔNG default
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"))
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(32))
    rule_id: Mapped[str | None] = mapped_column(String(8))
    rule_floor: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime]  # giờ máy (UTC)
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    caller_hmac: Mapped[str | None] = mapped_column(CHAR(64))
    caller_kid: Mapped[int | None] = mapped_column(SmallInteger)
    caller_last3: Mapped[str | None] = mapped_column(CHAR(3))
    caller_in_contacts: Mapped[bool | None]
    call_duration_s: Mapped[int | None]
    app_category: Mapped[str | None] = mapped_column(String(16))
    app_package: Mapped[str | None] = mapped_column(String(128))  # chỉ gói trong danh sách ngân hàng, không phải PII
    timing_detect_ms: Mapped[int | None]
    timing_pause_ms: Mapped[int | None]
    is_drill: Mapped[bool] = mapped_column(server_default=text("false"))
    drill_id: Mapped[uuid.UUID | None]
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )  # sự kiện đã BỎ caller.h1


__all__ = [
    "ActionToken",
    "AgentRun",
    "AgentStep",
    "Base",
    "Consent",
    "Device",
    "Family",
    "Incident",
    "IncidentTransition",
    "Job",
    "Member",
    "MessageOut",
    "PairingCode",
    "RiskEventRecord",
    "ThreatIndicator",
    "TrustedContact",
]


class Verification(Base):
    """Kết quả tra cứu/xác minh một số điện thoại hoặc đường link (spec 026, P2-11). CHỈ HMAC của chủ thể
    (`HMAC(pepper[kid], …)`) + 3 số cuối của số; không cột nào chứa số thô, h1 hay URL. Đồng thời là sổ đếm hạn mức
    `POST /v1/lookups` (chỉ mục `(actor_id, at)`). Giữ 90 ngày như sự cố (job retention, P2-20)."""

    __tablename__ = "verifications"
    __table_args__ = (
        CheckConstraint("actor IN ('device', 'guardian', 'system')", name="actor"),
        CheckConstraint("kind IN ('phone', 'url', 'account')", name="kind"),
        CheckConstraint("via IN ('typed', 'qr', 'call')", name="via"),
        CheckConstraint("verdict IN ('safe', 'warning', 'dangerous', 'unknown')", name="verdict"),
        CheckConstraint("subject_hmac ~ '^[0-9a-f]{64}$'", name="subject_hmac_hex"),
        CheckConstraint("last3 ~ '^[0-9]{3}$'", name="last3"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence"),
        Index("ix_verifications_actor_at", "actor_id", "at"),
        Index("ix_verifications_incident", "incident_id"),
        # Ghi số gọi đến lũy đẳng: mỗi (sự cố, chủ thể) một dòng `via = 'call'`.
        Index(
            "uq_verifications_call",
            "incident_id",
            "kind",
            "subject_kid",
            "subject_hmac",
            unique=True,
            postgresql_where=text("via = 'call'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    incident_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    actor: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None]  # devices.id | members.id; NULL khi actor = system
    kind: Mapped[str] = mapped_column(String(16))
    via: Mapped[str] = mapped_column(String(8))
    subject_kid: Mapped[int] = mapped_column(SmallInteger)
    subject_hmac: Mapped[str] = mapped_column(CHAR(64))
    last3: Mapped[str | None] = mapped_column(CHAR(3))  # chỉ kind = phone
    verdict: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    list_version: Mapped[str | None] = mapped_column(String(32))
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))
    at: Mapped[datetime] = mapped_column(server_default=func.now())


DRILL_STATES = "'scheduled', 'offered', 'in_progress', 'passed', 'failed', 'aborted', 'declined', 'expired'"


class Drill(Base):
    """Một bài diễn tập đã đặt lịch cho một người cao tuổi (spec 028, P2-13, DATA-MODEL §Drills). Cờ diễn tập CHỈ do
    máy chủ cấp (FR-003): `POST /v1/events` chỉ tin `drill_id` khớp một dòng `in_progress` của chính gia đình, trong
    khung giờ. Không cột nào chứa văn bản tự do: `answers` chỉ là mã lựa chọn (một chữ cái) theo từng bước. Mọi đổi
    `status` đi qua `DrillService` (bảng cạnh `ALLOWED`); trạng thái cuối không có cạnh đi ra."""

    __tablename__ = "drills"
    __table_args__ = (
        CheckConstraint(f"status IN ({DRILL_STATES})", name="status"),
        # 30 phút bảo đảm máy hỏi được ít nhất một lần theo nhịp heartbeat 15 phút; 4 giờ chặn khung mở quá lâu.
        CheckConstraint(
            "window_end > window_start AND window_end - window_start >= interval '30 minutes'"
            " AND window_end - window_start <= interval '4 hours'",
            name="window",
        ),
        # Điểm (số bước đúng) chỉ có khi máy chủ đã chấm xong: passed/failed.
        CheckConstraint("(status IN ('passed', 'failed')) = (score IS NOT NULL)", name="score_iff_graded"),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 5)", name="score_range"),
        CheckConstraint("answers IS NULL OR jsonb_typeof(answers) = 'array'", name="answers_array"),
        Index("ix_drills_family_window", "family_id", "window_start"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))  # người cao tuổi
    scheduled_by: Mapped[str] = mapped_column(String(64))  # id thành viên đặt lịch, hoặc "ops"
    script_id: Mapped[str] = mapped_column(String(64))  # id kịch bản trong data/drills (không phải khóa ngoại)
    window_start: Mapped[datetime]
    window_end: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(24), server_default=text("'scheduled'"))
    score: Mapped[int | None] = mapped_column(SmallInteger)
    answers: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)  # [{"step": 0, "choice_id": "b"}]; chỉ mã
    offered_at: Mapped[datetime | None]
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    debriefed_at: Mapped[datetime | None]
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class DataRequest(Base):
    """Yêu cầu xóa dữ liệu của một gia đình (spec 034, US-20.2). FK RESTRICT: vết pháp lý còn lại sau khi xóa. Không cột
    văn bản tự do: `error_code` là mã ngắn do máy chủ đặt."""

    __tablename__ = "data_requests"
    __table_args__ = (
        CheckConstraint("kind IN ('delete')", name="kind"),
        CheckConstraint("requested_via IN ('ops', 'app', 'web')", name="requested_via"),
        CheckConstraint("status IN ('pending', 'done', 'failed')", name="status"),
        CheckConstraint("(status = 'done') = (completed_at IS NOT NULL)", name="done_iff_completed"),
        Index("ix_data_requests_family", "family_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(16), server_default=text("'delete'"))
    requested_via: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'pending'"))
    error_code: Mapped[str | None] = mapped_column(String(32))
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None]


class DeviceHeartbeat(Base):
    """Một dòng mỗi khung 15 phút có heartbeat (spec 029, FR-003): đo độ phủ Gate M2. Không văn bản tự do, không PII.
    `protected` = mọi quyền lõi (vai trò sàng lọc cuộc gọi, quyền xem mức dùng app) đều bật. Xóa thiết bị ⇒ CASCADE."""

    __tablename__ = "device_heartbeats"
    __table_args__ = (
        CheckConstraint("mod(extract(epoch from slot)::bigint, 900) = 0", name="slot_15min"),
        Index("ix_device_heartbeats_slot", "slot"),
    )

    device_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    slot: Mapped[datetime] = mapped_column(primary_key=True)
    protected: Mapped[bool]


class RevokedSession(Base):
    """Phiên web người giám hộ đã đăng xuất (spec 037 T018): `jti` của token tới khi nó hết hạn. Không PII."""

    __tablename__ = "revoked_sessions"
    __table_args__ = (Index("ix_revoked_sessions_expires", "expires_at"),)

    jti: Mapped[str] = mapped_column(String(32), primary_key=True)
    expires_at: Mapped[datetime]


class CaseFile(Base):
    """Hồ sơ vụ việc cho người giám hộ (spec 031): bản nháp dựng TẤT ĐỊNH từ dữ kiện máy chủ đã có khi sự cố thật kết
    cục `case_open`. `content` = đúng `case_file.v1#/$defs/content` (không PII). Không `is_drill`: diễn tập không có hồ
    sơ."""

    __tablename__ = "case_files"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved', 'sent', 'discarded')", name="status"),
        CheckConstraint("summary_source IN ('template', 'llm')", name="summary_source"),
        UniqueConstraint("incident_id", name="uq_case_files_incident_id"),
        Index("ix_case_files_family_created", "family_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_id)
    incident_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), server_default=text("'draft'"))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)
    summary_source: Mapped[str] = mapped_column(String(16), server_default=text("'template'"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None]
    sent_at: Mapped[datetime | None]
    discarded_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    is_demo: Mapped[bool] = mapped_column(server_default=text("false"))
