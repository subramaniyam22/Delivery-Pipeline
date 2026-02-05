"""add description to projects

Revision ID: add_desc_col
Revises: fix_sales_role_enum
Create Date: 2026-02-06 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_desc_col'
down_revision = 'fix_sales_role_enum'
branch_labels = None
depends_on = None


def upgrade():
    # Check if column exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('projects')]
    
    if 'description' not in columns:
        op.add_column('projects', sa.Column('description', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('projects', 'description')
