"""Add requirements_json to onboarding_data

Revision ID: 018_add_requirements_json
Revises: 017_add_submission_requirements
Create Date: 2026-01-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '018_add_requirements_json'
down_revision = '017_add_submission_requirements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('onboarding_data', sa.Column('requirements_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column('onboarding_data', 'requirements_json')
