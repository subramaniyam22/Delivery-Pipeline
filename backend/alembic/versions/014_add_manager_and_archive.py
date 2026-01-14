"""Add manager hierarchy and project archive/pause

Revision ID: 014_manager_archive
Revises: 013_sla_client_emails
Create Date: 2026-01-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '014_manager_archive'
down_revision = '013_sla_client_emails'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add PAUSED and ARCHIVED to project_status enum
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'PAUSED'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'ARCHIVED'")
    
    # Add manager_id to users table
    user_columns = [c['name'] for c in inspector.get_columns('users')]
    if 'manager_id' not in user_columns:
        op.add_column('users',
            sa.Column('manager_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
        )
        op.create_index('ix_users_manager_id', 'users', ['manager_id'])
    
    # Add archive/pause fields to projects table
    project_columns = [c['name'] for c in inspector.get_columns('projects')]
    
    if 'paused_at' not in project_columns:
        op.add_column('projects', sa.Column('paused_at', sa.DateTime(), nullable=True))
    
    if 'paused_by_user_id' not in project_columns:
        op.add_column('projects', 
            sa.Column('paused_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
        )
    
    if 'pause_reason' not in project_columns:
        op.add_column('projects', sa.Column('pause_reason', sa.Text(), nullable=True))
    
    if 'archived_at' not in project_columns:
        op.add_column('projects', sa.Column('archived_at', sa.DateTime(), nullable=True))
    
    if 'archived_by_user_id' not in project_columns:
        op.add_column('projects',
            sa.Column('archived_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
        )
    
    if 'archive_reason' not in project_columns:
        op.add_column('projects', sa.Column('archive_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('projects', 'archive_reason')
    op.drop_column('projects', 'archived_by_user_id')
    op.drop_column('projects', 'archived_at')
    op.drop_column('projects', 'pause_reason')
    op.drop_column('projects', 'paused_by_user_id')
    op.drop_column('projects', 'paused_at')
    op.drop_index('ix_users_manager_id', 'users')
    op.drop_column('users', 'manager_id')
