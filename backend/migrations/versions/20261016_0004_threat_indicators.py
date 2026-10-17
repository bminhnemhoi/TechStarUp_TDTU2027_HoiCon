"""threat_indicators (spec 003, ADR-006: danh sách đe dọa chỉ lưu HMAC, không lưu h1)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16

Khóa duy nhất `(kind, value_kid, value_hmac)` đồng thời là chỉ mục tra cứu. Không có cột nào chứa h1 hay số điện thoại.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threat_indicators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value_hmac", sa.CHAR(length=64), nullable=False),
        sa.Column("value_kid", sa.SmallInteger(), nullable=False),
        sa.Column("last3", sa.CHAR(length=3), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("tactic", sa.String(length=64), nullable=True),
        sa.Column("list_version", sa.String(length=32), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('phone')", name=op.f("ck_threat_indicators_kind")),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name=op.f("ck_threat_indicators_confidence")),
        sa.CheckConstraint("value_hmac ~ '^[0-9a-f]{64}$'", name=op.f("ck_threat_indicators_hmac_hex")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_threat_indicators")),
        sa.UniqueConstraint("kind", "value_kid", "value_hmac", name="uq_threat_indicators_value"),
    )


def downgrade() -> None:
    op.drop_table("threat_indicators")
