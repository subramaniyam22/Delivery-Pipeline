"""Add preview_iteration_count to onboarding_data for client preview attempt limit.

Revision ID: w7e8f9a0b1c2
Revises: v6g7b8c9d0e1f
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'w7e8f9a0b1c2'
down_revision = 'j7a8b9c0d1e2f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('onboarding_data', sa.Column('preview_iteration_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('onboarding_data', 'preview_iteration_count')
