"""Add user archive fields

Revision ID: 006_add_user_archive_fields
Revises: 005_add_password_reset_tokens
Create Date: 2026-01-11
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006_add_user_archive_fields'
down_revision = '005_add_password_reset_tokens'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('archived_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'archived_at')
    op.drop_column('users', 'is_archived')
