"""Add template_blueprint_runs table and template denorm fields (blueprint_status, blueprint_last_run_id, blueprint_updated_at).

Revision ID: u5f8a9b0c1d2e
Revises: t4b6c8d0e1f2a
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "u5f8a9b0c1d2e"
down_revision = "t4b6c8d0e1f2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New table: template_blueprint_runs
    op.create_table(
        "template_blueprint_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("schema_version", sa.String(20), nullable=False, server_default="v1"),
        sa.Column("model_used", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("blueprint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_template_blueprint_runs_template_id", "template_blueprint_runs", ["template_id"])
    op.create_index("ix_template_blueprint_runs_status", "template_blueprint_runs", ["status"])
    op.create_index("ix_template_blueprint_runs_correlation_id", "template_blueprint_runs", ["correlation_id"])
    op.create_index("ix_template_blueprint_runs_template_started", "template_blueprint_runs", ["template_id", "started_at"], postgresql_ops={"started_at": "DESC NULLS LAST"})

    # Template denorm fields
    op.add_column("templates", sa.Column("blueprint_status", sa.String(30), nullable=True))
    op.add_column("templates", sa.Column("blueprint_last_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("templates", sa.Column("blueprint_updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key(
        "fk_templates_blueprint_last_run_id",
        "templates",
        "template_blueprint_runs",
        ["blueprint_last_run_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_templates_blueprint_last_run_id", "templates", type_="foreignkey")
    op.drop_column("templates", "blueprint_updated_at")
    op.drop_column("templates", "blueprint_last_run_id")
    op.drop_column("templates", "blueprint_status")
    op.drop_index("ix_template_blueprint_runs_template_started", table_name="template_blueprint_runs")
    op.drop_index("ix_template_blueprint_runs_correlation_id", table_name="template_blueprint_runs")
    op.drop_index("ix_template_blueprint_runs_status", table_name="template_blueprint_runs")
    op.drop_index("ix_template_blueprint_runs_template_id", table_name="template_blueprint_runs")
    op.drop_table("template_blueprint_runs")
