"""
Database migration: Add indexes and soft delete columns

Revision ID: add_indexes_soft_delete
Revises: previous_migration
Create Date: 2026-02-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
# revision identifiers
revision = 'add_indexes_soft_delete'
down_revision = '8cf57896ef1a'  # Linearize history
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes for performance and soft delete columns"""
    
    # Add indexes to Project table for frequently queried columns
    # Note: status, current_stage, manager, sales are indexed in 8cf57896ef1a
    
    op.create_index('idx_project_consultant_user_id', 'projects', ['consultant_user_id'])
    op.create_index('idx_project_builder_user_id', 'projects', ['builder_user_id'])
    op.create_index('idx_project_tester_user_id', 'projects', ['tester_user_id'])
    op.create_index('idx_project_pc_user_id', 'projects', ['pc_user_id'])
    
    # Composite index for common query patterns
    op.create_index('idx_project_status_stage', 'projects', ['status', 'current_stage'])
    op.create_index('idx_project_created_at', 'projects', ['created_at'])
    op.create_index('idx_project_updated_at', 'projects', ['updated_at'])
    
    # Add soft delete columns to projects table
    op.add_column('projects', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('projects', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('projects', sa.Column('deleted_by_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Add foreign key for deleted_by_user_id
    op.create_foreign_key(
        'fk_projects_deleted_by_user',
        'projects',
        'users',
        ['deleted_by_user_id'],
        ['id']
    )
    
    # Add index on is_deleted for filtering
    op.create_index('idx_project_is_deleted', 'projects', ['is_deleted'])
    
    # Add indexes to User table
    op.create_index('idx_user_role', 'users', ['role'])
    op.create_index('idx_user_is_active', 'users', ['is_active'])
    op.create_index('idx_user_region', 'users', ['region'])
    
    # Add indexes to AuditLog table for querying
    op.create_index('idx_audit_log_project_id', 'audit_logs', ['project_id'])
    op.create_index('idx_audit_log_actor_user_id', 'audit_logs', ['actor_user_id'])
    op.create_index('idx_audit_log_created_at', 'audit_logs', ['created_at'])
    op.create_index('idx_audit_log_action', 'audit_logs', ['action'])
    
    # Add indexes to Defect table
    op.create_index('idx_defect_project_id', 'defects', ['project_id'])
    op.create_index('idx_defect_status', 'defects', ['status'])
    op.create_index('idx_defect_severity', 'defects', ['severity'])
    op.create_index('idx_defect_assigned_to_user_id', 'defects', ['assigned_to_user_id'])
    
    # Add indexes to ProjectTask table
    op.create_index('idx_project_task_project_id', 'project_tasks', ['project_id'])
    op.create_index('idx_project_task_stage', 'project_tasks', ['stage'])
    op.create_index('idx_project_task_assignee_user_id', 'project_tasks', ['assignee_user_id'])
    op.create_index('idx_project_task_status', 'project_tasks', ['status'])


def downgrade():
    """Remove indexes and soft delete columns"""
    
    # Drop indexes from Project table
    # op.drop_index('idx_project_status', table_name='projects')
    # op.drop_index('idx_project_current_stage', table_name='projects')
    # op.drop_index('idx_project_manager_user_id', table_name='projects')
    # op.drop_index('idx_project_sales_user_id', table_name='projects')
    op.drop_index('idx_project_consultant_user_id', table_name='projects')
    op.drop_index('idx_project_builder_user_id', table_name='projects')
    op.drop_index('idx_project_tester_user_id', table_name='projects')
    op.drop_index('idx_project_created_at', table_name='projects')
    op.drop_index('idx_project_updated_at', table_name='projects')
    op.drop_index('idx_project_is_deleted', table_name='projects')
    
    # Drop soft delete columns
    op.drop_constraint('fk_projects_deleted_by_user', 'projects', type_='foreignkey')
    op.drop_column('projects', 'deleted_by_user_id')
    op.drop_column('projects', 'deleted_at')
    op.drop_column('projects', 'is_deleted')
    
    # Drop indexes from User table
    op.drop_index('idx_user_role', table_name='users')
    op.drop_index('idx_user_is_active', table_name='users')
    op.drop_index('idx_user_region', table_name='users')
    
    # Drop indexes from AuditLog table
    op.drop_index('idx_audit_log_project_id', table_name='audit_logs')
    op.drop_index('idx_audit_log_actor_user_id', table_name='audit_logs')
    op.drop_index('idx_audit_log_created_at', table_name='audit_logs')
    op.drop_index('idx_audit_log_action', table_name='audit_logs')
    
    # Drop indexes from Defect table
    op.drop_index('idx_defect_project_id', table_name='defects')
    op.drop_index('idx_defect_status', table_name='defects')
    op.drop_index('idx_defect_severity', table_name='defects')
    op.drop_index('idx_defect_assigned_to_user_id', table_name='defects')
    
    # Drop indexes from ProjectTask table
    op.drop_index('idx_project_task_project_id', table_name='project_tasks')
    op.drop_index('idx_project_task_stage', table_name='project_tasks')
    op.drop_index('idx_project_task_assignee_user_id', table_name='project_tasks')
    op.drop_index('idx_project_task_status', table_name='project_tasks')
