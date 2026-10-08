"""baseline: extensions vector + pgcrypto

Revision ID: 0001
Revises:
Create Date: 2026-10-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    # Không gỡ extension: có thể đang được dùng ngoài phạm vi migration này.
    pass
