"""Add client_preview_started_at to projects for timeout of stuck generating.

Revision ID: z0a1b2c3d4e5f
Revises: y9a0b1c2d3e4f
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


revision = 'z0a1b2c3d4e5f'
down_revision = 'y9a0b1c2d3e4f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('projects', sa.Column('client_preview_started_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('projects', 'client_preview_started_at')
