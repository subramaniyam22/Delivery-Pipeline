"""Add HITL overrides to project_configs and stage_approvals table.

Revision ID: n8b9c0d1e2f3
Revises: m7a8b9c0d1e2
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "n8b9c0d1e2f3"
down_revision = "m7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_configs",
        sa.Column("hitl_overrides_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
    )

    op.create_table(
        "stage_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_key", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_role", sa.String(50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("gate_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("inputs_fingerprint", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
    )
    op.create_index("ix_stage_approvals_project_id", "stage_approvals", ["project_id"])
    op.create_index("ix_stage_approvals_stage_key", "stage_approvals", ["stage_key"])
    op.create_index("ix_stage_approvals_status", "stage_approvals", ["status"])


def downgrade() -> None:
    op.drop_index("ix_stage_approvals_status", table_name="stage_approvals")
    op.drop_index("ix_stage_approvals_stage_key", table_name="stage_approvals")
    op.drop_index("ix_stage_approvals_project_id", table_name="stage_approvals")
    op.drop_table("stage_approvals")
    op.drop_column("project_configs", "hitl_overrides_json")
