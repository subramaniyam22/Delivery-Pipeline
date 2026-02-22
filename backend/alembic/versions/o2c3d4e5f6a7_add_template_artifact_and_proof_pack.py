"""Add template_artifacts and proof_packs tables.

Revision ID: o2c3d4e5f6a7
Revises: n1b2c3d4e5f6
Create Date: 2026-02-16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "o2c3d4e5f6a7"
down_revision = "n1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "template_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("s3_key", sa.String(1024), nullable=False, index=True),
        sa.Column("version", sa.String(64), nullable=False, index=True),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "proof_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("stage", sa.String(64), nullable=False, index=True),
        sa.Column("s3_prefix", sa.String(1024), nullable=False, index=True),
        sa.Column("size_mb", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("proof_packs")
    op.drop_table("template_artifacts")
