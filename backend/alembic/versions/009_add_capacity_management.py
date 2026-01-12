"""Add capacity management tables

Revision ID: 009_capacity_management
Revises: 008_team_assignments
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM

# revision identifiers, used by Alembic.
revision = '009_capacity_management'
down_revision = '008_team_assignments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Reference existing enums (they already exist in the database)
    role_type = ENUM('ADMIN', 'MANAGER', 'CONSULTANT', 'PC', 'BUILDER', 'TESTER', name='role', create_type=False)
    region_type = ENUM('US', 'INDIA', 'PHILIPPINES', name='region', create_type=False)
    stage_type = ENUM('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage', create_type=False)
    
    # Create capacity_configs table
    op.create_table(
        'capacity_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('role', role_type, nullable=False),
        sa.Column('region', region_type, nullable=True),
        sa.Column('daily_hours', sa.Float(), server_default='6.8', nullable=False),
        sa.Column('weekly_hours', sa.Float(), server_default='34.0', nullable=False),
        sa.Column('buffer_percentage', sa.Float(), server_default='10.0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_capacity_config_role_region', 'capacity_configs', ['role', 'region'], unique=True)

    # Create user_daily_capacity table
    op.create_table(
        'user_daily_capacity',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_hours', sa.Float(), server_default='6.8', nullable=False),
        sa.Column('allocated_hours', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('is_available', sa.Boolean(), server_default='true'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_daily_capacity_user_date', 'user_daily_capacity', ['user_id', 'date'], unique=True)

    # Create project_workloads table
    op.create_table(
        'project_workloads',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('stage', stage_type, nullable=False),
        sa.Column('role', role_type, nullable=False),
        sa.Column('estimated_hours', sa.Float(), nullable=False),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('assigned_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('priority_score', sa.Float(), server_default='1.0'),
        sa.Column('complexity_factor', sa.Float(), server_default='1.0'),
        sa.Column('is_completed', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Create capacity_allocations table
    op.create_table(
        'capacity_allocations',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('workload_id', UUID(as_uuid=True), sa.ForeignKey('project_workloads.id'), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('allocated_hours', sa.Float(), nullable=False),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )

    # Create capacity_suggestions table
    op.create_table(
        'capacity_suggestions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=False),
        sa.Column('role', role_type, nullable=False),
        sa.Column('suggested_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('suggestion_type', sa.String(50), nullable=False),
        sa.Column('suggestion_text', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), server_default='0.5'),
        sa.Column('factors_json', JSONB, server_default='{}'),
        sa.Column('was_accepted', sa.Boolean(), nullable=True),
        sa.Column('feedback_notes', sa.Text(), nullable=True),
        sa.Column('actual_outcome', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('feedback_at', sa.DateTime(), nullable=True),
    )

    # Create capacity_history table
    op.create_table(
        'capacity_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('role', role_type, nullable=False),
        sa.Column('region', region_type, nullable=True),
        sa.Column('planned_hours', sa.Float(), server_default='0.0'),
        sa.Column('actual_hours', sa.Float(), server_default='0.0'),
        sa.Column('projects_count', sa.Integer(), server_default='0'),
        sa.Column('tasks_completed', sa.Integer(), server_default='0'),
        sa.Column('efficiency_score', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )

    # Create capacity_manual_inputs table
    op.create_table(
        'capacity_manual_inputs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('input_type', sa.String(50), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('role', role_type, nullable=True),
        sa.Column('region', region_type, nullable=True),
        sa.Column('value_numeric', sa.Float(), nullable=True),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('context_json', JSONB, server_default='{}'),
        sa.Column('created_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )

    # Insert default capacity configurations
    # Using only values that exist in the region enum
    op.execute("""
        INSERT INTO capacity_configs (id, role, region, daily_hours, weekly_hours, buffer_percentage, is_active, created_at)
        VALUES
        -- Default configs for each role (applies to all regions when region is NULL)
        (gen_random_uuid(), 'CONSULTANT', NULL, 6.8, 34.0, 10.0, true, NOW()),
        (gen_random_uuid(), 'PC', NULL, 6.8, 34.0, 15.0, true, NOW()),
        (gen_random_uuid(), 'BUILDER', NULL, 6.8, 34.0, 10.0, true, NOW()),
        (gen_random_uuid(), 'TESTER', NULL, 6.8, 34.0, 10.0, true, NOW()),
        -- Region-specific configs (US and INDIA)
        (gen_random_uuid(), 'BUILDER', 'US', 6.5, 32.5, 10.0, true, NOW()),
        (gen_random_uuid(), 'BUILDER', 'INDIA', 7.0, 35.0, 10.0, true, NOW()),
        (gen_random_uuid(), 'TESTER', 'INDIA', 7.0, 35.0, 10.0, true, NOW());
    """)


def downgrade() -> None:
    op.drop_table('capacity_manual_inputs')
    op.drop_table('capacity_history')
    op.drop_table('capacity_suggestions')
    op.drop_table('capacity_allocations')
    op.drop_table('project_workloads')
    op.drop_index('ix_user_daily_capacity_user_date', table_name='user_daily_capacity')
    op.drop_table('user_daily_capacity')
    op.drop_index('ix_capacity_config_role_region', table_name='capacity_configs')
    op.drop_table('capacity_configs')
