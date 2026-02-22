"""Add confirmation_requests and policy_config tables.

Revision ID: n1b2c3d4e5f6
Revises: m0a1b2c3d4e5f
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "n1b2c3d4e5f6"
down_revision = "m0a1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("build_attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_table(
        "confirmation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, index=True, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reminded_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
    )
    op.create_table(
        "policy_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(80), nullable=False, index=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_unique_constraint("uq_policy_config_key", "policy_config", ["key"])


def downgrade() -> None:
    op.drop_constraint("uq_policy_config_key", "policy_config", type_="unique")
    op.drop_table("policy_config")
    op.drop_table("confirmation_requests")
    op.drop_column("projects", "build_attempt_count")
