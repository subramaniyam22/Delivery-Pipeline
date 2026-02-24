"""Allow audit_logs.actor_user_id to be NULL for system/automated actions.

Revision ID: y9a0b1c2d3e4f
Revises: x8f9a0b1c2d3e
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa


revision = 'y9a0b1c2d3e4f'
down_revision = 'x8f9a0b1c2d3e'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'audit_logs',
        'actor_user_id',
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        'audit_logs',
        'actor_user_id',
        existing_type=sa.UUID(),
        nullable=False,
    )
