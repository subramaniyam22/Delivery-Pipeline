"""add project config and stage output gate decision

Revision ID: e1c4b2a9f6d0
Revises: d7f3a2c6b1a9
Create Date: 2026-02-07 20:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e1c4b2a9f6d0"
down_revision = "d7f3a2c6b1a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("stage_gates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("thresholds_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("hitl_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_project_configs_project_id", "project_configs", ["project_id"], unique=True)

    op.add_column("stage_outputs", sa.Column("gate_decision", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("stage_outputs", "gate_decision")
    op.drop_index("ix_project_configs_project_id", table_name="project_configs")
    op.drop_table("project_configs")
