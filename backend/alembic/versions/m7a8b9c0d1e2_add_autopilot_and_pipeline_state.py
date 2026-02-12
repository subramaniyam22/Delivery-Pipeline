"""Add autopilot columns, project_stage_state, pipeline_events, job_runs correlation/requested_by.

Revision ID: m7a8b9c0d1e2
Revises: l6f7a8b9c0d1
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m7a8b9c0d1e2"
down_revision = "l6f7a8b9c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Project autopilot columns
    op.add_column("projects", sa.Column("autopilot_enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("projects", sa.Column("autopilot_mode", sa.String(30), nullable=False, server_default="conditional"))
    op.add_column("projects", sa.Column("autopilot_paused_reason", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("autopilot_failure_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projects", sa.Column("autopilot_last_action_at", sa.DateTime(), nullable=True))
    op.add_column("projects", sa.Column("autopilot_lock_until", sa.DateTime(), nullable=True))

    # JobRun correlation_id, requested_by, requested_by_user_id
    op.add_column("job_runs", sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("job_runs", sa.Column("requested_by", sa.String(50), nullable=True))
    op.add_column("job_runs", sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_job_runs_correlation_id", "job_runs", ["correlation_id"])
    op.create_foreign_key(
        "fk_job_runs_requested_by_user_id",
        "job_runs",
        "users",
        ["requested_by_user_id"],
        ["id"],
    )

    # project_stage_state
    op.create_table(
        "project_stage_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_key", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="not_started"),
        sa.Column("last_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("blocked_reasons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("required_actions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="[]"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_project_stage_state_project_id", "project_stage_state", ["project_id"])
    op.create_index("ix_project_stage_state_stage_key", "project_stage_state", ["stage_key"])
    op.create_index("ix_project_stage_state_last_job_id", "project_stage_state", ["last_job_id"])
    op.create_unique_constraint(
        "uq_project_stage_state_project_stage",
        "project_stage_state",
        ["project_id", "stage_key"],
    )

    # pipeline_events
    op.create_table(
        "pipeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_key", sa.String(50), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_pipeline_events_project_id", "pipeline_events", ["project_id"])
    op.create_index("ix_pipeline_events_stage_key", "pipeline_events", ["stage_key"])
    op.create_index("ix_pipeline_events_event_type", "pipeline_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_events_event_type", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_stage_key", table_name="pipeline_events")
    op.drop_index("ix_pipeline_events_project_id", table_name="pipeline_events")
    op.drop_table("pipeline_events")

    op.drop_constraint("uq_project_stage_state_project_stage", "project_stage_state", type_="unique")
    op.drop_index("ix_project_stage_state_last_job_id", table_name="project_stage_state")
    op.drop_index("ix_project_stage_state_stage_key", table_name="project_stage_state")
    op.drop_index("ix_project_stage_state_project_id", table_name="project_stage_state")
    op.drop_table("project_stage_state")

    op.drop_constraint("fk_job_runs_requested_by_user_id", "job_runs", type_="foreignkey")
    op.drop_index("ix_job_runs_correlation_id", table_name="job_runs")
    op.drop_column("job_runs", "requested_by_user_id")
    op.drop_column("job_runs", "requested_by")
    op.drop_column("job_runs", "correlation_id")

    op.drop_column("projects", "autopilot_lock_until")
    op.drop_column("projects", "autopilot_last_action_at")
    op.drop_column("projects", "autopilot_failure_count")
    op.drop_column("projects", "autopilot_paused_reason")
    op.drop_column("projects", "autopilot_mode")
    op.drop_column("projects", "autopilot_enabled")
