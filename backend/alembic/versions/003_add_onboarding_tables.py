"""Add onboarding tables

Revision ID: 003_add_onboarding
Revises: 002_add_region
Create Date: 2025-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_onboarding'
down_revision = '002_add_region'
branch_labels = None
depends_on = None


# Use existing enums
stage_enum = postgresql.ENUM('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage', create_type=False)
taskstatus_enum = postgresql.ENUM('NOT_STARTED', 'IN_PROGRESS', 'DONE', name='taskstatus', create_type=False)


def upgrade() -> None:
    # Create onboarding_data table
    op.create_table(
        'onboarding_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False, unique=True),
        sa.Column('contacts_json', postgresql.JSONB, server_default='[]'),
        sa.Column('logo_url', sa.String(1000), nullable=True),
        sa.Column('images_json', postgresql.JSONB, server_default='[]'),
        sa.Column('copy_text', sa.Text, nullable=True),
        sa.Column('use_custom_copy', sa.Boolean, server_default='false'),
        sa.Column('wcag_compliance_required', sa.Boolean, server_default='true'),
        sa.Column('wcag_level', sa.String(10), server_default='AA'),
        sa.Column('privacy_policy_url', sa.String(1000), nullable=True),
        sa.Column('privacy_policy_text', sa.Text, nullable=True),
        sa.Column('theme_preference', sa.String(100), nullable=True),
        sa.Column('theme_colors_json', postgresql.JSONB, server_default='{}'),
        sa.Column('custom_fields_json', postgresql.JSONB, server_default='[]'),
        sa.Column('completion_percentage', sa.Integer, server_default='0'),
        sa.Column('last_reminder_sent', sa.DateTime, nullable=True),
        sa.Column('reminder_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Create project_tasks table
    op.create_table(
        'project_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('stage', stage_enum, nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_predefined', sa.Boolean, server_default='false'),
        sa.Column('is_required', sa.Boolean, server_default='true'),
        sa.Column('status', taskstatus_enum, server_default='NOT_STARTED'),
        sa.Column('assignee_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('order_index', sa.Integer, server_default='0'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # Create client_reminders table
    op.create_table(
        'client_reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('recipient_email', sa.String(255), nullable=False),
        sa.Column('recipient_name', sa.String(255), nullable=True),
        sa.Column('reminder_type', sa.String(100), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('sent_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('status', sa.String(50), server_default='sent'),
    )

    # Create indexes
    op.create_index('ix_onboarding_data_project_id', 'onboarding_data', ['project_id'])
    op.create_index('ix_project_tasks_project_id', 'project_tasks', ['project_id'])
    op.create_index('ix_project_tasks_stage', 'project_tasks', ['stage'])
    op.create_index('ix_client_reminders_project_id', 'client_reminders', ['project_id'])


def downgrade() -> None:
    op.drop_index('ix_client_reminders_project_id')
    op.drop_index('ix_project_tasks_stage')
    op.drop_index('ix_project_tasks_project_id')
    op.drop_index('ix_onboarding_data_project_id')
    op.drop_table('client_reminders')
    op.drop_table('project_tasks')
    op.drop_table('onboarding_data')

