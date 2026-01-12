"""Add SLA configuration and client emails

Revision ID: 013
Revises: 012
Create Date: 2026-01-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create SLA Configuration table
    op.create_table(
        'sla_configurations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('default_days', sa.Integer, nullable=False, default=7),
        sa.Column('warning_threshold_days', sa.Integer, nullable=False, default=2),
        sa.Column('critical_threshold_days', sa.Integer, nullable=False, default=1),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create unique index on stage
    op.create_index('ix_sla_configurations_stage', 'sla_configurations', ['stage'], unique=True)
    
    # Add client email fields to projects
    op.add_column('projects', sa.Column('client_emails', JSONB, nullable=True, server_default='[]'))
    op.add_column('projects', sa.Column('client_primary_contact', sa.String(255), nullable=True))
    op.add_column('projects', sa.Column('client_company', sa.String(255), nullable=True))
    
    # Add phase deadline tracking
    op.add_column('projects', sa.Column('phase_deadlines', JSONB, nullable=True, server_default='{}'))
    op.add_column('projects', sa.Column('phase_start_dates', JSONB, nullable=True, server_default='{}'))
    op.add_column('projects', sa.Column('is_delayed', sa.Boolean, default=False, server_default='false'))
    op.add_column('projects', sa.Column('delay_reason', sa.Text, nullable=True))
    
    # Create client reminder history table
    op.create_table(
        'client_reminder_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('reminder_type', sa.String(100), nullable=False),
        sa.Column('sent_to', JSONB, nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('sent_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('sent_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('status', sa.String(50), default='SENT'),
    )
    
    # Seed default SLA configurations
    op.execute("""
        INSERT INTO sla_configurations (id, stage, default_days, warning_threshold_days, critical_threshold_days, description, is_active)
        VALUES 
            (gen_random_uuid(), 'ONBOARDING', 5, 2, 1, 'Client onboarding and requirements gathering', true),
            (gen_random_uuid(), 'ASSIGNMENT', 2, 1, 0, 'Team assignment and resource allocation', true),
            (gen_random_uuid(), 'BUILD', 14, 3, 1, 'Development and implementation phase', true),
            (gen_random_uuid(), 'TEST', 7, 2, 1, 'Testing and quality assurance phase', true),
            (gen_random_uuid(), 'COMPLETE', 2, 1, 0, 'Final review and project completion', true)
        ON CONFLICT (stage) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table('client_reminder_logs')
    op.drop_column('projects', 'delay_reason')
    op.drop_column('projects', 'is_delayed')
    op.drop_column('projects', 'phase_start_dates')
    op.drop_column('projects', 'phase_deadlines')
    op.drop_column('projects', 'client_company')
    op.drop_column('projects', 'client_primary_contact')
    op.drop_column('projects', 'client_emails')
    op.drop_index('ix_sla_configurations_stage')
    op.drop_table('sla_configurations')
