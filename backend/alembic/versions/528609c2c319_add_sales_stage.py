"""add_sales_stage

Revision ID: 528609c2c319
Revises: 0db97cb1d60b
Create Date: 2026-02-04 04:18:28.128719

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '528609c2c319'
down_revision = '0db97cb1d60b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'SALES' to Stage enum
    # Check if SALES already exists to avoid errors
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_enum 
            WHERE enumlabel = 'SALES' 
            AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'stage')
        );
    """))
    exists = result.scalar()
    
    if not exists:
        # Use raw SQL with autocommit
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE stage ADD VALUE 'SALES'")


def downgrade() -> None:
    pass
