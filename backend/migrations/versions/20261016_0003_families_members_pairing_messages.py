"""families + members + pairing_codes + messages_out (spec 002, ADR-010 D2: ghép Zalo, tin gửi đi, hạn mức)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16

Không đụng bảng checkpoint của LangGraph (do `AsyncPostgresSaver.setup()` tự tạo, ngoài Alembic).
Cột Zalo của `members` theo D1: `zalo_user_hmac` (tra cứu) + `zalo_chat_enc` (AES-256-GCM, để gửi); không có Zalo ID thô.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('families',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('display_name', sa.String(length=64), nullable=False),
    sa.Column('region', sa.String(length=8), nullable=False),
    sa.Column('plan', sa.String(length=16), server_default=sa.text("'free'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("region IN ('bac', 'trung', 'nam')", name=op.f('ck_families_region')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_families'))
    )
    op.create_table('members',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('alias', sa.String(length=20), nullable=True),
    sa.Column('address_form', sa.String(length=32), nullable=True),
    sa.Column('guardian_rank', sa.SmallInteger(), nullable=True),
    sa.Column('zalo_bot_id', sa.String(length=64), nullable=True),
    sa.Column('zalo_user_hmac', sa.String(length=64), nullable=True),
    sa.Column('zalo_hmac_kid', sa.SmallInteger(), nullable=True),
    sa.Column('zalo_chat_enc', sa.Text(), nullable=True),
    sa.Column('locale', sa.String(length=8), server_default=sa.text("'vi'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(role = 'guardian' AND guardian_rank IS NOT NULL AND guardian_rank IN (1, 2)) OR (role = 'protected' AND guardian_rank IS NULL)", name=op.f('ck_members_guardian_rank')),
    sa.CheckConstraint("role IN ('protected', 'guardian')", name=op.f('ck_members_role')),
    sa.CheckConstraint('(zalo_bot_id IS NULL AND zalo_user_hmac IS NULL AND zalo_hmac_kid IS NULL AND zalo_chat_enc IS NULL) OR (zalo_bot_id IS NOT NULL AND zalo_user_hmac IS NOT NULL AND zalo_hmac_kid IS NOT NULL AND zalo_chat_enc IS NOT NULL)', name=op.f('ck_members_zalo_all_or_none')),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_members_family_id_families'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_members')),
    sa.UniqueConstraint('zalo_bot_id', 'zalo_user_hmac', name='uq_members_zalo_account')
    )
    op.create_index('uq_members_guardian_rank', 'members', ['family_id', 'guardian_rank'], unique=True, postgresql_where=sa.text("role = 'guardian'"))
    op.create_table('pairing_codes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_pairing_codes_family_id_families'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pairing_codes'))
    )
    op.create_index('uq_pairing_codes_unused', 'pairing_codes', ['code_hash'], unique=True, postgresql_where=sa.text('used_at IS NULL'))
    op.create_table('messages_out',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('family_id', sa.Uuid(), nullable=True),
    sa.Column('incident_id', sa.Uuid(), nullable=True),
    sa.Column('member_id', sa.Uuid(), nullable=True),
    sa.Column('channel', sa.String(length=8), nullable=False),
    sa.Column('bot_id', sa.String(length=64), nullable=False),
    sa.Column('template_id', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('quota_month', sa.String(length=7), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.String(length=64), nullable=True),
    sa.Column('job_key', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("channel IN ('zalo', 'push', 'web')", name=op.f('ck_messages_out_channel')),
    sa.CheckConstraint("status IN ('queued', 'sent', 'held_quota', 'failed', 'fallback_required')", name=op.f('ck_messages_out_status')),
    sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_messages_out_family_id_families'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['member_id'], ['members.id'], name=op.f('fk_messages_out_member_id_members'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages_out')),
    sa.UniqueConstraint('job_key', name=op.f('uq_messages_out_job_key'))
    )
    op.create_index('ix_messages_out_quota', 'messages_out', ['bot_id', 'quota_month', 'status'], unique=False)
    op.create_index('ix_jobs_kind_created', 'jobs', ['kind', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_kind_created', table_name='jobs', if_exists=True)
    op.drop_index('ix_messages_out_quota', table_name='messages_out')
    op.drop_table('messages_out')
    op.drop_index('uq_pairing_codes_unused', table_name='pairing_codes', postgresql_where=sa.text('used_at IS NULL'))
    op.drop_table('pairing_codes')
    op.drop_index('uq_members_guardian_rank', table_name='members', postgresql_where=sa.text("role = 'guardian'"))
    op.drop_table('members')
    op.drop_table('families')
