"""hardening core: data_requests, tombstone families/members, chỉ mục cho job hạn lưu (spec 034, P2-20)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-16

`data_requests`: yêu cầu xóa dữ liệu của một gia đình. FK RESTRICT với `families` (vết pháp lý còn lại: gia đình bị xóa
chỉ được ẩn danh, không bị DELETE, vì `consents` giữ FK RESTRICT và là bằng chứng đồng ý theo Nghị định 356/2025). Không
cột nào chứa văn bản tự do. `families.deleted_at` / `members.deleted_at` đánh dấu tombstone đã ẩn danh. Chỉ mục
`agent_steps(at)` và `jobs(done_at)` phục vụ job `retention`; `risk_events(received_at)` đã có từ 0006.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), server_default=sa.text("'delete'"), nullable=False),
        sa.Column("requested_via", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('delete')", name=op.f("ck_data_requests_kind")),
        sa.CheckConstraint("requested_via IN ('ops', 'app', 'web')", name=op.f("ck_data_requests_requested_via")),
        sa.CheckConstraint("status IN ('pending', 'done', 'failed')", name=op.f("ck_data_requests_status")),
        sa.CheckConstraint(
            "(status = 'done') = (completed_at IS NOT NULL)", name=op.f("ck_data_requests_done_iff_completed")
        ),
        sa.ForeignKeyConstraint(
            ["family_id"], ["families.id"], name=op.f("fk_data_requests_family_id_families"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_requests")),
    )
    op.create_index("ix_data_requests_family", "data_requests", ["family_id"], unique=False)
    op.add_column("families", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("members", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_agent_steps_at", "agent_steps", ["at"], unique=False)
    op.create_index("ix_jobs_done_at", "jobs", ["done_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_done_at", table_name="jobs")
    op.drop_index("ix_agent_steps_at", table_name="agent_steps")
    op.drop_column("members", "deleted_at")
    op.drop_column("families", "deleted_at")
    op.drop_index("ix_data_requests_family", table_name="data_requests")
    op.drop_table("data_requests")
