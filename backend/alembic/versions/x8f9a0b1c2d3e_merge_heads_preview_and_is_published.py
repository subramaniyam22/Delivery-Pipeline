"""Merge heads: preview_iteration_count and fix_is_published_default.

Revision ID: x8f9a0b1c2d3e
Revises: p1e2f3a4b5c6d, w7e8f9a0b1c2
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'x8f9a0b1c2d3e'
down_revision = ('p1e2f3a4b5c6d', 'w7e8f9a0b1c2')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
