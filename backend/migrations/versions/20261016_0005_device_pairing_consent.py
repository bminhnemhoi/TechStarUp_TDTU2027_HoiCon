"""devices + consents (chỉ ghi thêm) + trusted_contacts + action_tokens (spec 020, P2-01)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-16

`consents` bất biến ở cấp CSDL: trigger `trg_consents_immutable` ném lỗi khi UPDATE/DELETE (mỗi dòng) và TRUNCATE
(mỗi câu lệnh). FK của `consents` là RESTRICT: xóa gia đình/thành viên không được kéo theo xóa bằng chứng đồng ý.
Không cột nào chứa số điện thoại/tên thật: chỉ băm (HMAC, SHA-256) + 3 số cuối.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PURPOSES = (
    "'core_protection', 'call_screening', 'usage_monitoring', 'overlay_pause', 'guardian_alerts',"
    " 'llm_processing', 'voice_input', 'drills', 'pilot_research'"
)


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=16), server_default=sa.text("'android'"), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=False),
        sa.Column("rules_version", sa.String(length=32), nullable=False),
        sa.Column("threat_list_version", sa.String(length=32), nullable=True),
        sa.Column("permission_state", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("fcm_token_enc", sa.Text(), nullable=True),
        sa.Column("device_secret_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("platform IN ('android', 'ios', 'web')", name=op.f("ck_devices_platform")),
        sa.CheckConstraint("device_secret_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_devices_secret_hash_hex")),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], name=op.f("fk_devices_family_id_families"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_devices_member_id_members"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("device_secret_hash", name="uq_devices_secret_hash"),
    )
    op.create_index("ix_devices_family", "devices", ["family_id"], unique=False)

    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("consent_version", sa.String(length=16), nullable=False),
        sa.Column("text_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"purpose IN ({PURPOSES})", name=op.f("ck_consents_purpose")),
        sa.CheckConstraint("channel IN ('app', 'zalo', 'web')", name=op.f("ck_consents_channel")),
        sa.CheckConstraint("text_sha256 ~ '^[0-9a-f]{64}$'", name=op.f("ck_consents_text_sha256_hex")),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], name=op.f("fk_consents_family_id_families"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_consents_member_id_members"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consents")),
    )
    op.create_index("ix_consents_member", "consents", ["member_id", "recorded_at"], unique=False)
    op.execute(
        """
        CREATE FUNCTION prevent_consent_tamper() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'consents is append-only: % is not allowed (rút đồng ý = ghi thêm dòng granted=false)', TG_OP
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_consents_immutable BEFORE UPDATE OR DELETE ON consents "
        "FOR EACH ROW EXECUTE FUNCTION prevent_consent_tamper()"
    )
    op.execute(
        "CREATE TRIGGER trg_consents_no_truncate BEFORE TRUNCATE ON consents "
        "FOR EACH STATEMENT EXECUTE FUNCTION prevent_consent_tamper()"
    )
    # ALWAYS: trigger vẫn chạy khi `session_replication_role = replica` (mặc định ORIGIN thì chế độ đó bỏ qua trigger).
    op.execute("ALTER TABLE consents ENABLE ALWAYS TRIGGER trg_consents_immutable")
    op.execute("ALTER TABLE consents ENABLE ALWAYS TRIGGER trg_consents_no_truncate")

    op.create_table(
        "trusted_contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("phone_hmac", sa.CHAR(length=64), nullable=False),
        sa.Column("phone_kid", sa.SmallInteger(), nullable=False),
        sa.Column("last3", sa.CHAR(length=3), nullable=True),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("phone_hmac ~ '^[0-9a-f]{64}$'", name=op.f("ck_trusted_contacts_phone_hmac_hex")),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], name=op.f("fk_trusted_contacts_family_id_families"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_trusted_contacts_member_id_members"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trusted_contacts")),
    )
    op.create_index("ix_trusted_contacts_hmac", "trusted_contacts", ["phone_kid", "phone_hmac"], unique=False)

    op.create_table(
        "action_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("scope IN ('incident_decision', 'guardian_view', 'drill_debrief')", name=op.f("ck_action_tokens_scope")),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_action_tokens_token_hash_hex")),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], name=op.f("fk_action_tokens_member_id_members"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_action_tokens")),
        sa.UniqueConstraint("token_hash", name="uq_action_tokens_token_hash"),
    )


def downgrade() -> None:
    # Hạ cấp xóa luôn bảng `consents` (DROP TABLE không bị trigger chặn) ⇒ không bao giờ làm khi còn bằng chứng.
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM consents)")).scalar():
        raise RuntimeError("consents còn dữ liệu: từ chối hạ cấp để không mất sổ đồng ý (Nghị định 356/2025)")
    op.drop_table("action_tokens")
    op.drop_index("ix_trusted_contacts_hmac", table_name="trusted_contacts")
    op.drop_table("trusted_contacts")
    op.execute("DROP TRIGGER trg_consents_no_truncate ON consents")
    op.execute("DROP TRIGGER trg_consents_immutable ON consents")
    op.execute("DROP FUNCTION prevent_consent_tamper()")
    op.drop_index("ix_consents_member", table_name="consents")
    op.drop_table("consents")
    op.drop_index("ix_devices_family", table_name="devices")
    op.drop_table("devices")
