"""add templates and artifact metadata fields

Revision ID: f2a9c4d7b8e1
Revises: e1c4b2a9f6d0
Create Date: 2026-02-07 21:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "f2a9c4d7b8e1"
down_revision = "e1c4b2a9f6d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("repo_url", sa.String(length=1000), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=False, server_default="main"),
        sa.Column("meta_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_templates_is_active", "templates", ["is_active"])

    op.add_column("artifacts", sa.Column("artifact_type", sa.String(length=100), nullable=True))
    op.add_column("artifacts", sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute("UPDATE artifacts SET artifact_type = type WHERE artifact_type IS NULL")

    op.add_column("stage_outputs", sa.Column("score", sa.Float(), nullable=True))
    op.add_column("stage_outputs", sa.Column("report_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("stage_outputs", sa.Column("evidence_links_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("stage_outputs", "evidence_links_json")
    op.drop_column("stage_outputs", "report_json")
    op.drop_column("stage_outputs", "score")

    op.drop_column("artifacts", "metadata_json")
    op.drop_column("artifacts", "artifact_type")

    op.drop_index("ix_templates_is_active", table_name="templates")
    op.drop_table("templates")
