"""drills: bài diễn tập nhận biết lừa đảo (spec 028, P2-13)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-16

Bảng mới, không sửa bảng cũ. Không cột nào chứa văn bản tự do: `answers` chỉ là danh sách mã lựa chọn (một chữ cái) theo
bước. `score` chỉ có khi máy chủ đã chấm (passed/failed). CHECK khung giờ: 30 phút (bảo đảm máy hỏi được ít nhất một lần
theo nhịp heartbeat 15 phút) tới 4 giờ. Xóa gia đình hoặc thành viên thì xóa dây chuyền các bài diễn tập của họ.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATES = "'scheduled', 'offered', 'in_progress', 'passed', 'failed', 'aborted', 'declined', 'expired'"


def upgrade() -> None:
    op.create_table(
        "drills",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("member_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_by", sa.String(length=64), nullable=False),
        sa.Column("script_id", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'scheduled'"), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("offered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("debriefed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"status IN ({STATES})", name=op.f("ck_drills_status")),
        sa.CheckConstraint(
            "window_end > window_start AND window_end - window_start >= interval '30 minutes'"
            " AND window_end - window_start <= interval '4 hours'",
            name=op.f("ck_drills_window"),
        ),
        sa.CheckConstraint(
            "(status IN ('passed', 'failed')) = (score IS NOT NULL)", name=op.f("ck_drills_score_iff_graded")
        ),
        sa.CheckConstraint("score IS NULL OR (score >= 0 AND score <= 5)", name=op.f("ck_drills_score_range")),
        sa.CheckConstraint("answers IS NULL OR jsonb_typeof(answers) = 'array'", name=op.f("ck_drills_answers_array")),
        sa.ForeignKeyConstraint(
            ["family_id"], ["families.id"], name=op.f("fk_drills_family_id_families"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["member_id"], ["members.id"], name=op.f("fk_drills_member_id_members"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drills")),
    )
    op.create_index("ix_drills_family_window", "drills", ["family_id", "window_start"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_drills_family_window", table_name="drills")
    op.drop_table("drills")
