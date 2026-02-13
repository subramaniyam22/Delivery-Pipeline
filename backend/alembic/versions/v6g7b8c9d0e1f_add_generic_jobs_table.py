"""Add generic jobs table and project_stage_state.evidence_json.

Revision ID: v6g7b8c9d0e1f
Revises: u5f8a9b0c1d2e
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "v6g7b8c9d0e1f"
down_revision = "u5f8a9b0c1d2e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_stage_state", sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"))
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(128), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("run_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("locked_by", sa.String(128), nullable=True),
        sa.Column("lock_expires_at", sa.DateTime(), nullable=True),
        sa.Column("idempotency_key", sa.String(256), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_run_at", "jobs", ["run_at"])
    op.create_index("ix_jobs_status_run_at", "jobs", ["status", "run_at"])
    op.create_index("ix_jobs_locked_by", "jobs", ["locked_by"])
    op.create_unique_constraint("uq_jobs_idempotency_key", "jobs", ["idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_jobs_idempotency_key", "jobs", type_="unique")
    op.drop_index("ix_jobs_locked_by", table_name="jobs")
    op.drop_index("ix_jobs_status_run_at", table_name="jobs")
    op.drop_index("ix_jobs_run_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_type", table_name="jobs")
    op.drop_table("jobs")
    op.drop_column("project_stage_state", "evidence_json")
