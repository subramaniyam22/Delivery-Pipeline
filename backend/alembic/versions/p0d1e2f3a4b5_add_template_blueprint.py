"""Add template blueprint fields and template_blueprint_jobs table.

Revision ID: p0d1e2f3a4b5
Revises: o9c0d1e2f3a4
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "p0d1e2f3a4b5"
down_revision = "o9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("blueprint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("templates", sa.Column("blueprint_schema_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("templates", sa.Column("blueprint_quality_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"))
    op.add_column("templates", sa.Column("prompt_log_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"))
    op.add_column("templates", sa.Column("blueprint_hash", sa.String(64), nullable=True))

    op.create_table(
        "template_blueprint_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_template_blueprint_jobs_template_id", "template_blueprint_jobs", ["template_id"])
    op.create_index("ix_template_blueprint_jobs_status", "template_blueprint_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_template_blueprint_jobs_status", table_name="template_blueprint_jobs")
    op.drop_index("ix_template_blueprint_jobs_template_id", table_name="template_blueprint_jobs")
    op.drop_table("template_blueprint_jobs")
    op.drop_column("templates", "blueprint_hash")
    op.drop_column("templates", "prompt_log_json")
    op.drop_column("templates", "blueprint_quality_json")
    op.drop_column("templates", "blueprint_schema_version")
    op.drop_column("templates", "blueprint_json")
