"""fix_missing_project_columns

Revision ID: fix_missing_cols
Revises: add_indexes_soft_delete
Create Date: 2026-02-05 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'fix_missing_cols'
down_revision = 'add_indexes_soft_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('projects')]

    if 'project_type' not in columns:
        op.add_column('projects', sa.Column('project_type', sa.String(length=50), nullable=True))
    
    if 'pmc_name' not in columns:
        op.add_column('projects', sa.Column('pmc_name', sa.String(length=255), nullable=True))
        
    if 'location' not in columns:
        op.add_column('projects', sa.Column('location', sa.String(length=255), nullable=True))
        
    if 'client_email_ids' not in columns:
        op.add_column('projects', sa.Column('client_email_ids', sa.Text(), nullable=True))
        
    # Check for manager_user_id and sales_user_id just in case
    if 'manager_user_id' not in columns:
         op.add_column('projects', sa.Column('manager_user_id', sa.UUID(), nullable=True))
         op.create_foreign_key('fk_projects_manager_user_id', 'projects', 'users', ['manager_user_id'], ['id'])
         
    if 'sales_user_id' not in columns:
         op.add_column('projects', sa.Column('sales_user_id', sa.UUID(), nullable=True))
         op.create_foreign_key('fk_projects_sales_user_id', 'projects', 'users', ['sales_user_id'], ['id'])


def downgrade() -> None:
    # Downgrade logic is tricky if conditional, but we can try dropping if exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('projects')]
    
    if 'project_type' in columns:
        op.drop_column('projects', 'project_type')
    # ... strict downgrade might not be needed for this fix migration
