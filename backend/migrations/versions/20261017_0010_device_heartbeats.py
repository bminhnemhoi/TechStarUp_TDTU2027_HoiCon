"""device_heartbeats: một dòng mỗi khung 15 phút để đo độ phủ heartbeat (spec 029, P2-14)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-17

PK `(device_id, slot)`: `slot` là mốc 15 phút (CHECK chia hết 900 giây) nên tối đa 96 dòng/ngày/thiết bị. FK `CASCADE`
tới `devices` (xóa thiết bị/gia đình thì dòng đi theo). `protected` = mọi quyền lõi đều bật tại heartbeat đầu tiên của
khung. Không cột văn bản tự do, không định danh: chỉ id thiết bị, mốc giờ và một cờ.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_heartbeats",
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("slot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("protected", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "mod(extract(epoch from slot)::bigint, 900) = 0", name=op.f("ck_device_heartbeats_slot_15min")
        ),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.id"], name=op.f("fk_device_heartbeats_device_id_devices"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("device_id", "slot", name=op.f("pk_device_heartbeats")),
    )
    op.create_index("ix_device_heartbeats_slot", "device_heartbeats", ["slot"], unique=False)  # job hạn lưu


def downgrade() -> None:
    op.drop_index("ix_device_heartbeats_slot", table_name="device_heartbeats")
    op.drop_table("device_heartbeats")
