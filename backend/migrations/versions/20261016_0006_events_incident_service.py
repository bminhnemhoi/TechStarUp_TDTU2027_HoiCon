"""incidents + incident_transitions + risk_events; FK từ action_tokens/messages_out (spec 021, P2-03)

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-16

Hai bất biến của máy trạng thái nằm ở CSDL (DATA-MODEL §4), không chỉ ở `IncidentService`:
  1. `level >= rule_floor` — CHECK `ck_incidents_level_ge_floor` (LLM chỉ được NÂNG, không hạ dưới sàn luật).
  2. Trạng thái cuối (`resolved_*`, `closed`) không quay lại và chỉ-đọc (`state`, `level`, `rule_floor`, `outcome`,
     `closed_at`) — trigger `trg_incidents_terminal`; kèm CHECK `closed_at` có giá trị ⇔ đang ở trạng thái cuối.
`incident_transitions` không sửa/xóa trực tiếp được (xóa đi qua CASCADE khi sự cố cha bị xóa).
`risk_events` chỉ lưu `HMAC(pepper, h1)` + 3 số cuối (ADR-006), không cột nào có số điện thoại thô hay h1.

`action_tokens.incident_id` / `messages_out.incident_id` trước đây không có FK vì chưa có bảng `incidents`. Bảng mới
rỗng nên mọi giá trị cũ là mồ côi: token hành động gắn sự cố bị xóa (vô nghĩa nếu thiếu sự cố), `messages_out.incident_id`
nới về NULL (dòng vẫn giữ, bộ đếm hạn mức không đổi). Chỉ dữ liệu dev/demo; downgrade KHÔNG phục hồi các giá trị này.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATES = (
    "'detected', 'assessing', 'awaiting_guardian', 'verifying', 'rescore', 'resolved_safe', 'resolved_prevented',"
    " 'resolved_false_alarm', 'resolved_no_response', 'case_open', 'closed'"
)
TERMINAL = "'resolved_safe', 'resolved_prevented', 'resolved_false_alarm', 'resolved_no_response', 'closed'"
LEVELS = "'none', 'low', 'medium', 'high', 'critical'"


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("state", sa.String(length=24), server_default=sa.text("'detected'"), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("rule_floor", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_drill", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("drill_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("opened_by_event_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"state IN ({STATES})", name=op.f("ck_incidents_state")),
        sa.CheckConstraint("level IN ('low', 'medium', 'high', 'critical')", name=op.f("ck_incidents_level")),
        sa.CheckConstraint(f"rule_floor IN ({LEVELS})", name=op.f("ck_incidents_rule_floor")),
        sa.CheckConstraint(
            f"array_position(ARRAY[{LEVELS}], level) >= array_position(ARRAY[{LEVELS}], rule_floor)",
            name=op.f("ck_incidents_level_ge_floor"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_incidents_version")),
        sa.CheckConstraint("NOT is_drill OR drill_id IS NOT NULL", name=op.f("ck_incidents_drill_has_id")),
        sa.CheckConstraint(
            f"(closed_at IS NOT NULL) = (state IN ({TERMINAL}))", name=op.f("ck_incidents_closed_iff_terminal")
        ),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], name=op.f("fk_incidents_family_id_families"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_incidents_member_id_members"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name=op.f("fk_incidents_device_id_devices"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incidents")),
    )
    op.create_index("ix_incidents_family", "incidents", ["family_id", sa.text("opened_at DESC")], unique=False)
    op.create_index(
        "ix_incidents_open_device",
        "incidents",
        ["device_id"],
        unique=False,
        postgresql_where=sa.text(f"state NOT IN ({TERMINAL})"),
    )
    op.execute(
        f"""
        CREATE FUNCTION prevent_terminal_exit() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.state IN ({TERMINAL}) AND (
                NEW.state IS DISTINCT FROM OLD.state OR NEW.level IS DISTINCT FROM OLD.level
                OR NEW.rule_floor IS DISTINCT FROM OLD.rule_floor OR NEW.outcome IS DISTINCT FROM OLD.outcome
                OR NEW.closed_at IS DISTINCT FROM OLD.closed_at
            ) THEN
                RAISE EXCEPTION 'incident is in terminal state %: it is read-only (mở lại = sự cố mới)', OLD.state
                    USING ERRCODE = 'restrict_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_incidents_terminal BEFORE UPDATE ON incidents "
        "FOR EACH ROW EXECUTE FUNCTION prevent_terminal_exit()"
    )
    op.execute("ALTER TABLE incidents ENABLE ALWAYS TRIGGER trg_incidents_terminal")

    op.create_table(
        "incident_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("from_state", sa.String(length=24), nullable=True),
        sa.Column("to_state", sa.String(length=24), nullable=False),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"from_state IS NULL OR from_state IN ({STATES})", name=op.f("ck_incident_transitions_from_state")),
        sa.CheckConstraint(f"to_state IN ({STATES})", name=op.f("ck_incident_transitions_to_state")),
        sa.CheckConstraint(
            "actor IN ('device', 'agent', 'guardian', 'timer', 'system')", name=op.f("ck_incident_transitions_actor")
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.id"], name=op.f("fk_incident_transitions_incident_id_incidents"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_incident_transitions")),
    )
    op.create_index("ix_incident_transitions_incident", "incident_transitions", ["incident_id", "at"], unique=False)
    # Chặn UPDATE, và DELETE trực tiếp. DELETE do ON DELETE CASCADE (sự cố cha đã bị xóa) vẫn qua: quyền xóa dữ liệu.
    op.execute(
        """
        CREATE FUNCTION prevent_transition_update() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND NOT EXISTS (SELECT 1 FROM incidents WHERE id = OLD.incident_id) THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'incident_transitions is append-only: % is not allowed', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_incident_transitions_immutable BEFORE UPDATE OR DELETE ON incident_transitions "
        "FOR EACH ROW EXECUTE FUNCTION prevent_transition_update()"
    )
    op.execute("ALTER TABLE incident_transitions ENABLE ALWAYS TRIGGER trg_incident_transitions_immutable")

    op.create_table(
        "risk_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("rule_id", sa.String(length=8), nullable=True),
        sa.Column("rule_floor", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("caller_hmac", sa.CHAR(length=64), nullable=True),
        sa.Column("caller_kid", sa.SmallInteger(), nullable=True),
        sa.Column("caller_last3", sa.CHAR(length=3), nullable=True),
        sa.Column("caller_in_contacts", sa.Boolean(), nullable=True),
        sa.Column("call_duration_s", sa.Integer(), nullable=True),
        sa.Column("app_category", sa.String(length=16), nullable=True),
        sa.Column("app_package", sa.String(length=128), nullable=True),
        sa.Column("timing_detect_ms", sa.Integer(), nullable=True),
        sa.Column("timing_pause_ms", sa.Integer(), nullable=True),
        sa.Column("is_drill", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("drill_id", sa.Uuid(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.CheckConstraint(
            "type IN ('call_started', 'call_ended', 'flagged_number_call', 'risk_window_opened', 'risk_window_closed',"
            " 'banking_app_foreground', 'sideload_detected', 'safe_pause_shown', 'safe_pause_continued',"
            " 'safe_pause_cancelled', 'ask_child_pressed')",
            name=op.f("ck_risk_events_type"),
        ),
        sa.CheckConstraint("rule_id IS NULL OR rule_id IN ('R0', 'R1', 'R2', 'R4')", name=op.f("ck_risk_events_rule_id")),
        sa.CheckConstraint(f"rule_floor IN ({LEVELS})", name=op.f("ck_risk_events_rule_floor")),
        sa.CheckConstraint(
            "app_category IS NULL OR app_category IN ('bank', 'wallet', 'securities', 'sideloaded', 'other')",
            name=op.f("ck_risk_events_app_category"),
        ),
        sa.CheckConstraint("caller_hmac IS NULL OR caller_hmac ~ '^[0-9a-f]{64}$'", name=op.f("ck_risk_events_caller_hmac_hex")),
        sa.CheckConstraint("caller_last3 IS NULL OR caller_last3 ~ '^[0-9]{3}$'", name=op.f("ck_risk_events_caller_last3_digits")),
        sa.CheckConstraint(
            "(caller_hmac IS NULL) = (caller_kid IS NULL) AND (caller_hmac IS NULL) = (caller_last3 IS NULL)",
            name=op.f("ck_risk_events_caller_together"),
        ),
        sa.CheckConstraint("call_duration_s IS NULL OR call_duration_s >= 0", name=op.f("ck_risk_events_call_duration")),
        sa.CheckConstraint("timing_detect_ms IS NULL OR timing_detect_ms >= 0", name=op.f("ck_risk_events_timing_detect")),
        sa.CheckConstraint("timing_pause_ms IS NULL OR timing_pause_ms >= 0", name=op.f("ck_risk_events_timing_pause")),
        sa.CheckConstraint("NOT is_drill OR drill_id IS NOT NULL", name=op.f("ck_risk_events_drill_has_id")),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], name=op.f("fk_risk_events_family_id_families"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], name=op.f("fk_risk_events_device_id_devices"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], name=op.f("fk_risk_events_incident_id_incidents"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_events")),
    )
    op.create_index("ix_risk_events_device", "risk_events", ["device_id", "received_at"], unique=False)
    op.create_index("ix_risk_events_incident", "risk_events", ["incident_id"], unique=False)
    op.create_index("ix_risk_events_received", "risk_events", ["received_at"], unique=False)

    # Vòng tham chiếu incidents ↔ risk_events: FK này thêm sau khi cả hai bảng đã có.
    op.create_foreign_key(
        "fk_incidents_opened_by_event_id_risk_events",
        "incidents",
        "risk_events",
        ["opened_by_event_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.execute("DELETE FROM action_tokens WHERE incident_id IS NOT NULL")
    op.execute("UPDATE messages_out SET incident_id = NULL WHERE incident_id IS NOT NULL")
    op.create_foreign_key(
        "fk_action_tokens_incident_id_incidents", "action_tokens", "incidents", ["incident_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_messages_out_incident_id_incidents", "messages_out", "incidents", ["incident_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_out_incident_id_incidents", "messages_out", type_="foreignkey")
    op.drop_constraint("fk_action_tokens_incident_id_incidents", "action_tokens", type_="foreignkey")
    op.drop_constraint("fk_incidents_opened_by_event_id_risk_events", "incidents", type_="foreignkey")
    op.drop_index("ix_risk_events_received", table_name="risk_events")
    op.drop_index("ix_risk_events_incident", table_name="risk_events")
    op.drop_index("ix_risk_events_device", table_name="risk_events")
    op.drop_table("risk_events")
    op.drop_index("ix_incident_transitions_incident", table_name="incident_transitions")
    op.drop_table("incident_transitions")
    op.execute("DROP FUNCTION prevent_transition_update()")
    op.execute("DROP TRIGGER trg_incidents_terminal ON incidents")
    op.execute("DROP FUNCTION prevent_terminal_exit()")
    op.drop_index("ix_incidents_open_device", table_name="incidents")
    op.drop_index("ix_incidents_family", table_name="incidents")
    op.drop_table("incidents")
