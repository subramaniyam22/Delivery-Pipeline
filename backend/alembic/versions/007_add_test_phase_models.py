"""Add test phase sub-agents models

Revision ID: 007_test_phase_models
Revises: 006_add_user_archive_fields
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_test_phase_models'
down_revision = '006_add_user_archive_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums using raw SQL with IF NOT EXISTS
    connection = op.get_bind()
    
    # Check and create testexecutionstatus enum
    result = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'testexecutionstatus'"
    ))
    if result.fetchone() is None:
        connection.execute(sa.text(
            "CREATE TYPE testexecutionstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')"
        ))
    
    # Check and create testresultstatus enum
    result = connection.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = 'testresultstatus'"
    ))
    if result.fetchone() is None:
        connection.execute(sa.text(
            "CREATE TYPE testresultstatus AS ENUM ('PASSED', 'FAILED', 'SKIPPED', 'BLOCKED')"
        ))
    
    # Create test_scenarios table
    op.create_table(
        'test_scenarios',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_file', sa.String(500), nullable=True),
        sa.Column('source_url', sa.String(1000), nullable=True),
        sa.Column('pmc_name', sa.String(255), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('is_auto_generated', sa.Boolean(), default=False),
        sa.Column('priority', sa.Integer(), default=2),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create test_cases table
    op.create_table(
        'test_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('preconditions', sa.Text(), nullable=True),
        sa.Column('steps_json', postgresql.JSONB(), default=list),
        sa.Column('expected_outcome', sa.Text(), nullable=True),
        sa.Column('test_data_json', postgresql.JSONB(), default=dict),
        sa.Column('is_automated', sa.Boolean(), default=False),
        sa.Column('automation_script', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), default=2),
        sa.Column('order_index', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['scenario_id'], ['test_scenarios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create test_executions table
    op.create_table(
        'test_executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', name='testexecutionstatus', create_type=False), nullable=True),
        sa.Column('executed_by', sa.String(100), default='QA_AUTOMATION_AGENT'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_tests', sa.Integer(), default=0),
        sa.Column('passed_count', sa.Integer(), default=0),
        sa.Column('failed_count', sa.Integer(), default=0),
        sa.Column('skipped_count', sa.Integer(), default=0),
        sa.Column('blocked_count', sa.Integer(), default=0),
        sa.Column('execution_log', sa.Text(), nullable=True),
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create test_results table
    op.create_table(
        'test_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', postgresql.ENUM('PASSED', 'FAILED', 'SKIPPED', 'BLOCKED', name='testresultstatus', create_type=False), nullable=False),
        sa.Column('actual_result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('screenshot_url', sa.String(1000), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('ai_notes', sa.Text(), nullable=True),
        sa.Column('defect_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['test_executions.id'], ),
        sa.ForeignKeyConstraint(['test_case_id'], ['test_cases.id'], ),
        sa.ForeignKeyConstraint(['defect_id'], ['defects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create defect_assignments table
    op.create_table(
        'defect_assignments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('defect_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assigned_by_agent', sa.String(100), nullable=True),
        sa.Column('pmc_name', sa.String(255), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('assignment_reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('reassigned_reason', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['defect_id'], ['defects.id'], ),
        sa.ForeignKeyConstraint(['assigned_to_user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_availability table
    op.create_table(
        'user_availability',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('start_date', sa.DateTime(), nullable=False),
        sa.Column('end_date', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('is_available', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create builder_work_history table
    op.create_table(
        'builder_work_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pmc_name', sa.String(255), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('worked_on_stage', postgresql.ENUM('ONBOARDING', 'ASSIGNMENT', 'BUILD', 'TEST', 'DEFECT_VALIDATION', 'COMPLETE', name='stage', create_type=False), nullable=True),
        sa.Column('task_count', sa.Integer(), default=0),
        sa.Column('last_worked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add new columns to defects table
    op.add_column('defects', sa.Column('title', sa.String(500), nullable=True))
    op.add_column('defects', sa.Column('pmc_name', sa.String(255), nullable=True))
    op.add_column('defects', sa.Column('location_name', sa.String(255), nullable=True))
    op.add_column('defects', sa.Column('assigned_to_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('defects', sa.Column('assigned_by_agent', sa.Boolean(), default=False))
    op.add_column('defects', sa.Column('source_test_case_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('defects', sa.Column('created_by_agent', sa.String(100), nullable=True))
    op.add_column('defects', sa.Column('fixed_by_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('defects', sa.Column('fixed_at', sa.DateTime(), nullable=True))
    op.add_column('defects', sa.Column('fix_description', sa.Text(), nullable=True))
    op.add_column('defects', sa.Column('validated_by_agent', sa.Boolean(), default=False))
    op.add_column('defects', sa.Column('validation_notes', sa.Text(), nullable=True))
    
    # Add foreign keys to defects
    op.create_foreign_key('fk_defects_assigned_to', 'defects', 'users', ['assigned_to_user_id'], ['id'])
    op.create_foreign_key('fk_defects_fixed_by', 'defects', 'users', ['fixed_by_user_id'], ['id'])


def downgrade() -> None:
    # Drop foreign keys from defects
    op.drop_constraint('fk_defects_assigned_to', 'defects', type_='foreignkey')
    op.drop_constraint('fk_defects_fixed_by', 'defects', type_='foreignkey')
    
    # Drop new columns from defects
    op.drop_column('defects', 'validation_notes')
    op.drop_column('defects', 'validated_by_agent')
    op.drop_column('defects', 'fix_description')
    op.drop_column('defects', 'fixed_at')
    op.drop_column('defects', 'fixed_by_user_id')
    op.drop_column('defects', 'created_by_agent')
    op.drop_column('defects', 'source_test_case_id')
    op.drop_column('defects', 'assigned_by_agent')
    op.drop_column('defects', 'assigned_to_user_id')
    op.drop_column('defects', 'location_name')
    op.drop_column('defects', 'pmc_name')
    op.drop_column('defects', 'title')
    
    # Drop tables
    op.drop_table('builder_work_history')
    op.drop_table('user_availability')
    op.drop_table('defect_assignments')
    op.drop_table('test_results')
    op.drop_table('test_executions')
    op.drop_table('test_cases')
    op.drop_table('test_scenarios')
    
    # Drop enums
    sa.Enum(name='testresultstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='testexecutionstatus').drop(op.get_bind(), checkfirst=True)
