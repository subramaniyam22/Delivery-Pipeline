"""add job runs table

Revision ID: d7f3a2c6b1a9
Revises: b206386a8ce2
Create Date: 2026-02-07 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "d7f3a2c6b1a9"
down_revision = "b206386a8ce2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    job_run_status = postgresql.ENUM(
        "QUEUED",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "NEEDS_HUMAN",
        "CANCELED",
        name="job_run_status",
        create_type=False,
    )
    job_run_status.create(op.get_bind(), checkfirst=True)

    stage_enum = postgresql.ENUM(
        "SALES",
        "ONBOARDING",
        "ASSIGNMENT",
        "BUILD",
        "TEST",
        "DEFECT_VALIDATION",
        "COMPLETE",
        name="stage",
        create_type=False,
    )
    stage_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", stage_enum, nullable=False),
        sa.Column("status", job_run_status, nullable=False, server_default="QUEUED"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("locked_by", sa.String(length=100), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
    )
    op.create_index("ix_job_runs_project_id", "job_runs", ["project_id"])
    op.create_index("ix_job_runs_stage", "job_runs", ["stage"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])
    op.create_index("ix_job_runs_request_id", "job_runs", ["request_id"])
    op.create_index("ix_job_runs_next_run_at", "job_runs", ["next_run_at"])
    op.create_index("ix_job_runs_locked_by", "job_runs", ["locked_by"])

    op.add_column("stage_outputs", sa.Column("job_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_stage_outputs_job_run_id", "stage_outputs", ["job_run_id"])
    op.create_foreign_key(
        "fk_stage_outputs_job_run_id",
        "stage_outputs",
        "job_runs",
        ["job_run_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_stage_outputs_job_run_id", "stage_outputs", type_="foreignkey")
    op.drop_index("ix_stage_outputs_job_run_id", table_name="stage_outputs")
    op.drop_column("stage_outputs", "job_run_id")

    op.drop_index("ix_job_runs_locked_by", table_name="job_runs")
    op.drop_index("ix_job_runs_next_run_at", table_name="job_runs")
    op.drop_index("ix_job_runs_request_id", table_name="job_runs")
    op.drop_index("ix_job_runs_status", table_name="job_runs")
    op.drop_index("ix_job_runs_stage", table_name="job_runs")
    op.drop_index("ix_job_runs_project_id", table_name="job_runs")
    op.drop_table("job_runs")

    job_run_status = sa.Enum(
        "QUEUED",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        "NEEDS_HUMAN",
        "CANCELED",
        name="job_run_status",
    )
    job_run_status.drop(op.get_bind(), checkfirst=True)
