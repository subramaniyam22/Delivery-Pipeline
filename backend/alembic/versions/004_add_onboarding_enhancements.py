"""Add onboarding enhancements - pricing, templates, auto reminders

Revision ID: 004_onboarding_enhancements
Revises: 003_add_onboarding
Create Date: 2025-01-03 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_onboarding_enhancements'
down_revision = '003_add_onboarding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to onboarding_data
    op.add_column('onboarding_data', sa.Column('client_access_token', sa.String(255), nullable=True, unique=True))
    op.add_column('onboarding_data', sa.Column('token_expires_at', sa.DateTime, nullable=True))
    op.add_column('onboarding_data', sa.Column('logo_file_path', sa.String(1000), nullable=True))
    op.add_column('onboarding_data', sa.Column('custom_copy_base_price', sa.Integer, server_default='500'))
    op.add_column('onboarding_data', sa.Column('custom_copy_word_count', sa.Integer, server_default='1000'))
    op.add_column('onboarding_data', sa.Column('custom_copy_final_price', sa.Integer, nullable=True))
    op.add_column('onboarding_data', sa.Column('custom_copy_notes', sa.Text, nullable=True))
    op.add_column('onboarding_data', sa.Column('selected_template_id', sa.String(100), nullable=True))
    op.add_column('onboarding_data', sa.Column('next_reminder_at', sa.DateTime, nullable=True))
    op.add_column('onboarding_data', sa.Column('auto_reminder_enabled', sa.Boolean, server_default='true'))
    
    # Add new columns to project_tasks
    op.add_column('project_tasks', sa.Column('is_auto_completed', sa.Boolean, server_default='false'))
    op.add_column('project_tasks', sa.Column('linked_field', sa.String(100), nullable=True))
    
    # Create index for client access token
    op.create_index('ix_onboarding_data_client_access_token', 'onboarding_data', ['client_access_token'])


def downgrade() -> None:
    op.drop_index('ix_onboarding_data_client_access_token')
    op.drop_column('project_tasks', 'linked_field')
    op.drop_column('project_tasks', 'is_auto_completed')
    op.drop_column('onboarding_data', 'auto_reminder_enabled')
    op.drop_column('onboarding_data', 'next_reminder_at')
    op.drop_column('onboarding_data', 'selected_template_id')
    op.drop_column('onboarding_data', 'custom_copy_notes')
    op.drop_column('onboarding_data', 'custom_copy_final_price')
    op.drop_column('onboarding_data', 'custom_copy_word_count')
    op.drop_column('onboarding_data', 'custom_copy_base_price')
    op.drop_column('onboarding_data', 'logo_file_path')
    op.drop_column('onboarding_data', 'token_expires_at')
    op.drop_column('onboarding_data', 'client_access_token')

