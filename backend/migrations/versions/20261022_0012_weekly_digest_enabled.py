"""members.weekly_digest_enabled: người giám hộ tắt/bật bản tin tuần (spec 032, P2-17)

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-22

Cột theo NGƯỜI GIÁM HỘ (hai người trong một nhà có thể muốn khác nhau), mặc định bật. Tin "mất bảo vệ" không có cột tắt (an
toàn). Không bảng mới: chống trùng dựa vào khóa `jobs`/`messages_out`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "members", sa.Column("weekly_digest_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )


def downgrade() -> None:
    op.drop_column("members", "weekly_digest_enabled")
