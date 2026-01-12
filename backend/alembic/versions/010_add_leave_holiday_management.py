"""Add leave and holiday management tables

Revision ID: 010_leave_holiday
Revises: 009_capacity_management
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision = '010_leave_holiday'
down_revision = '009_capacity_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add unavailability_reason column to user_daily_capacity if not exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('user_daily_capacity')]
    if 'unavailability_reason' not in columns:
        op.add_column('user_daily_capacity', 
            sa.Column('unavailability_reason', sa.String(255), nullable=True)
        )
    
    # Create leave_type enum (check if exists first)
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE leavetype AS ENUM ('ANNUAL', 'SICK', 'PERSONAL', 'MATERNITY', 'PATERNITY', 
                      'BEREAVEMENT', 'UNPAID', 'WORK_FROM_HOME', 'TRAINING');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create leave_status enum (check if exists first)
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE leavestatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Reference existing enums for use in tables
    leave_type = ENUM('ANNUAL', 'SICK', 'PERSONAL', 'MATERNITY', 'PATERNITY', 
                      'BEREAVEMENT', 'UNPAID', 'WORK_FROM_HOME', 'TRAINING',
                      name='leavetype', create_type=False)
    leave_status = ENUM('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED',
                        name='leavestatus', create_type=False)
    
    # Reference existing region enum
    region_type = ENUM('US', 'INDIA', 'PHILIPPINES', name='region', create_type=False)
    
    # Get existing tables
    tables = inspector.get_table_names()
    
    # Create user_leaves table if not exists
    if 'user_leaves' in tables:
        return  # All tables should exist if user_leaves exists
        
    op.create_table(
        'user_leaves',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('leave_type', leave_type, nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', leave_status, server_default='PENDING', nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('partial_day', sa.Boolean(), server_default='false'),
        sa.Column('hours_off', sa.Float(), nullable=True),
        sa.Column('approved_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_leaves_user_dates', 'user_leaves', ['user_id', 'start_date', 'end_date'])
    
    # Create region_holidays table
    op.create_table(
        'region_holidays',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('region', region_type, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('is_optional', sa.Boolean(), server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_region_holiday_date', 'region_holidays', ['region', 'date'], unique=True)
    
    # Create company_holidays table
    op.create_table(
        'company_holidays',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_company_holiday_date', 'company_holidays', ['date'], unique=True)
    
    # Insert sample holidays for 2026
    op.execute("""
        INSERT INTO company_holidays (id, name, date, year, description, created_at)
        VALUES
        (gen_random_uuid(), 'New Year''s Day', '2026-01-01', 2026, 'New Year celebration', NOW()),
        (gen_random_uuid(), 'Christmas Day', '2026-12-25', 2026, 'Christmas celebration', NOW()),
        (gen_random_uuid(), 'Christmas Eve', '2026-12-24', 2026, 'Christmas Eve', NOW());
    """)
    
    # Insert US holidays
    op.execute("""
        INSERT INTO region_holidays (id, region, name, date, year, is_optional, description, created_at)
        VALUES
        (gen_random_uuid(), 'US', 'Martin Luther King Jr. Day', '2026-01-19', 2026, false, 'MLK Day', NOW()),
        (gen_random_uuid(), 'US', 'Presidents Day', '2026-02-16', 2026, false, 'Presidents Day', NOW()),
        (gen_random_uuid(), 'US', 'Memorial Day', '2026-05-25', 2026, false, 'Memorial Day', NOW()),
        (gen_random_uuid(), 'US', 'Independence Day', '2026-07-04', 2026, false, 'Independence Day', NOW()),
        (gen_random_uuid(), 'US', 'Labor Day', '2026-09-07', 2026, false, 'Labor Day', NOW()),
        (gen_random_uuid(), 'US', 'Thanksgiving', '2026-11-26', 2026, false, 'Thanksgiving Day', NOW()),
        (gen_random_uuid(), 'US', 'Day after Thanksgiving', '2026-11-27', 2026, false, 'Black Friday', NOW());
    """)
    
    # Insert India holidays
    op.execute("""
        INSERT INTO region_holidays (id, region, name, date, year, is_optional, description, created_at)
        VALUES
        (gen_random_uuid(), 'INDIA', 'Republic Day', '2026-01-26', 2026, false, 'Republic Day of India', NOW()),
        (gen_random_uuid(), 'INDIA', 'Holi', '2026-03-10', 2026, false, 'Festival of Colors', NOW()),
        (gen_random_uuid(), 'INDIA', 'Good Friday', '2026-04-03', 2026, false, 'Good Friday', NOW()),
        (gen_random_uuid(), 'INDIA', 'Independence Day', '2026-08-15', 2026, false, 'Independence Day of India', NOW()),
        (gen_random_uuid(), 'INDIA', 'Gandhi Jayanti', '2026-10-02', 2026, false, 'Birthday of Mahatma Gandhi', NOW()),
        (gen_random_uuid(), 'INDIA', 'Diwali', '2026-10-20', 2026, false, 'Festival of Lights', NOW()),
        (gen_random_uuid(), 'INDIA', 'Diwali Holiday', '2026-10-21', 2026, false, 'Diwali Celebration', NOW());
    """)


def downgrade() -> None:
    op.drop_index('ix_company_holiday_date', table_name='company_holidays')
    op.drop_table('company_holidays')
    op.drop_index('ix_region_holiday_date', table_name='region_holidays')
    op.drop_table('region_holidays')
    op.drop_index('ix_user_leaves_user_dates', table_name='user_leaves')
    op.drop_table('user_leaves')
    
    # Remove unavailability_reason column from user_daily_capacity
    op.drop_column('user_daily_capacity', 'unavailability_reason')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS leavestatus')
    op.execute('DROP TYPE IF EXISTS leavetype')
