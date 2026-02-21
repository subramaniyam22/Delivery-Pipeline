"""Add project_template_instances for template clone / build lock.

Revision ID: l9c0d1e2f3a4
Revises: k8b9c0d1e2f3a
Create Date: 2026-02-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "l9c0d1e2f3a4"
down_revision = "k8b9c0d1e2f3a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_template_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("fallback_template_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("fallback_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("use_fallback_callout", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fallback_template_id"], ["templates.id"], ondelete="SET NULL"),
    )
    op.create_unique_constraint("uq_project_template_instances_project_id", "project_template_instances", ["project_id"])


def downgrade() -> None:
    op.drop_table("project_template_instances")
