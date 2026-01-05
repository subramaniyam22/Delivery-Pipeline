"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2025-12-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('ADMIN', 'MANAGER', 'CONSULTANT', 'PC', 'BUILDER', 'TESTER', name='role'), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('client_name', sa.String(255), nullable=False),
        sa.Column('priority', sa.String(50), default='MEDIUM'),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED', name='projectstatus'), nullable=False),
        sa.Column('current_stage', sa.Enum('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage'), nullable=False),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('stage', sa.Enum('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('assignee_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.Enum('NOT_STARTED', 'IN_PROGRESS', 'DONE', name='taskstatus'), nullable=False),
        sa.Column('checklist_json', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create stage_outputs table
    op.create_table(
        'stage_outputs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('stage', sa.Enum('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage'), nullable=False),
        sa.Column('status', sa.Enum('SUCCESS', 'NEEDS_HUMAN', 'BLOCKED', 'FAILED', name='stagestatus'), nullable=False),
        sa.Column('summary', sa.Text()),
        sa.Column('structured_output_json', postgresql.JSONB, default=dict),
        sa.Column('required_next_inputs_json', postgresql.JSONB, default=list),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('stage', sa.Enum('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage'), nullable=False),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('notes', sa.Text()),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    # Create defects table
    op.create_table(
        'defects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='defectseverity'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'VALID', 'INVALID', 'FIXED', 'RETEST', name='defectstatus'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_json', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create admin_configs table
    op.create_table(
        'admin_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('value_json', postgresql.JSONB, nullable=False),
        sa.Column('updated_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('payload_json', postgresql.JSONB, default=dict),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('admin_configs')
    op.drop_table('defects')
    op.drop_table('artifacts')
    op.drop_table('stage_outputs')
    op.drop_table('tasks')
    op.drop_table('projects')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS role')
    op.execute('DROP TYPE IF EXISTS projectstatus')
    op.execute('DROP TYPE IF EXISTS stage')
    op.execute('DROP TYPE IF EXISTS taskstatus')
    op.execute('DROP TYPE IF EXISTS stagestatus')
    op.execute('DROP TYPE IF EXISTS defectseverity')
    op.execute('DROP TYPE IF EXISTS defectstatus')
