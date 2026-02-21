"""Add HOLD/NEEDS_REVIEW to project status and autonomy columns.

Revision ID: k8b9c0d1e2f3a
Revises: j7a8b9c0d1e2f
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "k8b9c0d1e2f3a"
down_revision = "j7a8b9c0d1e2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new project status enum values (PostgreSQL enum type is usually lowercase)
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'HOLD'")
    op.execute("ALTER TYPE projectstatus ADD VALUE IF NOT EXISTS 'NEEDS_REVIEW'")

    op.add_column(
        "projects",
        sa.Column("hold_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("needs_review_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("blockers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
    )
    op.add_column(
        "projects",
        sa.Column("defect_cycle_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("projects", "defect_cycle_count")
    op.drop_column("projects", "blockers_json")
    op.drop_column("projects", "needs_review_reason")
    op.drop_column("projects", "hold_reason")
    # PostgreSQL does not support removing enum values; leave HOLD/NEEDS_REVIEW in type