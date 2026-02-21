"""Add onboarding field_sentinels_json, job_runs.config_version, OnboardingData.last_content_update_at.

Revision ID: m0a1b2c3d4e5f
Revises: l9c0d1e2f3a4
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "m0a1b2c3d4e5f"
down_revision = "l9c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_data",
        sa.Column("field_sentinels_json", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "onboarding_data",
        sa.Column("last_content_update_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "job_runs",
        sa.Column("config_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "templates",
        sa.Column("build_source_type", sa.String(20), nullable=True),
    )
    op.add_column(
        "templates",
        sa.Column("build_source_ref", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("templates", "build_source_ref")
    op.drop_column("templates", "build_source_type")
    op.drop_column("job_runs", "config_version")
    op.drop_column("onboarding_data", "last_content_update_at")
    op.drop_column("onboarding_data", "field_sentinels_json")
