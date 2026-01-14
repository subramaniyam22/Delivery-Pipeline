"""Add reminder interval hours to onboarding data

Revision ID: 015_reminder_interval
Revises: 014_manager_archive
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '015_reminder_interval'
down_revision = '014_manager_archive'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add reminder_interval_hours column with default 24
    op.add_column('onboarding_data', sa.Column('reminder_interval_hours', sa.Integer(), nullable=True, server_default='24'))


def downgrade() -> None:
    op.drop_column('onboarding_data', 'reminder_interval_hours')
