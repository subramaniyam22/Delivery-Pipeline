"""Add onboarding submission tracking and requirements overrides

Revision ID: 017_add_submission_requirements
Revises: 016_add_wcag_confirmed
Create Date: 2026-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '017_add_submission_requirements'
down_revision = '016_add_wcag_confirmed'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Project-level minimum requirement overrides
    op.add_column('projects', sa.Column('minimum_requirements_override', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('projects', sa.Column('allow_requirements_exceptions', sa.Boolean(), server_default='false', nullable=False))

    # Client submission tracking
    op.add_column('onboarding_data', sa.Column('submitted_at', sa.DateTime(), nullable=True))
    op.add_column('onboarding_data', sa.Column('missing_fields_eta_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('onboarding_data', 'missing_fields_eta_json')
    op.drop_column('onboarding_data', 'submitted_at')
    op.drop_column('projects', 'allow_requirements_exceptions')
    op.drop_column('projects', 'minimum_requirements_override')
