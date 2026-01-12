"""Add comprehensive capacity management tables

Revision ID: 011_comprehensive_capacity
Revises: 010_leave_holiday
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM

# revision identifiers, used by Alembic.
revision = '011_comprehensive_capacity'
down_revision = '010_leave_holiday'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Add is_mandatory to company_holidays if not exists
    columns = [c['name'] for c in inspector.get_columns('company_holidays')]
    if 'is_mandatory' not in columns:
        op.add_column('company_holidays',
            sa.Column('is_mandatory', sa.Boolean(), server_default='true')
        )
    
    # Create leave_entitlement_type enum
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE leaveentitlementtype AS ENUM (
                'CASUAL', 'SICK', 'EARNED', 'MATERNITY', 'PATERNITY',
                'BEREAVEMENT', 'UNPAID', 'COMPENSATORY', 'WORK_FROM_HOME'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Create calendar_provider enum
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE calendarprovider AS ENUM ('GOOGLE', 'OUTLOOK', 'APPLE', 'MANUAL');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))
    
    # Reference existing enums
    role_type = ENUM('ADMIN', 'MANAGER', 'CONSULTANT', 'PC', 'BUILDER', 'TESTER',
                     name='role', create_type=False)
    region_type = ENUM('US', 'INDIA', 'PHILIPPINES', name='region', create_type=False)
    leave_entitlement_type = ENUM('CASUAL', 'SICK', 'EARNED', 'MATERNITY', 'PATERNITY',
                                   'BEREAVEMENT', 'UNPAID', 'COMPENSATORY', 'WORK_FROM_HOME',
                                   name='leaveentitlementtype', create_type=False)
    calendar_provider_type = ENUM('GOOGLE', 'OUTLOOK', 'APPLE', 'MANUAL',
                                   name='calendarprovider', create_type=False)
    
    # Skip if tables already exist
    if 'leave_entitlement_policies' in tables:
        return
    
    # Create leave_entitlement_policies table
    op.create_table(
        'leave_entitlement_policies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('leave_type', leave_entitlement_type, nullable=False),
        sa.Column('role', role_type, nullable=True),
        sa.Column('region', region_type, nullable=True),
        sa.Column('annual_days', sa.Float(), nullable=False),
        sa.Column('can_carry_forward', sa.Boolean(), server_default='false'),
        sa.Column('max_carry_forward_days', sa.Float(), server_default='0'),
        sa.Column('requires_approval', sa.Boolean(), server_default='true'),
        sa.Column('min_notice_days', sa.Integer(), server_default='0'),
        sa.Column('max_consecutive_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_leave_policy_type_role_region', 'leave_entitlement_policies',
                    ['leave_type', 'role', 'region'], unique=True)
    
    # Create user_leave_balances table
    op.create_table(
        'user_leave_balances',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('leave_type', leave_entitlement_type, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('entitled_days', sa.Float(), nullable=False),
        sa.Column('used_days', sa.Float(), server_default='0'),
        sa.Column('pending_days', sa.Float(), server_default='0'),
        sa.Column('carried_forward', sa.Float(), server_default='0'),
        sa.Column('adjusted_days', sa.Float(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_leave_balance', 'user_leave_balances',
                    ['user_id', 'leave_type', 'year'], unique=True)
    
    # Create calendar_connections table
    op.create_table(
        'calendar_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('provider', calendar_provider_type, nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('calendar_id', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_calendar_connection_user', 'calendar_connections',
                    ['user_id', 'provider'], unique=True)
    
    # Create meeting_blocks table
    op.create_table(
        'meeting_blocks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('connection_id', UUID(as_uuid=True), sa.ForeignKey('calendar_connections.id'), nullable=True),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('is_all_day', sa.Boolean(), server_default='false'),
        sa.Column('is_recurring', sa.Boolean(), server_default='false'),
        sa.Column('recurrence_rule', sa.String(255), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('is_busy', sa.Boolean(), server_default='true'),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_meeting_user_date', 'meeting_blocks', ['user_id', 'start_time'])
    
    # Create time_entries table
    op.create_table(
        'time_entries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('hours', sa.Float(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_billable', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    op.create_index('ix_time_entry_user_date', 'time_entries', ['user_id', 'date'])
    
    # Create capacity_adjustments table
    op.create_table(
        'capacity_adjustments',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('adjustment_type', sa.String(50), nullable=False),
        sa.Column('daily_hours_adjustment', sa.Float(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('approved_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Insert default leave entitlement policies
    op.execute("""
        INSERT INTO leave_entitlement_policies (id, leave_type, role, region, annual_days, can_carry_forward, max_carry_forward_days, requires_approval, min_notice_days, is_active)
        VALUES
        -- Universal policies (all roles, all regions)
        (gen_random_uuid(), 'CASUAL', NULL, NULL, 12, false, 0, true, 1, true),
        (gen_random_uuid(), 'SICK', NULL, NULL, 10, false, 0, false, 0, true),
        (gen_random_uuid(), 'EARNED', NULL, NULL, 15, true, 5, true, 7, true),
        (gen_random_uuid(), 'MATERNITY', NULL, NULL, 180, false, 0, true, 30, true),
        (gen_random_uuid(), 'PATERNITY', NULL, NULL, 15, false, 0, true, 7, true),
        (gen_random_uuid(), 'BEREAVEMENT', NULL, NULL, 5, false, 0, false, 0, true),
        (gen_random_uuid(), 'COMPENSATORY', NULL, NULL, 0, true, 10, true, 1, true),
        (gen_random_uuid(), 'WORK_FROM_HOME', NULL, NULL, 52, false, 0, true, 1, true),
        
        -- India-specific (additional earned leaves)
        (gen_random_uuid(), 'EARNED', NULL, 'INDIA', 18, true, 10, true, 7, true),
        
        -- US-specific
        (gen_random_uuid(), 'EARNED', NULL, 'US', 20, true, 5, true, 7, true);
    """)


def downgrade() -> None:
    op.drop_table('capacity_adjustments')
    op.drop_index('ix_time_entry_user_date', table_name='time_entries')
    op.drop_table('time_entries')
    op.drop_index('ix_meeting_user_date', table_name='meeting_blocks')
    op.drop_table('meeting_blocks')
    op.drop_index('ix_calendar_connection_user', table_name='calendar_connections')
    op.drop_table('calendar_connections')
    op.drop_index('ix_user_leave_balance', table_name='user_leave_balances')
    op.drop_table('user_leave_balances')
    op.drop_index('ix_leave_policy_type_role_region', table_name='leave_entitlement_policies')
    op.drop_table('leave_entitlement_policies')
    
    op.drop_column('company_holidays', 'is_mandatory')
    
    op.execute('DROP TYPE IF EXISTS calendarprovider')
    op.execute('DROP TYPE IF EXISTS leaveentitlementtype')
