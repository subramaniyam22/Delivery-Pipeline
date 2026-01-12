"""Add date of joining and update leave policies

Revision ID: 012_date_of_joining
Revises: 011_comprehensive_capacity
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '012_date_of_joining'
down_revision = '011_comprehensive_capacity'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Add date_of_joining to users table
    columns = [c['name'] for c in inspector.get_columns('users')]
    if 'date_of_joining' not in columns:
        op.add_column('users',
            sa.Column('date_of_joining', sa.Date(), nullable=True)
        )
    
    # Update leave entitlement policies with correct values
    # First, deactivate old policies
    op.execute("""
        UPDATE leave_entitlement_policies 
        SET is_active = false 
        WHERE is_active = true;
    """)
    
    # Insert updated policies with correct values
    op.execute("""
        INSERT INTO leave_entitlement_policies 
        (id, leave_type, role, region, annual_days, can_carry_forward, max_carry_forward_days, 
         requires_approval, min_notice_days, max_consecutive_days, is_active)
        VALUES
        -- Casual Leave: 12 per year (all roles, all regions)
        (gen_random_uuid(), 'CASUAL', NULL, NULL, 12, false, 0, true, 1, NULL, true),
        
        -- Sick Leave: 12 per year (all roles, all regions)
        (gen_random_uuid(), 'SICK', NULL, NULL, 12, false, 0, false, 0, NULL, true),
        
        -- Earned Leave: 1.25 per month = 15 per year (prorated based on DOJ)
        -- Setting annual_days to 15, but calculation will prorate based on months worked
        (gen_random_uuid(), 'EARNED', NULL, NULL, 15, true, 5, true, 7, NULL, true),
        
        -- Maternity Leave: 6 months = 180 days (calendar days)
        (gen_random_uuid(), 'MATERNITY', NULL, NULL, 180, false, 0, true, 30, NULL, true),
        
        -- Paternity Leave: 1 week = 5 working days
        (gen_random_uuid(), 'PATERNITY', NULL, NULL, 5, false, 0, true, 7, NULL, true),
        
        -- Bereavement Leave: 3 days
        (gen_random_uuid(), 'BEREAVEMENT', NULL, NULL, 3, false, 0, false, 0, NULL, true),
        
        -- Work From Home: 12 per year
        (gen_random_uuid(), 'WORK_FROM_HOME', NULL, NULL, 12, false, 0, true, 1, NULL, true),
        
        -- Compensatory Off: Earned based on overtime (starts at 0)
        (gen_random_uuid(), 'COMPENSATORY', NULL, NULL, 0, true, 10, true, 1, NULL, true),
        
        -- Unpaid Leave: Unlimited but requires approval
        (gen_random_uuid(), 'UNPAID', NULL, NULL, 365, false, 0, true, 7, NULL, true);
    """)


def downgrade() -> None:
    op.drop_column('users', 'date_of_joining')
