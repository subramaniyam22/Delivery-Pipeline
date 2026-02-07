"""add_stage_history

Revision ID: c1a4e77d9f3b
Revises: b3f0e9b6c1a2
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c1a4e77d9f3b'
down_revision = 'b3f0e9b6c1a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('stage_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'stage_history')
