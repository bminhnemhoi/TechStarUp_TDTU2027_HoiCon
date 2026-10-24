"""data_requests.execute_after + trạng thái 'cancelled' (spec 038 FR-006, T007)

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-25

Yêu cầu xóa từ app có khoảng chờ 24 giờ: `execute_after` là lúc purge bắt đầu; trong khoảng chờ người được bảo vệ hủy
được (`status = 'cancelled'`, `completed_at` vẫn NULL). Dòng cũ lấy `execute_after = requested_at` (đã/đang chạy ngay).
Không PII.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_requests", sa.Column("execute_after", sa.DateTime(timezone=True), nullable=True))
    op.execute("update data_requests set execute_after = requested_at")
    op.alter_column("data_requests", "execute_after", nullable=False, server_default=sa.func.now())
    op.drop_constraint(op.f("ck_data_requests_status"), "data_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_data_requests_status"), "data_requests", "status IN ('pending', 'done', 'failed', 'cancelled')"
    )


def downgrade() -> None:
    op.execute("update data_requests set status = 'failed' where status = 'cancelled'")
    op.drop_constraint(op.f("ck_data_requests_status"), "data_requests", type_="check")
    op.create_check_constraint(
        op.f("ck_data_requests_status"), "data_requests", "status IN ('pending', 'done', 'failed')"
    )
    op.drop_column("data_requests", "execute_after")
