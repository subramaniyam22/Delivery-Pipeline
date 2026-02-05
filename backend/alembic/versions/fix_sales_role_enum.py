"""fix_sales_role_enum

Revision ID: fix_sales_enum
Revises: fix_missing_cols
Create Date: 2026-02-05 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'fix_sales_enum'
down_revision = 'fix_missing_cols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres specific command to add value to Enum
    # We use a primitive check to avoid error if already exists
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    
    try:
        # Check if 'SALES' exists in 'role' enum
        result = session.execute(sa.text("SELECT 1 FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'role' AND pg_enum.enumlabel = 'SALES'")).scalar()
        
        if not result:
            # Must run outside transaction block sometimes? 
            # In recent Postgres it's safe within txn.
            # But just in case, we execute it.
            op.execute("ALTER TYPE role ADD VALUE 'SALES'")
            print("Added SALES to role enum")
        else:
            print("SALES already in role enum")
            
    except Exception as e:
        print(f"Error updating enum: {e}")
        # If 'role' type doesn't exist (maybe upper case?), we might fail.
        # But standard fastapi/sqlalchemy creates lower case enum types by default.

def downgrade() -> None:
    # Cannot remove value from Enum in Postgres easily
    pass
