"""case_files: hồ sơ vụ việc cho người giám hộ (spec 031, P2-16)

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-22

Một sự cố thật kết cục `case_open` có tối đa MỘT hồ sơ (UNIQUE `incident_id`). `content` chỉ là đúng
`docs/schemas/case_file.v1.json#/$defs/content`: dữ kiện máy chủ đã có, không số điện thoại đầy đủ/h1/HMAC/tên gói/lời kể.
Không có `is_drill`: diễn tập không bao giờ sinh hồ sơ. Xóa sự cố/gia đình ⇒ CASCADE; xóa thành viên duyệt ⇒ SET NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "case_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("summary_source", sa.String(length=16), server_default=sa.text("'template'"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'approved', 'sent', 'discarded')", name=op.f("ck_case_files_status")),
        sa.CheckConstraint("summary_source IN ('template', 'llm')", name=op.f("ck_case_files_summary_source")),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["incidents.id"], name=op.f("fk_case_files_incident_id_incidents"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["family_id"], ["families.id"], name=op.f("fk_case_files_family_id_families"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["members.id"], name=op.f("fk_case_files_approved_by_members"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_case_files")),
        sa.UniqueConstraint("incident_id", name=op.f("uq_case_files_incident_id")),
    )
    op.create_index("ix_case_files_family_created", "case_files", ["family_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_case_files_family_created", table_name="case_files")
    op.drop_table("case_files")
