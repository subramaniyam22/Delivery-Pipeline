"""Add project_contracts table and project.contract_build_error.

Revision ID: o9c0d1e2f3a4
Revises: n8b9c0d1e2f3
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "o9c0d1e2f3a4"
down_revision = "n8b9c0d1e2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("contract_build_error", sa.Text(), nullable=True))

    op.create_table(
        "project_contracts",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contract_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_project_contracts_updated_at", "project_contracts", ["updated_at"])


def downgrade() -> None:
    op.drop_index("ix_project_contracts_updated_at", table_name="project_contracts")
    op.drop_table("project_contracts")
    op.drop_column("projects", "contract_build_error")
