"""jobs + agent_runs + agent_steps (P1-S4: hàng đợi hẹn giờ, trace tác tử)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('agent_runs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('incident_id', sa.Uuid(), nullable=True),
    sa.Column('graph', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'running'"), nullable=False),
    sa.Column('thread_id', sa.String(length=64), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cost_usd', sa.Numeric(precision=12, scale=6), server_default=sa.text('0'), nullable=False),
    sa.Column('is_drill', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.CheckConstraint("graph IN ('incident', 'coach')", name=op.f('ck_agent_runs_graph')),
    sa.CheckConstraint("status IN ('running', 'waiting', 'done', 'failed')", name=op.f('ck_agent_runs_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_runs')),
    sa.UniqueConstraint('thread_id', name=op.f('uq_agent_runs_thread_id'))
    )
    op.create_table('jobs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=64), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('run_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('idempotency_key', sa.String(length=200), nullable=True),
    sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('locked_by', sa.String(length=64), nullable=True),
    sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs')),
    sa.UniqueConstraint('idempotency_key', name=op.f('uq_jobs_idempotency_key'))
    )
    op.create_index('ix_jobs_due', 'jobs', ['run_at'], unique=False, postgresql_where=sa.text('done_at IS NULL'))
    op.create_table('agent_steps',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('run_id', sa.Uuid(), nullable=False),
    sa.Column('node', sa.String(length=64), nullable=False),
    sa.Column('model_profile', sa.String(length=16), nullable=True),
    sa.Column('model', sa.String(length=64), nullable=True),
    sa.Column('prompt_version', sa.String(length=32), nullable=True),
    sa.Column('input_redacted', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('latency_ms', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('tokens_in', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('tokens_out', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('cost_usd', sa.Numeric(precision=12, scale=6), server_default=sa.text('0'), nullable=False),
    sa.Column('fallback_used', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('error', sa.String(length=64), nullable=True),
    sa.Column('at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], name=op.f('fk_agent_steps_run_id_agent_runs'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_agent_steps'))
    )
    op.create_index('ix_agent_steps_run_at', 'agent_steps', ['run_id', 'at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agent_steps_run_at', table_name='agent_steps')
    op.drop_table('agent_steps')
    op.drop_index('ix_jobs_due', table_name='jobs', postgresql_where=sa.text('done_at IS NULL'))
    op.drop_table('jobs')
    op.drop_table('agent_runs')
