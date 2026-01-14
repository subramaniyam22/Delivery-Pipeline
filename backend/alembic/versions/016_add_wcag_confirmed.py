"""Add wcag_confirmed field to onboarding_data

Revision ID: 016_add_wcag_confirmed
Revises: 015_reminder_interval
Create Date: 2026-01-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '016_add_wcag_confirmed'
down_revision = '015_reminder_interval'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add wcag_confirmed column with default False
    # This ensures existing records don't auto-complete the WCAG requirement
    op.add_column('onboarding_data', sa.Column('wcag_confirmed', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('onboarding_data', 'wcag_confirmed')
