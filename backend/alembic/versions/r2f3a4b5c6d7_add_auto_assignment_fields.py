"""Add User skills/capacity/availability and Project assignment_rationale for auto-assignment.

Revision ID: r2f3a4b5c6d7
Revises: q1e2f3a4b5c6
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "r2f3a4b5c6d7"
down_revision = "q1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("skills_json", JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"))
    op.add_column("users", sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("availability_status", sa.String(30), nullable=False, server_default="available"))
    op.add_column("users", sa.Column("timezone", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("performance_score", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("active_assignments_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projects", sa.Column("assignment_rationale_json", JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"))


def downgrade() -> None:
    op.drop_column("projects", "assignment_rationale_json")
    op.drop_column("users", "active_assignments_count")
    op.drop_column("users", "performance_score")
    op.drop_column("users", "timezone")
    op.drop_column("users", "availability_status")
    op.drop_column("users", "capacity")
    op.drop_column("users", "skills_json")
