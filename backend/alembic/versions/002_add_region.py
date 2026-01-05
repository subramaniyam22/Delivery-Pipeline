"""Add region column to users table

Revision ID: 002_add_region
Revises: 001_initial
Create Date: 2025-12-30

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_region'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the region enum type
    op.execute("CREATE TYPE region AS ENUM ('INDIA', 'US', 'PH')")
    
    # Add the region column to users table with default value
    op.add_column(
        'users',
        sa.Column('region', sa.Enum('INDIA', 'US', 'PH', name='region'), nullable=True, server_default='INDIA')
    )


def downgrade() -> None:
    # Remove the region column
    op.drop_column('users', 'region')
    
    # Drop the region enum type
    op.execute('DROP TYPE IF EXISTS region')

