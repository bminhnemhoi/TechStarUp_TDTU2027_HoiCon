"""revoked_sessions: danh sách phiên web người giám hộ đã đăng xuất (spec 037 T018)

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-24

`DELETE /v1/guardian/session` ghi `jti` của token vào đây tới khi token hết hạn; `get_current_guardian` từ chối `jti` có
trong bảng. Chỉ mã phiên ngẫu nhiên, không PII. Dòng quá hạn bị job `retention` xóa.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "revoked_sessions",
        sa.Column("jti", sa.String(length=32), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_revoked_sessions_expires", "revoked_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_revoked_sessions_expires", table_name="revoked_sessions")
    op.drop_table("revoked_sessions")
