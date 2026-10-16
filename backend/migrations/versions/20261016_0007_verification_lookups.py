"""verifications + threat_indicators.bucket_enc + consents.purpose += lookups (spec 026, P2-11, ADR-011)

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-16

`verifications` chỉ lưu `HMAC(pepper[kid], …)` của chủ thể (số điện thoại hoặc tên máy chủ của URL) + 3 số cuối của số;
không cột nào chứa số thô, h1 hay URL. Nó cũng là sổ đếm hạn mức của `POST /v1/lookups` (chỉ mục `(actor_id, at)`).
`threat_indicators.bucket_enc` là bucket 24 bit của h1 đã MÃ HÓA (AES-256-GCM, AAD gắn `value_hmac`), nullable: dòng cũ
chưa có bucket thì không xuống máy cho tới khi nạp lại tệp seed.

`consents` là sổ chỉ-ghi-thêm (trigger `trg_consents_immutable` chặn DELETE), nên hạ cấp KHÔNG xóa được các dòng
`lookups` đã có. CHECK cũ vì vậy được dựng lại bằng `NOT VALID`: dòng cũ giữ nguyên, nhưng không ghi thêm được mục đích
`lookups` mới. Nâng cấp lại thay CHECK bằng bản có `lookups` và kiểm toàn bộ dòng.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_PURPOSES = (
    "'core_protection', 'call_screening', 'usage_monitoring', 'overlay_pause', 'guardian_alerts',"
    " 'llm_processing', 'voice_input', 'drills', 'pilot_research'"
)
NEW_PURPOSES = f"{OLD_PURPOSES}, 'lookups'"


def upgrade() -> None:
    op.create_table(
        "verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("actor", sa.String(length=16), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("via", sa.String(length=8), nullable=False),
        sa.Column("subject_kid", sa.SmallInteger(), nullable=False),
        sa.Column("subject_hmac", sa.CHAR(length=64), nullable=False),
        sa.Column("last3", sa.CHAR(length=3), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("list_version", sa.String(length=32), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("actor IN ('device', 'guardian', 'system')", name=op.f("ck_verifications_actor")),
        sa.CheckConstraint("kind IN ('phone', 'url', 'account')", name=op.f("ck_verifications_kind")),
        sa.CheckConstraint("via IN ('typed', 'qr', 'call')", name=op.f("ck_verifications_via")),
        sa.CheckConstraint(
            "verdict IN ('safe', 'warning', 'dangerous', 'unknown')", name=op.f("ck_verifications_verdict")
        ),
        sa.CheckConstraint("subject_hmac ~ '^[0-9a-f]{64}$'", name=op.f("ck_verifications_subject_hmac_hex")),
        sa.CheckConstraint("last3 ~ '^[0-9]{3}$'", name=op.f("ck_verifications_last3")),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name=op.f("ck_verifications_confidence")),
        sa.ForeignKeyConstraint(
            ["family_id"], ["families.id"], name=op.f("fk_verifications_family_id_families"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.id"], name=op.f("fk_verifications_incident_id_incidents"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_verifications")),
    )
    op.create_index("ix_verifications_actor_at", "verifications", ["actor_id", "at"], unique=False)
    op.create_index("ix_verifications_incident", "verifications", ["incident_id"], unique=False)
    op.create_index(
        "uq_verifications_call",
        "verifications",
        ["incident_id", "kind", "subject_kid", "subject_hmac"],
        unique=True,
        postgresql_where=sa.text("via = 'call'"),
    )
    op.add_column("threat_indicators", sa.Column("bucket_enc", sa.String(length=128), nullable=True))
    op.drop_constraint(op.f("ck_consents_purpose"), "consents", type_="check")
    op.create_check_constraint(op.f("ck_consents_purpose"), "consents", f"purpose IN ({NEW_PURPOSES})")


def downgrade() -> None:
    op.drop_constraint(op.f("ck_consents_purpose"), "consents", type_="check")
    # NOT VALID: giữ nguyên dòng `lookups` đã có (sổ đồng ý không xóa được) nhưng chặn ghi thêm.
    op.execute(f"ALTER TABLE consents ADD CONSTRAINT ck_consents_purpose CHECK (purpose IN ({OLD_PURPOSES})) NOT VALID")
    op.drop_column("threat_indicators", "bucket_enc")
    op.drop_index("uq_verifications_call", table_name="verifications")
    op.drop_index("ix_verifications_incident", table_name="verifications")
    op.drop_index("ix_verifications_actor_at", table_name="verifications")
    op.drop_table("verifications")
