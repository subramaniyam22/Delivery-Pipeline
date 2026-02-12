"""Add template validation fields, project quality_overrides, template_validation_jobs.

Revision ID: q1e2f3a4b5c6
Revises: p0d1e2f3a4b5
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "q1e2f3a4b5c6"
down_revision = "p0d1e2f3a4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("templates", sa.Column("validation_status", sa.String(30), nullable=False, server_default="not_run"))
    op.add_column("templates", sa.Column("validation_last_run_at", sa.DateTime(), nullable=True))
    op.add_column("templates", sa.Column("validation_hash", sa.String(64), nullable=True))
    op.add_column("projects", sa.Column("quality_overrides_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"))

    op.create_table(
        "template_validation_jobs",
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
    op.create_index("ix_template_validation_jobs_template_id", "template_validation_jobs", ["template_id"])
    op.create_index("ix_template_validation_jobs_status", "template_validation_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_template_validation_jobs_status", table_name="template_validation_jobs")
    op.drop_index("ix_template_validation_jobs_template_id", table_name="template_validation_jobs")
    op.drop_table("template_validation_jobs")
    op.drop_column("projects", "quality_overrides_json")
    op.drop_column("templates", "validation_hash")
    op.drop_column("templates", "validation_last_run_at")
    op.drop_column("templates", "validation_status")
