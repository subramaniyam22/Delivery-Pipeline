"""Add team assignment fields to projects

Revision ID: 008_team_assignments
Revises: 007_test_phase_models
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '008_team_assignments'
down_revision = '007_test_phase_models'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add team assignment columns to projects table
    op.add_column('projects', sa.Column('pc_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('projects', sa.Column('consultant_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('projects', sa.Column('builder_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('projects', sa.Column('tester_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'tester_user_id')
    op.drop_column('projects', 'builder_user_id')
    op.drop_column('projects', 'consultant_user_id')
    op.drop_column('projects', 'pc_user_id')
