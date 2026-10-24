"""booth_join_codes: mã tham gia gian trưng bày (spec 050 FR-007, T012)

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-24

Chỉ lưu HMAC của mã (không lưu mã thô). Mã sống ≤ 10 phút, ≤ 50 khách, bị thu hồi khi đặt lại gian. Không PII; dữ liệu
chỉ của gia đình demo. Dòng quá hạn bị job `retention` xóa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "booth_join_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("family_id", sa.Uuid(), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.CHAR(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_guests", sa.SmallInteger(), server_default=sa.text("50"), nullable=False),
        sa.Column("guests", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name="ck_booth_join_codes_hash_hex"),
        sa.CheckConstraint("max_guests BETWEEN 1 AND 50", name="ck_booth_join_codes_max_guests"),
        sa.CheckConstraint("guests >= 0 AND guests <= max_guests", name="ck_booth_join_codes_guests"),
        sa.UniqueConstraint("code_hash", name="uq_booth_join_codes_hash"),
    )
    op.create_index("ix_booth_join_codes_expires", "booth_join_codes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_booth_join_codes_expires", table_name="booth_join_codes")
    op.drop_table("booth_join_codes")
