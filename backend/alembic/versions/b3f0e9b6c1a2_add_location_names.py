"""add_location_names

Revision ID: b3f0e9b6c1a2
Revises: fix_missing_cols
Create Date: 2026-02-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b3f0e9b6c1a2'
down_revision = 'fix_missing_cols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('projects', sa.Column('location_names', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'location_names')
