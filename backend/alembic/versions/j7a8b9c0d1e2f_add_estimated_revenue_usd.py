"""add_estimated_revenue_usd

Revision ID: j7a8b9c0d1e2f
Revises: v6g7b8c9d0e1f
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa


revision = 'j7a8b9c0d1e2f'
down_revision = 'v6g7b8c9d0e1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('estimated_revenue_usd', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'estimated_revenue_usd')
